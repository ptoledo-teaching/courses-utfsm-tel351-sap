# SAP - Stateful APIs

Este laboratorio se centra en la persistencia de estado mediante Amazon DynamoDB. En la actividad se implementa una API para registrar pruebas operacionales y observaciones sobre la infraestructura de la Holonet mediante AWS Lambda, Amazon API Gateway y una table DynamoDB.

La infraestructura se configura desde AWS Management Console. Las `routes` de la API se importan desde un contrato OpenAPI proporcionado, mientras que las interacciones con DynamoDB deben analizarse, completarse y verificarse durante el laboratorio.

## Resultados esperados

Al completar el laboratorio podrá:

1. Modelar entidades relacionadas en DynamoDB mediante una primary key compuesta
2. Implementar operaciones de escritura, lectura, consulta, actualización y transacción
3. Construir una consulta `Query` a partir del patrón de acceso de un sistema
4. Distinguir el acceso dirigido mediante `Query` de la exploración completa mediante `Scan`
5. Utilizar expresiones condicionales y transacciones para proteger la consistencia del estado
6. Implementar una API con estado mediante la integración de API Gateway, Lambda y DynamoDB
7. Resolver múltiples `routes` mediante una Lambda function
8. Definir una inline policy de mínimo privilegio mediante el editor visual de IAM
9. Interpretar el comportamiento y las fallas de una API mediante códigos de estado HTTP y CloudWatch Logs
10. Verificar funcionalmente una infraestructura y eliminar sus recursos al finalizar su uso

## Preparación previa

Antes del laboratorio:

- Confirme que su cuenta AWS personal se encuentra operativa
- Ingrese a AWS Management Console mediante la identidad administrativa de uso regular
- Confirme que el role `TEL351-Evaluator` creado en el laboratorio ICC continúa disponible y tiene asociada la managed policy `ReadOnlyAccess`
- Confirme que puede acceder al sitio de evaluación en [https://lab04.shareddomain.link](https://lab04.shareddomain.link)
- Descargue los siguientes archivos:
  - [`assets/openapi.yaml`](assets/openapi.yaml)
  - [`assets/lambda_function.py`](assets/lambda_function.py)

> `openapi.yaml` define el contrato y las `routes` de la API. `lambda_function.py` contiene una implementación inicial deliberadamente incompleta que deberá corregir durante la actividad.

El sitio de evaluación [https://lab04.shareddomain.link](https://lab04.shareddomain.link) inspecciona la infraestructura desplegada, ejecuta pruebas funcionales remotas y conserva el historial de intentos asociado al RUT.

La evaluación requiere solamente el AWS account ID y el RUT normalizado. El RUT se escribe sin puntos ni guion y con `k` minúscula. Las comprobaciones se ejecutan de manera independiente mientras el role de evaluación pueda asumirse: el incumplimiento de una no impide ejecutar las demás.

## Contexto

La Holonet es la red de telecomunicaciones de la República Galáctica. Esta red permite transmitir mensajes holográficos y otros datos a grandes distancias mediante enlaces a través del hiperespacio. Su funcionamiento depende de una infraestructura distribuida que debe mantenerse operativa en numerosos sectores de la galaxia.

Los equipos responsables del mantenimiento de la red ejecutan experimentos de diagnóstico para analizar el funcionamiento de sus componentes. Un experimento corresponde a una prueba operacional delimitada, realizada sobre la infraestructura de un sector de la galaxia. Puede utilizarse, por ejemplo, para examinar la disponibilidad de un enlace, la respuesta de un repetidor o la estabilidad de una transmisión.

Cada experimento registra un nombre, el sector analizado y su estado actual. Mientras permanece abierto puede recibir múltiples observaciones producidas durante la prueba. Cada observación corresponde a un resultado operacional e incorpora un identificador, el instante en que fue obtenido, el componente que actuó como fuente y un mensaje descriptivo. Las observaciones deben conservarse asociadas al experimento correspondiente y recuperarse en orden cronológico.

El cierre representa el término definitivo de una prueba. Después de esa transición, el experimento y sus observaciones continúan disponibles para consulta, pero no se aceptan nuevos registros ni un segundo cierre. El sistema también debe impedir que la repetición de una solicitud reemplace accidentalmente un experimento o una observación ya existente.

La API que se implementará constituye la interfaz de acceso a este estado compartido. Sus operaciones deben producir resultados consistentes y DynamoDB debe conservar los datos mediante las condiciones necesarias para proteger las reglas anteriores.

## Interacción y verificación de la API

El sitio de evaluación comprueba de forma remota el estado de la infraestructura y el comportamiento de la API. Durante el desarrollo también puede interactuar directamente con la API para observar sus respuestas e identificar el origen de los errores. Postman permite construir y repetir solicitudes HTTP sin escribir comandos ni modificar la infraestructura.

### Probar los endpoints mediante Postman

1. Cree una colección en Postman para el laboratorio
2. Agregue una variable de colección denominada `baseUrl` cuyo valor sea la **Invoke URL** de la HTTP API, sin una barra al final
3. Para las solicitudes `PUT` y `POST`, seleccione **Body → raw → JSON** e ingrese el cuerpo correspondiente
4. Confirme que estas solicitudes incluyan el encabezado `Content-Type: application/json`
5. Guarde cada solicitud en la colección para poder ejecutarla nuevamente después de modificar y desplegar el código

Utilice un identificador de prueba que no haya empleado antes, por ejemplo `postman-001`, y ejecute la siguiente secuencia:

1. Envíe `GET {{baseUrl}}/experiments/postman-001`; antes de crear el experimento debe responder con HTTP `404`
2. Envíe `PUT {{baseUrl}}/experiments/postman-001` con el cuerpo de creación descrito en la subsección **Analizar el sistema requerido**; debe responder con HTTP `201`
3. Repita la solicitud `GET`; debe responder con HTTP `200` y mostrar el experimento en estado `OPEN`
4. Envíe una observación mediante `POST {{baseUrl}}/experiments/postman-001/observations`; debe responder con HTTP `201`
5. Envíe una segunda observación con otro `observationId` y un `observedAt` anterior al de la primera; también debe responder con HTTP `201`
6. Envíe `GET {{baseUrl}}/experiments/postman-001/observations`; debe responder con HTTP `200` y presentar primero la observación con la marca temporal anterior
7. Repita exactamente uno de los `POST`; debe responder con HTTP `409`
8. Envíe `PATCH {{baseUrl}}/experiments/postman-001/close`; debe responder con HTTP `200` y mostrar el estado `CLOSED`
9. Repita el cierre y luego intente agregar una nueva observación; ambas solicitudes deben responder con HTTP `409`

Para repetir la secuencia completa, utilice otro `experimentId`. Esto evita que el estado conservado por una prueba anterior altere los resultados esperados.

### Inspeccionar fallas mediante CloudWatch Logs

Cuando una respuesta no coincida con el resultado esperado:

1. Abra la Lambda function `tel351-sap`
2. Abra **Monitor → View CloudWatch logs**
3. Abra el log stream más reciente
4. Localice la invocación mediante su método HTTP, ruta e identificador de experimento
5. Identifique si la falla corresponde a una validación, una expresión de DynamoDB, una autorización IAM o una excepción no controlada
6. Regrese al código, realice la corrección y seleccione **Deploy** antes de enviar nuevamente la solicitud desde Postman

## Evaluación

En cualquier momento del laboratorio puede evaluar la infraestructura y el comportamiento implementado. No corresponde a una actividad separada: cada intento comprueba el estado alcanzado al seguir la guía.

1. Ingrese a [https://lab04.shareddomain.link](https://lab04.shareddomain.link)
2. Complete **AWS account ID** y **RUT normalizado**
3. Seleccione **Evaluar ahora**
4. Revise individualmente las comprobaciones de infraestructura y comportamiento
5. Corrija la implementación y repita la evaluación cuantas veces sea necesario durante el bloque

Las doce comprobaciones son binarias. El role de evaluación es una precondición sin puntaje y las once comprobaciones restantes suman 100 puntos. Mientras `TEL351-Evaluator` pueda asumirse, el incumplimiento de una comprobación no impide ejecutar las demás. Cada escenario funcional utiliza identificadores nuevos y no depende de los datos creados por otro escenario.

El sitio de evaluación conserva indefinidamente todos los intentos asociados al RUT y los muestra desde el más reciente hasta el más antiguo. El mayor puntaje se muestra solamente como resumen del historial. Los items creados por las pruebas permanecen en la table para que pueda inspeccionar sus atributos `experimentId` y `recordId`.

### Comprobaciones consideradas

La evaluación comprueba:

- La table `tel351-sap` utiliza `experimentId` y `recordId` de tipo String
- La Lambda function obtiene el nombre de la table desde `TABLE_NAME`
- El execution role autoriza solamente las operaciones DynamoDB requeridas
- Las cinco `routes` utilizan la misma Lambda integration
- Un experimento repetido no reemplaza el item original
- Las observaciones se consultan mediante `Query` en orden cronológico
- Las observaciones de distintos experimentos permanecen aisladas
- Una transacción impide registrar observaciones después del cierre
- El cierre solo se aplica una vez a un experimento abierto
- La evaluación remota alcanza 100 puntos

## Actividad

### 1. Establecer la Región principal

1. En la esquina superior derecha seleccione **South America (São Paulo)**
2. Confirme que la Región visible sea **`sa-east-1`**
3. Anote su **AWS account ID** de 12 dígitos

> Todos los recursos del laboratorio se crean en `sa-east-1`. No cambie la Región durante la actividad.

### 2. Analizar el sistema requerido

La API administra experimentos de diagnóstico sobre la infraestructura de la Holonet. Cada experimento comienza en estado `OPEN`, puede recibir observaciones y finalmente pasa a `CLOSED`. Un experimento cerrado permanece disponible para consulta, pero no puede recibir nuevas observaciones ni volver a cerrarse.

Las operaciones expuestas son:

| Method | Path | Resultado esperado |
| --- | --- | --- |
| `PUT` | `/experiments/{experimentId}` | Crea un experimento abierto |
| `GET` | `/experiments/{experimentId}` | Obtiene los metadatos del experimento |
| `POST` | `/experiments/{experimentId}/observations` | Agrega una observación a un experimento abierto |
| `GET` | `/experiments/{experimentId}/observations` | Lista sus observaciones en orden cronológico |
| `PATCH` | `/experiments/{experimentId}/close` | Cierra un experimento abierto |

La creación de un experimento recibe un nombre y el sector donde se realiza:

```json
{
  "name": "Hyperdrive relay diagnostic",
  "sector": "Anoat"
}
```

El registro de una observación recibe un identificador, el instante de observación en UTC, su fuente y un mensaje:

```json
{
  "observationId": "obs-001",
  "observedAt": "2026-09-09T19:10:00Z",
  "source": "relay-anoat-7",
  "message": "Relay response within expected range"
}
```

Las solicitudes `GET` y `PATCH` no requieren un cuerpo. Los códigos de estado HTTP forman parte del contrato: las creaciones exitosas responden con `201`; las lecturas y actualizaciones exitosas, con `200`; la consulta de un experimento inexistente, con `404`; y los conflictos de estado o duplicación, con `409`.

El sistema utiliza una única table. El atributo `experimentId` actúa como partition key y agrupa todos los items de un experimento. El atributo `recordId` actúa como sort key, distingue los metadatos de las observaciones y mantiene estas últimas ordenadas:

| Tipo de item | `experimentId` | `recordId` |
| --- | --- | --- |
| Experimento | `<experimentId>` | `METADATA` |
| Observación | `<experimentId>` | `<observedAt>#<observationId>` |

La composición de `recordId` responde al patrón de acceso que requiere listar las observaciones en orden cronológico. `observedAt` aparece primero y utiliza el formato UTC `YYYY-MM-DDTHH:MM:SSZ`; por ello, el orden lexicográfico de la sort key coincide con el orden cronológico esperado. Si dos observaciones tienen la misma marca temporal, `observationId` evita que produzcan la misma primary key compuesta.

### 3. Crear la table DynamoDB

1. En el buscador superior busque y abra **DynamoDB**
2. Abra **Tables** y seleccione **Create table**
3. Configure:

   | Campo | Valor |
   | --- | --- |
   | Table name | `tel351-sap` |
   | Partition key | `experimentId` de tipo String |
   | Sort key | `recordId` de tipo String |

4. Conserve la opción **Default settings**, que configura la capacidad **On-demand**
5. Cree la table y espere hasta que su estado sea **Active**

### 4. Crear la Lambda function

#### 4.1 Crear la function e instalar el código inicial

Cree una Lambda function mediante **Lambda → Functions → Create function → Author from scratch**:

1. Ingrese `tel351-sap` en **Function name** y seleccione el runtime **Python 3.14**
2. Mantenga la opción que crea un execution role nuevo con permisos básicos para Lambda
3. Cree la function
4. Abra **Configuration → Environment variables → Edit**
5. Agregue `TABLE_NAME` con valor `tel351-sap` y guarde la configuración
6. Abra **Code → `lambda_function.py`**
7. Reemplace su contenido por [`assets/lambda_function.py`](assets/lambda_function.py) y seleccione **Deploy**

La function utiliza `event.routeKey` para seleccionar la operación correspondiente a cada solicitud. Las cinco `routes` comparten el mismo código, la misma variable de entorno y el mismo execution role.

#### 4.2 Autorizar las operaciones sobre la table

Construya una inline policy en el execution role de la function mediante el editor visual de IAM:

1. Abra **Configuration → Permissions** en `tel351-sap`
2. Seleccione el nombre del execution role para abrirlo en IAM
3. Seleccione **Add permissions → Create inline policy**
4. En el editor visual seleccione **DynamoDB** como servicio
5. En **Allowed actions**, seleccione `PutItem`, `GetItem`, `Query`, `UpdateItem` y `ConditionCheckItem`
6. En **Resources**, restrinja el permiso a la table `tel351-sap` creada en `sa-east-1`
7. Revise el resumen de permisos y compruebe que no existan otras acciones ni recursos DynamoDB autorizados
8. Ingrese `tel351-sap-dynamodb` como **Policy name**
9. Cree la policy

### 5. Importar y conectar la HTTP API

#### 5.1 Importar el contrato OpenAPI

1. Abra **API Gateway → APIs**
2. Seleccione **Create API**
3. En **HTTP API**, seleccione **Import**
4. Cargue [`assets/openapi.yaml`](assets/openapi.yaml)
5. Confirme que el nombre de la API sea `tel351-sap`
6. Complete la importación
7. Abra **Routes** y compruebe que existen las cinco combinaciones de `method` y `path` indicadas en la sección 2

La definición OpenAPI importa el contrato y las `routes`, pero no crea DynamoDB, Lambda ni sus permisos.

> API Gateway puede informar que los `schemas` de las solicitudes no se utilizan para validar una HTTP API. Continúe con la importación: estos `schemas` documentan el contrato y la Lambda function realiza la validación efectiva.

#### 5.2 Crear y asociar las integrations

Abra **Integrations → Manage integrations** y conecte las `routes` con la function:

1. Seleccione **Create** y cree una Lambda integration con `tel351-sap`
2. Asocie la integration a las cinco `routes` importadas
3. Confirme en **Integrations** que todas las `routes` utilizan `tel351-sap`
4. Abra **Stages**
5. Si no existe, cree el stage `$default` con **Auto-deploy** habilitado; si ya existe, confirme que mantenga esa configuración
6. Copie la **Invoke URL** y consérvela para realizar las pruebas en Postman

### 6. Completar las interacciones con DynamoDB

El archivo inicial permite observar resultados parciales antes de terminar toda la implementación. Trabaje sobre cada `TODO`, despliegue los cambios y utilice el sitio de evaluación para comprobar su efecto.

#### 6.1 Implementar la consulta de observaciones

La operación `list_observations` no se encuentra implementada. Escriba su contenido mediante `Query`, comenzando por importar `Key` desde `boto3.dynamodb.conditions`.

La consulta debe:

- Seleccionar la partition key `experimentId` recibida en la ruta
- Utilizar una lectura fuertemente consistente
- Entregar los items en orden ascendente de `recordId`
- Conservar en la respuesta solamente los items cuyo `entityType` sea `OBSERVATION`
- Responder con HTTP `200` y un objeto que contenga `experimentId` y la lista `observations`

`Scan` examinaría todos los items de la table antes de seleccionar los pertenecientes al experimento. `Query` utiliza directamente la partition key y limita la operación a la partición requerida. La policy autoriza `Query`, pero no `Scan`.

#### 6.2 Evitar el reemplazo de experimentos

`PutItem` reemplaza silenciosamente un item que ya utiliza la misma primary key. Modifique `create_experiment` para que la escritura se realice solamente cuando el item de metadatos todavía no existe.

La primera solicitud sobre un identificador debe responder con HTTP `201`. Una segunda solicitud con el mismo identificador debe conservar el item original y responder con HTTP `409`.

#### 6.3 Restringir el registro de observaciones

`add_observation` utiliza una transacción compuesta por un `ConditionCheck` sobre los metadatos y un `Put` para la observación. Analice ambas operaciones y complete sus condiciones para que:

- El experimento exista y su estado sea `OPEN`
- Una observación no reemplace otra con la misma primary key
- La comprobación y la escritura se apliquen o cancelen como una sola unidad

Una observación aceptada debe responder con HTTP `201`. Una observación repetida, asociada a un experimento inexistente o enviada después del cierre debe responder con HTTP `409`.

#### 6.4 Restringir la transición de cierre

`close_experiment` utiliza `UpdateItem`. Complete su expresión condicional para que la actualización solo pueda aplicarse a los metadatos de un experimento existente cuyo estado actual sea `OPEN`.

El primer cierre debe cambiar el estado a `CLOSED` y responder con HTTP `200`. Cerrar nuevamente el mismo experimento o cerrar uno inexistente debe responder con HTTP `409`.

## Limpieza posterior

Realice la limpieza después de completar la evaluación, fuera del bloque de clase si es necesario. No elimine el role `TEL351-Evaluator`, ya que se reutilizará en actividades posteriores.

### API Gateway

1. Abra **API Gateway → APIs**
2. Seleccione `tel351-sap`
3. Seleccione **Delete** y confirme

### Lambda function y CloudWatch Logs

1. Abra la Lambda function `tel351-sap`
2. En **Configuration → Permissions**, anote el nombre de su execution role
3. Elimine la function
4. Abra **CloudWatch → Log groups**
5. Elimine el log group `/aws/lambda/tel351-sap`
6. Abra **IAM → Roles** y elimine el execution role que anotó

### DynamoDB

1. Abra **DynamoDB → Tables**
2. Seleccione `tel351-sap`
3. Elimine la table y confirme escribiendo su nombre

### Verificación final

Confirme que la API, la Lambda function, su log group, su execution role y la table fueron eliminados. El role `TEL351-Evaluator` debe permanecer disponible.

## Apéndice: Referencia de interacciones con DynamoDB

Esta referencia resume las operaciones de DynamoDB utilizadas en el laboratorio. Los ejemplos emplean nombres genéricos: deben adaptarse al modelo de datos y al contrato de la API antes de incorporarlos a la Lambda function.

### Acceso mediante la interfaz de alto nivel

`boto3.resource("dynamodb")` entrega la interfaz de alto nivel del SDK. Al trabajar mediante un objeto `Table`, los valores de Python se convierten automáticamente al formato de atributos de DynamoDB.

```python
import boto3

table = boto3.resource("dynamodb").Table("nombre-table")
```

Las respuestas de las operaciones son diccionarios. Como los campos `Item` e `Items` no aparecen en todas las respuestas, `result.get("Item")` y `result.get("Items", [])` permiten procesarlas sin asumir que siempre estarán presentes.

### Escribir un item con PutItem

`put_item` crea un item o reemplaza completamente el que ya tenga la misma primary key.

```python
table.put_item(
    Item={
        "groupId": group_id,
        "recordId": record_id,
        "name": name,
    }
)
```

Para impedir un reemplazo accidental se agrega una expresión condicional mediante `ConditionExpression`. La escritura solo se realiza cuando la condición es verdadera.

```python
table.put_item(
    Item=item,
    ConditionExpression=(
        "attribute_not_exists(groupId) "
        "AND attribute_not_exists(recordId)"
    ),
)
```

Si la condición no se cumple, el SDK genera un `ClientError` cuyo código es `ConditionalCheckFailedException`.

### Obtener un item con GetItem

`get_item` requiere la primary key completa. En una table con partition key y sort key deben entregarse ambos atributos.

```python
result = table.get_item(
    Key={
        "groupId": group_id,
        "recordId": record_id,
    },
    ConsistentRead=True,
)

item = result.get("Item")
```

`ConsistentRead=True` solicita una lectura fuertemente consistente. Si el item no existe, la respuesta no contiene el campo `Item`.

### Consultar una partición con Query

`Query` recupera items a partir de un valor determinado de la partition key. Para construir su condición de clave mediante `KeyConditionExpression` se utiliza `Key` desde `boto3.dynamodb.conditions`.

```python
from boto3.dynamodb.conditions import Key

result = table.query(
    KeyConditionExpression=Key("groupId").eq(group_id),
    ConsistentRead=True,
    ScanIndexForward=True,
)

items = result.get("Items", [])
```

`ScanIndexForward=True` entrega los resultados en orden ascendente de sort key; `False` invierte ese orden. Cuando se necesita limitar un intervalo dentro de la partición, la condición también puede operar sobre la sort key:

```python
condition = (
    Key("groupId").eq(group_id)
    & Key("recordId").begins_with("PREFIX#")
)
```

Una condición de clave solo puede utilizar igualdad sobre la partition key y, opcionalmente, una condición admitida sobre la sort key. Los demás atributos no forman parte de la selección dirigida por la primary key.

Después de recibir los items, Python puede seleccionar un tipo de entidad y construir la representación que formará parte de la respuesta HTTP:

```python
records = [
    {
        name: item[name]
        for name in ("recordId", "value")
        if name in item
    }
    for item in items
    if item.get("entityType") == "DETAIL"
]
```

Esta selección no modifica los items almacenados ni ejecuta una segunda operación sobre DynamoDB.

### Examinar una table con Scan

`Scan` examina los items de la table sin exigir un valor de partition key. `Attr` permite construir una expresión de filtro mediante `FilterExpression` sobre atributos que no forman parte de la primary key.

```python
from boto3.dynamodb.conditions import Attr

result = table.scan(
    FilterExpression=(
        Attr("entityType").eq("DETAIL")
        & Attr("status").eq("OPEN")
    ),
    ProjectionExpression=(
        "groupId, recordId, entityType, #state"
    ),
    ExpressionAttributeNames={
        "#state": "status",
    },
)

items = result.get("Items", [])
matched_items = result.get("Count", 0)
examined_items = result.get("ScannedCount", 0)
```

En el ejemplo, `Items` contiene solamente los items que cumplen ambas condiciones. `Count` indica cuántos fueron incluidos en la respuesta y `ScannedCount` cuántos fueron examinados antes de aplicar el filtro.

Esta operación puede ser útil para inspecciones o procesos que realmente necesitan recorrer toda la table. No sustituye a `Query` cuando el patrón de acceso ya conoce la partition key: en ese caso examina datos que no pertenecen a la partición buscada y su costo crece con el tamaño total de la table.

Tanto `Query` como `Scan` admiten `FilterExpression`, pero el filtro se aplica después de leer los items. Por ello, un filtro puede reducir la cantidad de datos incluidos en la respuesta, pero no transforma un `Scan` en una consulta dirigida ni evita la lectura previa de los items descartados.

### Actualizar un item con UpdateItem

`update_item` modifica atributos específicos sin reemplazar el item completo. Los nombres que puedan coincidir con palabras reservadas se representan mediante `ExpressionAttributeNames`; los valores se entregan mediante `ExpressionAttributeValues`.

```python
result = table.update_item(
    Key={
        "groupId": group_id,
        "recordId": record_id,
    },
    UpdateExpression="SET #state = :new_state",
    ConditionExpression=(
        "attribute_exists(groupId) AND #state = :current_state"
    ),
    ExpressionAttributeNames={
        "#state": "status",
    },
    ExpressionAttributeValues={
        ":current_state": "OPEN",
        ":new_state": "CLOSED",
    },
    ReturnValues="ALL_NEW",
)

updated_item = result["Attributes"]
```

`ReturnValues="ALL_NEW"` hace que DynamoDB devuelva el item después de aplicar la actualización. Si la condición no se cumple, la actualización no se realiza y se genera `ConditionalCheckFailedException`.

### Ejecutar operaciones como una transacción

El cliente de bajo nivel permite ejecutar `transact_write_items`. Todas las operaciones de la transacción se aplican juntas o se cancelan en su conjunto.

```python
from boto3.dynamodb.types import TypeSerializer

dynamodb = boto3.client("dynamodb")
serializer = TypeSerializer()


def serialize_map(value):
    return {
        name: serializer.serialize(item)
        for name, item in value.items()
    }
```

La serialización es necesaria porque el cliente de bajo nivel recibe valores con el formato de DynamoDB, como `{"S": "OPEN"}`, en lugar de valores nativos de Python.

```python
dynamodb.transact_write_items(
    TransactItems=[
        {
            "ConditionCheck": {
                "TableName": table_name,
                "Key": serialize_map(metadata_key),
                "ConditionExpression": "#state = :expected",
                "ExpressionAttributeNames": {
                    "#state": "status",
                },
                "ExpressionAttributeValues": {
                    ":expected": {"S": "OPEN"},
                },
            }
        },
        {
            "Put": {
                "TableName": table_name,
                "Item": serialize_map(new_item),
                "ConditionExpression": (
                    "attribute_not_exists(groupId) "
                    "AND attribute_not_exists(recordId)"
                ),
            }
        },
    ]
)
```

Si falla cualquiera de las condiciones, ningún cambio se aplica y el SDK genera `TransactionCanceledException`.

### Procesar resultados paginados

`Query` y `Scan` devuelven una página de hasta 1 MB por llamada. Si la respuesta contiene `LastEvaluatedKey`, aún quedan items por recuperar. La llamada siguiente debe incluir este valor como `ExclusiveStartKey`.

```python
items = []
arguments = {
    "KeyConditionExpression": Key("groupId").eq(group_id),
}

while True:
    result = table.query(**arguments)
    items.extend(result.get("Items", []))

    if "LastEvaluatedKey" not in result:
        break

    arguments["ExclusiveStartKey"] = result["LastEvaluatedKey"]
```

En conjuntos pequeños puede no aparecer paginación, pero una implementación general no debe asumir que una sola respuesta contiene todos los resultados.
