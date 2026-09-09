import base64
import datetime as dt
import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError


TABLE_NAME = os.environ["TABLE_NAME"]
table = boto3.resource("dynamodb").Table(TABLE_NAME)
dynamodb = boto3.client("dynamodb")
serializer = TypeSerializer()


def json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError


def response(status, payload):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(payload, ensure_ascii=False, default=json_default),
    }


def request_body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    body = json.loads(raw)
    if not isinstance(body, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON.")
    return body


def required_string(body, name):
    value = body.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} debe ser un string no vacío.")
    return value.strip()


def serialize_map(value):
    return {name: serializer.serialize(item) for name, item in value.items()}


def public_experiment(item):
    return {
        name: item[name]
        for name in ("experimentId", "name", "sector", "status", "createdAt", "closedAt")
        if name in item
    }


def create_experiment(event, experiment_id):
    body = request_body(event)
    item = {
        "experimentId": experiment_id,
        "recordId": "METADATA",
        "entityType": "EXPERIMENT",
        "name": required_string(body, "name"),
        "sector": required_string(body, "sector"),
        "status": "OPEN",
        "createdAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }
    table.put_item(
        Item=item,
        # TODO: impida que PutItem reemplace un experimento existente.
    )
    return response(201, public_experiment(item))


def get_experiment(_event, experiment_id):
    result = table.get_item(
        Key={"experimentId": experiment_id, "recordId": "METADATA"},
        ConsistentRead=True,
    )
    item = result.get("Item")
    if not item:
        return response(404, {"error": "EXPERIMENT_NOT_FOUND", "message": "El experimento no existe."})
    return response(200, public_experiment(item))


def add_observation(event, experiment_id):
    body = request_body(event)
    observation_id = required_string(body, "observationId")
    observed_at = required_string(body, "observedAt")
    item = {
        "experimentId": experiment_id,
        "recordId": f"{observed_at}#{observation_id}",
        "entityType": "OBSERVATION",
        "observationId": observation_id,
        "observedAt": observed_at,
        "source": required_string(body, "source"),
        "message": required_string(body, "message"),
    }
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "ConditionCheck": {
                    "TableName": TABLE_NAME,
                    "Key": serialize_map({"experimentId": experiment_id, "recordId": "METADATA"}),
                    # TODO: la expresión provisional acepta cualquier status; debe aceptar solamente OPEN.
                    "ConditionExpression": "attribute_exists(experimentId) AND (#status = :open OR #status <> :open)",
                    "ExpressionAttributeNames": {"#status": "status"},
                    "ExpressionAttributeValues": {":open": {"S": "OPEN"}},
                }
            },
            {
                "Put": {
                    "TableName": TABLE_NAME,
                    "Item": serialize_map(item),
                    "ConditionExpression": "attribute_not_exists(experimentId) AND attribute_not_exists(recordId)",
                }
            },
        ]
    )
    public = {name: item[name] for name in ("observationId", "observedAt", "source", "message")}
    return response(201, public)


def list_observations(_event, experiment_id):
    # TODO: implemente esta operación mediante Query. La respuesta debe contener experimentId y observations.
    return response(501, {"error": "NOT_IMPLEMENTED", "message": "La consulta de observaciones no está implementada."})


def close_experiment(_event, experiment_id):
    closed_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    result = table.update_item(
        Key={"experimentId": experiment_id, "recordId": "METADATA"},
        UpdateExpression="SET #status = :closed, closedAt = :closed_at",
        # TODO: la expresión provisional acepta cualquier status; debe aceptar solamente OPEN.
        ConditionExpression="attribute_exists(experimentId) AND (#status = :open OR #status <> :open)",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":open": "OPEN", ":closed": "CLOSED", ":closed_at": closed_at},
        ReturnValues="ALL_NEW",
    )
    return response(200, public_experiment(result["Attributes"]))


ROUTES = {
    "PUT /experiments/{experimentId}": create_experiment,
    "GET /experiments/{experimentId}": get_experiment,
    "POST /experiments/{experimentId}/observations": add_observation,
    "GET /experiments/{experimentId}/observations": list_observations,
    "PATCH /experiments/{experimentId}/close": close_experiment,
}


def lambda_handler(event, context):
    route_key = str(event.get("routeKey") or "")
    experiment_id = str((event.get("pathParameters") or {}).get("experimentId") or "").strip()
    print(json.dumps({"requestId": context.aws_request_id, "routeKey": route_key, "experimentId": experiment_id}))
    try:
        handler = ROUTES.get(route_key)
        if not handler:
            return response(404, {"error": "ROUTE_NOT_FOUND", "message": "La route no existe."})
        if not experiment_id:
            raise ValueError("experimentId es obligatorio.")
        return handler(event, experiment_id)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return response(400, {"error": "INVALID_JSON", "message": "El cuerpo no contiene JSON válido."})
    except ValueError as error:
        return response(400, {"error": "INVALID_REQUEST", "message": str(error)})
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException" and route_key.startswith("PUT "):
            return response(409, {"error": "EXPERIMENT_EXISTS", "message": "El experimento ya existe."})
        if code in {"TransactionCanceledException", "ConditionalCheckFailedException"} and route_key.startswith("POST "):
            return response(409, {"error": "OBSERVATION_REJECTED", "message": "El experimento no está abierto o la observación ya existe."})
        if code == "ConditionalCheckFailedException" and route_key.startswith("PATCH "):
            return response(409, {"error": "CLOSE_REJECTED", "message": "El experimento no existe o no está abierto."})
        print(json.dumps({"requestId": context.aws_request_id, "awsError": code}))
        return response(500, {"error": "DYNAMODB_ERROR", "message": "DynamoDB rechazó la operación."})
