# Datos y documentos: DynamoDB, Athena, Textract y el proyecto final del curso

> **Fuentes:**
> - **L24** = `docs/raw/miax-cloud-main/content/24-dynamodb.md` (Amazon DynamoDB), completa: de «Conceptos» a «Limpieza: Aurora».
> - **L25** = `docs/raw/miax-cloud-main/content/25-athena.md` (Amazon Athena), completa.
> - **L26** = `docs/raw/miax-cloud-main/content/26-textract.md` (Amazon Textract), completa, incluida la actividad de créditos de Bedrock.
> - **L28** = `docs/raw/miax-cloud-main/content/28-proyecto.md` (Proyecto final), completa.
> - **L02** = `docs/raw/miax-cloud-main/content/02-cuenta-costes.md`, solo la tabla de actividades de créditos (qué lección acompaña a cada actividad).
> - **EJ** = `docs/raw/miax-cloud-main/ejemplos/`: `dynamodb/1_crear_tabla.py`, `2_cargar_datos.py`, `3_leer_datos.py`; `athena/consulta.py`; `textract/run_textract.py`; y de `textract/salida/` solo la **estructura** de `1.json` y `2.json` (claves, tipos y recuento de bloques) y las líneas de texto que contienen.
> - **DATOS** = `docs/raw/miax-cloud-main/market_data/market_data_proc.csv` (recuentos hechos aquí con pandas).
> - **CAMBIOS** = `docs/raw/miax-cloud-main/CAMBIOS.md` (revisión del material del 08/11/2026): tablas «Cambios por obsolescencia» y «Errores corregidos».
> - **T13**, **T14** = `docs/raw/transcripciones/T13.txt` y `T14.txt`, transcripciones automáticas de las clases del 13 y 14/11/2026. Se han buscado con grep los términos DynamoDB, Athena, Textract, Bedrock, Aurora, PostgreSQL, NoSQL, PDF, scraping, IA y práctica; tramos útiles en §1.
> - **ENUNCIADO** = `docs/raw/transcripciones/enunciado.txt` (práctica B7). **DEC** = `docs/DECISIONES.md`.
> - Web: **[AWS DynamoDB componentes]** = https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html ; **[AWS Athena precios]** = https://aws.amazon.com/athena/pricing/ ; **[AWS Textract Block]** = https://docs.aws.amazon.com/textract/latest/dg/API_Block.html (enlazada desde L26).
>
> **Convenciones:** "(L24 «Clave principal»)" = diapositiva de la lección 24 citada por su título (cada `---` del Markdown es una diapositiva). "(EJ dynamodb/2_cargar_datos.py)" = fichero de ejemplo. "(T14 ~04:43)" = hora aproximada en la transcripción, siempre **paráfrasis** de un texto automático muy ruidoso; lo que no se entiende bien va marcado *(dudoso)*. **Nota:** = contenido propio (cálculos, conexiones, advertencias), no del material de clase. A fecha de este documento **ninguno de estos cuatro temas se ha dado en clase** (§1); todo sale de las diapositivas publicadas y de los ejemplos. Lo que la práctica necesita y el curso no cubre (KID, scraping, Bedrock, Aurora con Data API, FastAPI en Lambda) está en [06_piezas_de_la_practica.md](06_piezas_de_la_practica.md).
>
> Escrito el 19/11/2026.

---

## 1. Dónde encaja este bloque

**Idea.** Las lecciones 24 a 28 cierran el curso con tres servicios de datos (una base de datos NoSQL, SQL sobre ficheros y extracción de documentos) y un proyecto que los integra con Lambda, S3 y despliegue automático. La práctica B7 usa otras piezas (PostgreSQL y Bedrock), pero los patrones son los mismos.

| Lección | Servicio | Qué resuelve | ¿Visto en clase a 19/11? | Actividad de créditos asociada (L02) |
|---|---|---|---|---|
| L24 | DynamoDB | Base de datos clave-valor gestionada, sin servidor | No | Crear una base de datos Aurora o RDS (20 $) |
| L25 | Athena | SQL sobre ficheros en S3 | No | — |
| L26 | Textract | Texto, tablas y formularios de PDF e imágenes | No | Usar un modelo en Bedrock (20 $) |
| L28 | Proyecto final | Integración Lambda + S3 + DynamoDB (+ Textract) + CI/CD | No | — |

Qué hay en las transcripciones (grep en T13 y T14):

- **Ni DynamoDB, ni Athena, ni Textract aparecen** en ninguna de las dos clases. Tampoco "NoSQL".
- **La práctica, adelantada** (T14 ~04:42:20-04:43:50): el profesor anuncia que dará una descripción breve del entregable y que se irá montando en los dos primeros talleres; en el tercero cada grupo presenta en 5-10 minutos. Lo centrará en casos de uso de **scraping de datos desestructurados**, que se procesarán **con inteligencia artificial** para extraer la información posible, se guardarán y se servirán a través de una página web. Es exactamente el ENUNCIADO.
- **Secretos para claves de modelos** (T14 ~01:10:35-01:11:32): una clave de API de un proveedor de modelos no debe ir en una variable de entorno sino guardarse como **secreto** (cifrado, con acceso controlado), sobre todo en producción; se verá más adelante. Conecta con el secreto de la base de datos gestionado por RDS ([06](06_piezas_de_la_practica.md), §5.3).
- **Bedrock, de pasada** (T13 ~00:14:37-00:14:52): al repasar servicios que conocían los alumnos, el profesor relaciona SageMaker con "la parte de IA" de Amazon y comenta que los nombres cambian a menudo *(dudoso: la frase mezcla SageMaker y Bedrock como si uno fuera el nombre antiguo del otro; no lo son, son servicios distintos)*.
- **PostgreSQL, de pasada** (T13 ~02:48:20-02:49:01): al hablar de puertos, cita que una base de datos PostgreSQL o MySQL usa un puerto reservado *(dudoso: se oye "5, 4, 3, 2"; el de PostgreSQL es el 5432)*.

**Nota:** las dos actividades de créditos de estas lecciones son justo las piezas de la práctica que no tienen lección propia: la de L24 lanza una **Aurora sin servidor** (L24 «Ejercicio: Aurora») y la de L26 prueba un **modelo fundacional en Bedrock** (L26 «Ejercicio: Bedrock»). Merece la pena hacerlas antes del Taller 2, y borrar la base de datos al terminar, porque "se cobra por hora mientras exista" (L24 «Limpieza: Aurora»).

---

## 2. DynamoDB: tablas, elementos y clave principal

**Idea.** DynamoDB es una base de datos NoSQL gestionada de baja latencia (L24, portada). Solo la clave principal tiene esquema; el resto de atributos puede variar de un elemento a otro.

| Concepto | Qué es (L24 «Conceptos») | Equivalente relacional aproximado (**Nota**) |
|---|---|---|
| Tabla | Colección de elementos | Tabla |
| Elemento | Grupo de atributos con clave única | Fila |
| Atributo | Dato individual | Columna, pero sin esquema fijo |
| Índice secundario | Otra forma de consultar | Índice, pero con su propia clave |

- "Excepto la clave principal, la tabla **no tiene esquema**" (L24 «Conceptos»); la diapositiva «Elementos sin esquema fijo» lo ilustra con una tabla *People* en la que cada persona tiene atributos distintos (imagen de la documentación de AWS).
- La documentación añade que los atributos pueden anidarse hasta 32 niveles y que las claves solo pueden ser de tipo cadena, número o binario [AWS DynamoDB componentes].

### 2.1 Clave simple y clave compuesta

| Tipo | Composición | Ejemplo de clase |
|---|---|---|
| Simple | Clave de partición | `usuario_id` |
| Compuesta | Partición + ordenación | `VALOR` + `TIME_ID` |

(L24 «Clave principal».)

- La **clave de partición** decide dónde se guarda el elemento; la **de ordenación** ordena los elementos de una misma partición (L24 «Clave principal»). La documentación lo concreta: el valor de la partición pasa por una función hash interna que elige la partición física, y todos los elementos con la misma partición se guardan juntos y ordenados por la clave de ordenación; por eso a la partición también se la llama *hash attribute* y a la ordenación *range attribute* (`HASH` y `RANGE` en el código) [AWS DynamoDB componentes].
- **No puede haber dos elementos con la misma clave: el segundo sobrescribe al primero** (L24 «Clave principal»). Esta frase es la que explica el error de §4.
- Aviso de la lección: "Diseña primero las consultas": en DynamoDB la tabla se modela a partir de cómo se va a leer (L24 «Clave principal»).

**Nota:** en una base relacional se modela la entidad y luego se escriben las consultas que hagan falta; en DynamoDB, si una consulta no encaja en la clave (o en un índice secundario), hay que recorrer la tabla entera. Esta es la principal razón por la que la práctica, que pide filtrar y comparar fondos por varios criterios, usa PostgreSQL (§9).

---

## 3. Crear, escribir y leer: modo bajo demanda, `Decimal` y `query`

**Idea.** El curso usa el modo de capacidad **bajo demanda** para no tener que dimensionar lecturas y escrituras, y lee siempre por clave con `query`.

- **Bajo demanda** es el modo por defecto en la consola, se ajusta solo y no obliga a decidir unidades de lectura y escritura (L24 «Modo de capacidad»). Es uno de los cambios del material revisado: la versión original usaba **capacidad aprovisionada** (CAMBIOS, «DynamoDB»).

```python
table = boto3.resource("dynamodb", region_name=REGION).create_table(
    TableName="MARKET_DATA",
    KeySchema=[{"AttributeName": "VALOR", "KeyType": "HASH"},
               {"AttributeName": "TIME_ID", "KeyType": "RANGE"}],
    AttributeDefinitions=[{"AttributeName": "VALOR", "AttributeType": "S"},
                          {"AttributeName": "TIME_ID", "AttributeType": "S"}],
    BillingMode="PAY_PER_REQUEST",
)
table.wait_until_exists()
```

(EJ dynamodb/1_crear_tabla.py, con `REGION = "eu-west-3"`; la diapositiva hace lo mismo con la tabla *Movies*, `year` numérico y `title` texto.)

- Solo se declaran en `AttributeDefinitions` los atributos que forman parte de una clave; el resto (`VOLUMEN`, `PRECIO`) se añade al escribir. `BillingMode="PAY_PER_REQUEST"` es el modo bajo demanda.
- **boto3 no admite `float`: hay que usar `Decimal`** (L24 «Insertar y leer»). El ejemplo de carga convierte con `Decimal(str(fila["PRECIO"]))` (EJ dynamodb/2_cargar_datos.py).
- `put_item` escribe, `get_item` lee un elemento por su clave completa y `query` lee todos los de una partición con `KeyConditionExpression=Key("year").eq(2015)`. **Prefiere `query` a `scan`**, que recorre y cobra toda la tabla (L24 «Insertar y leer»).
- La demo de consola crea la tabla *Movies* y añade un elemento a mano desde **Explore table items** (L24 «Demo en la consola»).

**Nota:** el paso por `str` antes de `Decimal` importa: `Decimal(5.41)` conserva el error binario del `float` (`5.4100000000000001421...`), mientras que `Decimal("5.41")` es exacto. El mismo cuidado vale para los porcentajes de costes de la práctica: en PostgreSQL, `NUMERIC` y no `double precision` ([06](06_piezas_de_la_practica.md), §5.4).

---

## 4. El error corregido: la carga de market data y `TIME_ID`

**Idea.** La primera versión del ejercicio usaba `TIME` como clave de ordenación y **perdía casi la mitad de las filas** sin dar ningún error, porque cada escritura con una clave repetida sobrescribía la anterior. La corrección añade un número de secuencia a la clave.

### 4.1 Qué pasaba

- El fichero `market_data_proc.csv` tiene columnas `VALOR, VOLUMEN, PRECIO, TIME` (DATOS) y **16.769 filas, pero solo 8.544 combinaciones distintas de `VALOR` y `TIME`**: muchas operaciones son del mismo instante (L24 «Ejercicio», aviso «Una trampa en estos datos»).
- Con `VALOR` + `TIME` como clave, las filas del mismo instante tienen la misma clave y la última escritura gana: quedarían 8.544 elementos y se perderían 8.225 filas (un 49 %). CAMBIOS lo recoge como primer "error corregido": "perdía casi la mitad de las filas (16.769 filas, 8.544 claves únicas). Se añade `TIME_ID`".
- Ejemplo real, primeras filas del CSV: diez operaciones de SAN a 5,41 € con la misma marca `2018-03-19 09:00:18.002` y volúmenes 1, 44, 20, 45... (DATOS). Con la clave antigua, de esas diez solo sobreviviría una.

### 4.2 La corrección

```python
with table.batch_writer() as lote:
    for i, fila in enumerate(registros):
        lote.put_item(Item={
            "VALOR": fila["VALOR"],
            "TIME_ID": f"{fila['TIME']}#{i:06d}",
            "VOLUMEN": int(fila["VOLUMEN"]),
            "PRECIO": Decimal(str(fila["PRECIO"])),
        })
```

(L24 «Carga por lotes»; EJ dynamodb/2_cargar_datos.py lo aplica a todo el CSV leído con pandas.)

- `TIME_ID` = marca de tiempo + `#` + número de fila con seis dígitos, p. ej. `2018-03-19 09:00:18.002#000003` (el formato `TIME#000123` del enunciado del ejercicio) (L24 «Ejercicio»).
- Con `batch_writer` el código se escribe como si fueran `put_item` individuales (L24 «Carga por lotes»). Según la guía de boto3, el objeto agrupa las escrituras en lotes y reenvía automáticamente los elementos que DynamoDB devuelva sin procesar (https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html).
- El ejercicio pide comprobar que al leer SAN llegan **9.585 filas** (L24 «Ejercicio», paso 5).

### 4.3 Leer con paginación

`query` devuelve los resultados por páginas: mientras la respuesta traiga `LastEvaluatedKey`, hay que repetir la llamada pasándola como `ExclusiveStartKey` (EJ dynamodb/3_leer_datos.py). Sin ese bucle, el recuento de SAN saldría por debajo de 9.585 y parecería que la carga ha fallado.

**Nota (comprobación propia).** Con pandas: SAN = 9.585 filas y TEF = 7.184; total 16.769 (DATOS). La suma cuadra con L24.

**Nota (por qué funciona y qué enseña).**
- El orden se conserva: la parte de la marca de tiempo va delante y tiene longitud fija, así que el orden lexicográfico de `TIME_ID` es el cronológico, y el sufijo solo desempata operaciones del mismo instante. Un rango de horas se puede leer con `Key("TIME_ID").between(...)`.
- **La clave es idempotente solo si el fichero no cambia.** Volver a cargar el mismo CSV en el mismo orden genera las mismas claves y sobrescribe con los mismos valores; pero si el CSV llega reordenado o con una fila nueva en medio, las secuencias se desplazan y la misma operación recibe otra clave: duplicados sin error. Una clave que no dependa del orden (un hash del contenido, o un identificador de la operación si el mercado lo da) es más robusta. La práctica aplica esa idea con el **SHA-256 del PDF** como identidad del documento (DEC D-1.2) y la remata en la base de datos con `INSERT ... ON CONFLICT` ([06](06_piezas_de_la_practica.md), §6).
- **La sobrescritura silenciosa es el riesgo, no el `put_item`.** Ni DynamoDB ni el lote avisan; solo lo detecta comparar recuentos de entrada y de salida. Es la comprobación mínima de cualquier carga de la práctica: documentos descargados = documentos en S3 = filas en PostgreSQL.

**Limpieza:** borrar las tablas al terminar (L24 «Carga por lotes»).

---

## 5. Athena: SQL directamente sobre S3

**Idea.** Athena ejecuta SQL sobre ficheros que ya están en S3, sin servidores ni carga previa: la tabla es solo una descripción de cómo leerlos (L25 «Cómo funciona»).

Flujo: ficheros en S3 (CSV, Parquet...) → tabla (define el esquema) → Athena (consulta SQL) → resultado (L25 «Cómo funciona»).

| Aspecto | Qué dice el curso |
|---|---|
| Precio | Por datos escaneados: 5 $ por TB en la mayoría de regiones (L25 «Cómo funciona») |
| Cómo pagar menos | Parquet y particiones: se lee menos (L25 «Cómo funciona») |
| Copia de datos | Ninguna: la tabla solo describe cómo leerlos (L25 «Cómo funciona») |
| Ruta | Athena lee **todo** lo que haya bajo la ruta: cada tabla en su carpeta (L25 «Preparar los datos») |
| Resultados | Se guardan en un bucket propio que se indica en **Edit settings** (L25 «Preparar los datos») |

- La página de precios añade que S3 cobra aparte sus tarifas de almacenamiento, peticiones y transferencia [AWS Athena precios].

### 5.1 La tabla y la cabecera del CSV

```sql
CREATE EXTERNAL TABLE miax.market_data (
  valor string, volumen int, precio double, `time` string
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
LOCATION 's3://miax-<alias>-datos/athena/market/'
TBLPROPERTIES ('skip.header.line.count' = '1');
```

(L25 «Crear la tabla»; antes, `CREATE DATABASE IF NOT EXISTS miax;`, y cada sentencia se ejecuta por separado.)

- `TBLPROPERTIES ('skip.header.line.count' = '1')` es la corrección de CAMBIOS: "Athena: se ignora la cabecera del CSV" (CAMBIOS, «Errores corregidos»).
- `time` va entre comillas invertidas porque es palabra reservada (L25 «Crear la tabla»).

**Nota (qué pasaba sin esa propiedad).** La línea `VALOR,VOLUMEN,PRECIO,TIME` se leería como un dato más: una fila con `valor = 'VALOR'` y `volumen` y `precio` nulos (el texto no se convierte a `int` ni a `double`). El `count(*)` daría 16.770 y el `GROUP BY valor` mostraría un tercer grupo espurio "VALOR". Es el mismo tipo de error que el de §4: no falla nada, simplemente el resultado está mal.

**Nota (dos detalles que no salen en la lección).** (1) En las consultas `SELECT`, a diferencia de la DDL, los identificadores reservados se escriben entre comillas dobles (`"time"`), no invertidas. (2) `ROW FORMAT DELIMITED` corta por cada coma y no entiende campos entrecomillados que contengan comas; el CSV de market data no los tiene, pero un CSV con nombres de fondos como "Fondo X, FI" sí los tendría *(por verificar qué SerDe de Athena conviene en ese caso)*.

### 5.2 Consultas y Python

```sql
SELECT valor, count(*) AS operaciones, sum(volumen) AS volumen,
       sum(precio * volumen) / sum(volumen) AS vwap
FROM miax.market_data GROUP BY valor;
```

(L25 «Consultas»: bajo el resultado la consola muestra los **datos escaneados**.)

- Desde Python, `pyathena` con `PandasCursor` devuelve un `DataFrame`; necesita `s3_staging_dir` (el bucket de resultados) y la región (L25 «Desde Python»; EJ athena/consulta.py).
- Ejercicio: crear la tabla, calcular el precio medio por valor en la consola y repetirlo en Python; limpieza: `DROP TABLE` y vaciar el bucket de resultados (L25 «Ejercicio»).

**Nota:** la consulta es el **VWAP** por valor: precio medio ponderado por volumen, la misma métrica que en los talleres de ejecución del máster. Con Athena se calcula sin cargar nada en una base de datos.

---

## 6. Textract: texto, tablas y formularios de un PDF

**Idea.** Textract es un servicio de extracción *especializado*: devuelve en JSON lo que hay en la página (líneas, palabras, tablas, pares clave-valor) con su posición y su confianza, pero no interpreta qué significa cada dato (L26 «Qué ofrece»).

| Operación | Devuelve (L26 «Qué ofrece») |
|---|---|
| Detect Document Text | Líneas y palabras |
| Analyze Document | Además tablas, formularios y consultas |
| Analyze Expense | Facturas y recibos |
| Analyze ID | Documentos de identidad |

- Capa gratuita solo tres meses para clientes nuevos: 1.000 páginas al mes con Detect Document Text y 100 con tablas o formularios (L26 «Qué ofrece», nota).
- Aviso: probar con documentos ficticios o públicos, nunca el DNI ni datos personales (L26 «Qué ofrece»). En coherencia, el ejemplo original con un DNI se cambió por un documento genérico (CAMBIOS, «Decisiones de publicación»).
- Demo sin programar: abrir Textract, subir un PDF de pocas páginas y revisar las pestañas de texto, tablas y formularios (L26 «Demo»).

### 6.1 Síncrono o asíncrono

| Modo | Para | API |
|---|---|---|
| Síncrono | Una imagen o un PDF de una página | `detect_document_text`, `analyze_document` |
| Asíncrono | PDF de varias páginas en S3 | `start_...` y `get_...` |

(L26 «Síncrono o asíncrono».) **El bucket debe estar en la misma región en la que se llama a Textract** (misma diapositiva).

### 6.2 Análisis asíncrono

```python
trabajo = textract.start_document_text_detection(
    DocumentLocation={"S3Object": {"Bucket": BUCKET, "Name": DOCUMENTO}})
job_id = trabajo["JobId"]
while True:                                   # sondeo cada 3 s
    resultado = textract.get_document_text_detection(JobId=job_id)
    if resultado["JobStatus"] != "IN_PROGRESS":
        break
    time.sleep(3)
if resultado["JobStatus"] != "SUCCEEDED":
    raise RuntimeError(resultado.get("StatusMessage", resultado["JobStatus"]))
```

(EJ textract/run_textract.py; la diapositiva L26 «Análisis asíncrono» es la misma sin la comprobación de `SUCCEEDED`.)

- Después se recorren los bloques `LINE` y, si la respuesta trae `NextToken`, se pide la página siguiente de resultados con `get_document_text_detection(JobId=..., NextToken=...)` (EJ textract/run_textract.py; L26 «Análisis asíncrono»).
- **En producción, una notificación de SNS en lugar de consultar en bucle** (L26 «Análisis asíncrono»).
- Para tablas y formularios: `start_document_analysis(..., FeatureTypes=["TABLES", "FORMS"], OutputConfig={"S3Bucket": ..., "S3Prefix": "textract/"})`; con `OutputConfig` Textract guarda además el JSON del resultado en el bucket (L26 «Tablas y formularios, con salida a S3»).
- Ejercicio: subir un PDF público, extraer el texto, repetir con `FeatureTypes=["TABLES"]` y buscar las tablas entre los bloques (L26 «Ejercicio»). Las tablas aparecen como bloques `TABLE` cuyas celdas son bloques `CELL` relacionados, con su fila y columna; los formularios, como `KEY_VALUE_SET` [AWS Textract Block].

**Nota:** el sondeo con `time.sleep` dentro de una Lambda consume tiempo facturado y choca con el límite de 15 minutos; por eso el aviso de SNS. El mismo razonamiento aplica a cualquier trabajo largo de la práctica: un script por lotes (referencia del ENUNCIADO, §6) puede esperar; una Lambda conviene que no.

---

## 7. Lo que enseña la salida de ejemplo: un KIID visto por Textract

**Idea.** El PDF de ejemplo del curso es, casualmente, el antepasado directo del documento de la práctica: un **"Key Investor Information"** de un fondo UCITS indexado (ISIN IE00B03HCZ61, fechado a 15/02/2022), es decir, el KIID/DFI que el KID sustituyó en 2023 ([06](06_piezas_de_la_practica.md), §2.6). Su salida muestra qué da Textract y qué no.

### 7.1 Estructura de los JSON (EJ textract/salida)

| Clave de primer nivel | `1.json` | `2.json` |
|---|---|---|
| `JobStatus` | `SUCCEEDED` | `SUCCEEDED` |
| `DetectDocumentTextModelVersion` | `1.0` | `1.0` |
| `DocumentMetadata` | objeto | objeto |
| `NextToken`, `StatusMessage`, `Warnings` | nulos | nulos |
| `Blocks` (recuento) | 1.000: 2 `PAGE`, 162 `LINE`, 836 `WORD` | 734: 65 `LINE`, 669 `WORD` |
| Páginas cubiertas | 1 y 2 | 2 |

- Cada bloque lleva `BlockType`, `Id`, `Page`, `Text`, `Confidence` y `Geometry` (caja `BoundingBox` y `Polygon` en coordenadas relativas a la página) (EJ textract/salida; [AWS Textract Block]).
- Al ser `Detect Document Text`, no hay bloques `TABLE` ni `KEY_VALUE_SET`.

**Nota:** el primer fichero se corta en 1.000 bloques exactos y el segundo continúa la página 2: es la paginación de la salida que se guarda con `OutputConfig` (§6.2). Quien lea solo `1.json` pierde un tercio del documento, el equivalente del `LastEvaluatedKey` de §4.3.

### 7.2 Cuatro problemas para extraer campos (observación propia sobre las líneas)

1. **El indicador de riesgo se queda sin respuesta.** Tras «Risk and reward profile» aparecen siete líneas `1`, `2`, ..., `7`, todas con confianza 100. La categoría del fondo es la casilla **resaltada**, y el resaltado no es texto: Textract no dice cuál es.
2. **Las dos columnas se entremezclan.** El orden de lectura alterna frases de la columna izquierda («The Fund employs a passive management...») y de la derecha («Portfolio transaction costs will have an impact...»).
3. **Etiquetas y valores son líneas sueltas.** «Entry charge», «None», «from their distributor.», «Exit charge», «None»; más abajo, «Ongoing charges» y «0.18%». Entre medias se cuelan frases de la columna explicativa («The ongoing charges figure is based on expenses for the year ended 31...»). Que `0.18%` sea el valor de los gastos corrientes solo se deduce por el orden o por la posición en la página.
4. **El ruido gráfico entra como texto.** La primera línea es una `R` con confianza 48,8: un trozo del logotipo.

**Nota:** con `FeatureTypes=["TABLES", "FORMS"]` mejorarían el 3 y quizá el 2, pero el 1 seguiría igual, y quedaría escribir reglas para convertir "None" en 0 o en `null`, distinguir euros de porcentajes y adaptar todo eso a cada gestora. Es el argumento central de §9.

---

## 8. El proyecto final del curso

**Idea.** L28 propone integrar Lambda, S3, DynamoDB y despliegue automático en uno de dos casos de uso, con criterios de calidad explícitos. CAMBIOS aclara que **el proyecto final no tiene solución publicada** (CAMBIOS, «Decisiones de publicación»).

| | Caso 1: tipos de cambio | Caso 2: documentos |
|---|---|---|
| Flujo | EventBridge Scheduler (diario) → Lambda → BCE → S3 (CSV) → DynamoDB (histórico) | PDF en bucket S3 → Lambda → Textract → DynamoDB (datos extraídos) |
| Disparador | Programación diaria | Subida de un documento al bucket |
| Pasos | Obtener los tipos de referencia del BCE; guardar un CSV en S3 y los datos en DynamoDB en cada ejecución; programar con Scheduler; permisos del rol; repositorio con despliegue por OIDC | Función que se ejecuta al subir un documento; lanzar Textract; guardar una parte del resultado en DynamoDB; permisos del rol; repositorio con despliegue por OIDC |
| Fuente | L28 «Caso de uso 1: tipos de cambio» | L28 «Caso de uso 2: documentos» |

**Criterios de calidad** (L28 «Criterios de calidad»):

- **Permisos**: se puede empezar con `AmazonS3FullAccess`, `AmazonDynamoDBFullAccess` o `AmazonTextractFullAccess`; para nota, limitarlos a los recursos propios.
- **Sin secretos en Git**: variables de entorno y OIDC.
- **Lógica separada** del controlador y con tests.
- **Timeout y memoria** ajustados.
- **Extra**: toda la infraestructura con Terraform.
- Al entregar, borrar la programación, las funciones, las tablas y los buckets.

Dos correcciones de CAMBIOS que afectan directamente al caso 2 (CAMBIOS, «Errores corregidos»): en una Lambda con disparador S3 la clave del objeto llega codificada y hay que decodificarla con `unquote_plus` (un PDF llamado `DFP Internacional.pdf` llega como `DFP+Internacional.pdf`), y hay que evitar **bucles recursivos** (una función que escribe en el mismo bucket y prefijo que la disparan se vuelve a invocar a sí misma).

**Nota:** el caso 2 es el esqueleto de B7 con dos piezas cambiadas (Bedrock por Textract y PostgreSQL por DynamoDB) y dos añadidas (la captura por scraping antes y la API con la aplicación después). Los criterios de L28 coinciden casi uno a uno con las reglas del ENUNCIADO (§5) y con DEC D-0.3 (lógica en un paquete común) y D-0.4 (sin credenciales, OIDC). El enunciado no dice que B7 sustituya al proyecto de L28; se trata aquí como su antecedente.

---

## 9. Para la práctica

### 9.1 Por qué PostgreSQL y Bedrock, y no DynamoDB y Textract

La elección no es libre: el ENUNCIADO exige "PostgreSQL en AWS" y "un modelo de Amazon Bedrock con salidas estructuradas" (§1 y §4 del ENUNCIADO). Pero conviene saber justificarla en la exposición, porque la pregunta "¿por qué no lo que vimos en el curso?" es previsible.

| Necesidad de B7 | Con DynamoDB / Textract | Con PostgreSQL / Bedrock |
|---|---|---|
| Filtrar y comparar fondos por gestora, SRI, costes, periodo (API y aplicación) | Cada patrón de consulta exige diseñar su clave o un índice secundario (§2.1); lo demás es `scan` (§3) | `WHERE`, `ORDER BY`, `GROUP BY` y `JOIN` sobre cualquier columna |
| Evitar duplicados si un documento se procesa dos veces | Hay que construir una clave idempotente a mano (§4.4); la sobrescritura es silenciosa | Restricción `UNIQUE` + `INSERT ... ON CONFLICT` atómico ([06](06_piezas_de_la_practica.md), §6) |
| Tipos y validación (SRI entero 1-7, porcentajes) | Sin esquema salvo la clave; `Decimal` en el cliente | Tipos `SMALLINT`, `NUMERIC`, `DATE` y `CHECK` en la propia tabla |
| Leer el SRI resaltado, emparejar etiqueta y valor, distinguir € de % | No lo resuelve: devuelve texto y posiciones (§7.2) | El modelo recibe el PDF y responde con los campos del Anexo A según un esquema |
| Gestoras con maquetaciones distintas | Reglas por gestora, frágiles ante cambios | Un mismo esquema y un mismo prompt para todas; el enunciado pide `null` si el campo no está |
| Coste fijo | DynamoDB bajo demanda: sin coste fijo | Aurora cobra por capacidad mientras no se pausa (DEC D-3.1, D-5.2; [06](06_piezas_de_la_practica.md), §5.4) |

**Nota:** la última fila es la única en la que gana la opción del curso. Por eso la arquitectura de referencia usa Aurora Serverless v2 con **auto-pausa**, que acerca su coste en reposo a cero.

### 9.2 Qué se reaprovecha de estas lecciones

- **Organización en S3 y misma región**: el bucket de los PDF en la región de los servicios que lo leen (L26 «Síncrono o asíncrono»); una carpeta por conjunto de datos, porque los servicios que leen una ruta leen todo lo que cuelga de ella (L25 «Preparar los datos»).
- **Identidad e idempotencia**: la lección de `TIME_ID` (§4) es la de DEC D-1.2: el identificador no puede depender del orden de proceso; el SHA-256 del PDF sí lo cumple.
- **Comprobar recuentos en cada salto** (descargados, subidos a S3, extraídos, cargados), como el "comprueba que llegan las 9.585 filas" de L24.
- **Paginación** (§4.3, §7.1): toda API que devuelva listas puede devolverlas por páginas; vale también para listar objetos de S3.
- **Números exactos**: `Decimal(str(x))` en Python y `NUMERIC` en PostgreSQL para porcentajes de costes (§3).
- **Patrones de Lambda + S3** del caso 2 (§8), con `unquote_plus` y sin bucles recursivos, si se elige la ampliación "arquitectura por eventos (S3 → Lambda)" del ENUNCIADO.
- **Permisos mínimos** y limpieza al terminar (L28 «Criterios de calidad»).
- **Textract como línea base** para la ampliación "comparar la calidad de extracción de varios modelos" del ENUNCIADO: su texto plano frente a la salida estructurada de Bedrock, medidos contra KID revisados a mano.
- **Athena para auditar** (opcional): si el manifiesto de descargas se guarda en S3 como CSV o JSON, una tabla externa permite consultarlo con SQL sin tocar la base de datos.

---

## 10. Preguntas de repaso

1. En una tabla de DynamoDB con clave compuesta `VALOR` + `TIME`, ¿qué ocurre al escribir dos operaciones de SAN con la misma marca de tiempo? ¿Por qué no salta ningún error?
2. El `TIME_ID` de la corrección conserva el orden cronológico dentro de cada valor. ¿Por qué? ¿En qué situación dejaría de ser idempotente una recarga del CSV?
3. ¿Qué diferencia hay entre `query` y `scan`, y por qué el curso recomienda el primero? ¿Qué pasa si se ignora `LastEvaluatedKey`?
4. ¿Qué devolvería `SELECT count(*) FROM miax.market_data` si la tabla de Athena se hubiera creado sin `skip.header.line.count`? ¿Y el `GROUP BY valor`?
5. ¿Cuándo se usa la API síncrona de Textract y cuándo la asíncrona? ¿Qué requisito de región impone la asíncrona y por qué se recomienda SNS en producción?
6. En la salida de ejemplo, ¿por qué Textract extrae las siete cifras del indicador de riesgo pero no permite saber cuál es la del fondo?
7. Enumera tres necesidades de la práctica B7 que resuelve mejor PostgreSQL que DynamoDB y una en la que DynamoDB es mejor.
8. ¿Qué dos correcciones de CAMBIOS afectan a una Lambda disparada por la subida de un PDF a S3?
