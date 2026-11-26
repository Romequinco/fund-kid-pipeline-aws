# Registro de decisiones del proyecto

Formato ligero tipo ADR, como en los talleres de RL. ID `D-X.n`: `X` es la fase del pipeline (0 general,
1 captura y almacenamiento, 2 extracción, 3 base de datos, 4 API y aplicación, 5 infraestructura y despliegue) y `n`
un correlativo. El estado es `ABIERTA` o `CERRADA`. Las decisiones se añaden al final de su bloque.

---

### D-0.1 · Arquitectura de referencia como punto de partida

- **Fecha:** 2026-11-19
- **Decisión:** se sigue la arquitectura de referencia del enunciado (§6). Cualquier pieza que se cambie deja aquí su
  justificación, porque el enunciado lo permite "siempre que se justifiquen" y la exposición la pregunta.
- **Estado:** CERRADA

### D-0.2 · Región de AWS

- **Fecha:** 2026-11-19
- **Contexto:** el curso usa `eu-west-3` (París) por defecto. En clase se habilitó también `eu-north-1` (Estocolmo)
  para quien no podía seleccionar París. Bedrock no ofrece todos los modelos en todas las regiones, y en la UE se
  accede a muchos con perfiles de inferencia entre regiones (`eu.`).
- **Alternativas:** `eu-west-3`, `eu-north-1` o `eu-central-1`, según qué modelo de Bedrock quede disponible con salidas
  estructuradas.
- **Decisión (2026-11-26):** `eu-west-3` (París). Es la del curso y la de la solución de referencia, el modelo elegido
  (D-2.2) funciona desde ahí, y el bootstrap (bucket del estado, OIDC y rol de GitHub) ya está creado en ella.
- **Estado:** CERRADA

### D-0.3 · Un paquete común como única fuente de verdad

- **Fecha:** 2026-11-19
- **Decisión:** la lógica vive en `src/kid_pipeline/` (captura, S3, extracción, base de datos). `src/pipeline.py` la
  ejecuta por lotes, y `src/api.py` y `src/dashboard.py` son capas finas que se despliegan como imágenes. Así se prueba
  sin AWS y no se duplica código entre el lote, la API y la aplicación.
- **Estado:** CERRADA

### D-0.4 · Sin credenciales en el repositorio

- **Fecha:** 2026-11-19
- **Decisión:** en local, `aws login` (como en el curso). En GitHub Actions, **OIDC** con un rol limitado a este
  repositorio. La contraseña de la base de datos la gestiona RDS en Secrets Manager. La configuración no secreta (nombres
  de bucket, ARN, región) entra por variables de entorno y `.env.example` documenta cuáles.
- **Estado:** CERRADA

### D-0.5 · Estructura compacta: tres carpetas

- **Fecha:** 2026-11-19
- **Decisión:** como en los talleres de RL, tres carpetas. `src/` contiene todo el código y sus tests (un fichero, como
  `notebooks/common/test_common.py`, con las páginas web guardadas que usa en `src/fixtures/`); `infra/` contiene
  Terraform y los Dockerfiles; `docs/` contiene las decisiones y la teoría. Las dependencias de cada imagen son *extras* de `pyproject.toml` (`api`, `dashboard`, `dev`), sin un
  `requirements.txt` por servicio, y un único workflow de AWS (`deploy.yml`) despliega y ejecuta el lote.
- **Estado:** CERRADA

---

### D-1.1 · Captura responsable

- **Fecha:** 2026-11-19
- **Decisión:** respetar `robots.txt`, identificarse con un `User-Agent` propio, hacer una pausa entre peticiones y
  descargar solo los PDF públicos del KID. Para cada documento se guarda su origen (URL de la ficha y del PDF) y cuándo
  se descargó (exigido por el enunciado, §4).
- **Detalle:** `urllib.robotparser` no entiende comodines, así que `SesionEducada` comprueba aparte los `Disallow` con
  `*` o `$` (RFC 9309).
- **Detalle (19/11/2026):** la pausa de 2 s por servidor se aplica también a la petición de `robots.txt` y a cada
  reintento. Se reintentan los fallos de red, los 5xx y el 429 (respetando `Retry-After`, con un tope de 60 s), con
  espera creciente; el `timeout` separa conexión (10 s) y lectura (30 s).
- **Estado:** CERRADA

### D-1.2 · Identidad del documento e idempotencia

- **Fecha:** 2026-11-19
- **Decisión:** el documento se identifica por el **SHA-256 del PDF**. La clave en S3 y la fila en la base de datos se
  derivan de él, así que procesar dos veces el mismo PDF no crea duplicados. Si una gestora publica un KID nuevo para
  el mismo ISIN, es otro documento: se conserva el histórico.
- **Estado:** CERRADA

### D-1.3 · Bestinver prohíbe los PDF en su robots.txt

- **Fecha:** 2026-11-19
- **Contexto:** el robots.txt de Bestinver tiene `Disallow: /*.pdf$` para todos los agentes (comprobado el 19/11/2026).
  Con la regla de D-1.1, el scraper se negará a descargar sus KID. Además, Azvalor respondió HTTP 418 a la petición
  automática, y sus fichas cuelgan hoy de `/fondos-de-inversion/`, no de `/fondos/` como dice el enunciado.
- **Alternativas:** usar Cobas y Azvalor como las dos fuentes mínimas; preguntar en el Taller 1 cómo lo trata la
  solución de referencia; o buscar los mismos KID en otra fuente pública (CNMV, plataformas de distribución).
- **Decisión (Taller 1, 19/11/2026):** el profesor confirmó en clase que se pueden descargar los PDF de Bestinver, y
  su solución de referencia lo hace. `Bestinver.respeta_robots = False` es una excepción **solo para esa fuente** y
  sus PDF de www.bestinver.es (un PDF enlazado en otro dominio pasa por el robots.txt de ese dominio), con el motivo
  guardado en el manifiesto de cada documento (`robots`). El resto de la cortesía se mantiene: User-Agent
  propio que identifica el proyecto, pausa de 2 s por servidor, una descarga por documento y ningún intento de
  saltarse bloqueos. El KID es un documento que la gestora está obligada a publicar en su web (Reglamento PRIIPs).
- **Azvalor:** su `robots.txt` devuelve 418, que según el RFC 9309 (un 4xx) permite el acceso; sus fichas responden
  con normalidad al User-Agent propio.
- **Estado:** CERRADA

### D-1.4 · Qué se captura de cada gestora

- **Fecha:** 2026-11-19
- **Decisión:**
  - **Bestinver:** todas las fichas de `/fondos-de-inversion/` salvo 5 páginas informativas. Una clase por ficha.
  - **Azvalor:** sus 5 fondos.
  - **Cobas:** los fondos y la SICAV de `/productos/inversion-libre/`, un KID por clase. Los planes de pensiones se
    excluyen porque publican otro documento, no un KID PRIIPs.
- **Evidencia (captura real del 19/11/2026):** 49 KID (22 de Bestinver, 5 de Azvalor y 22 de Cobas), sin errores ni
  duplicados. En los 43 con ISIN en la web, ese ISIN aparece dentro del PDF. Las 6 fichas de Bestinver sin ISIN (bonos
  institucionales y Sharpe High Yield) no lo muestran en la web. La ficha `bestinver-bonos-institucional` no enlaza KID.
- **Para el Taller 2:** los PDF de Cobas son el KID (3 páginas) más un anexo de escenarios y rentabilidades pasadas
  (8-9 páginas en total). La extracción debe tomar los datos del KID, no del anexo.
- **Ampliación (19/11/2026): todas las clases de Bestinver.** 8 fondos de Bestinver tienen varias clases (B, R, X, Z;
  Sharpe High Yield: A2, B2, Z2) con una ficha por clase (`...-clase-r/`) que no está en el listado, sino en el menú de
  la ficha principal. Se siguen esos enlaces (solo los rotulados «Clase X» bajo `/fondos-de-inversion/`): 19 KID más,
  41 en Bestinver. Las fichas de clase no muestran el ISIN; lo da el PDF (`isin_pdf`, D-1.5).
- **Evidencia (segunda captura real, 19/11/2026):** 68 KID (41 de Bestinver, 5 de Azvalor y 22 de Cobas), sin errores
  ni duplicados; frente a la primera, 19 nuevos y 49 sin cambios. `verificar` da OK: los 68 son KID PRIIPs con un
  ISIN (43 de la web, todos dentro del PDF, y 25 solo del PDF), las 47 clases de la web coinciden con la del PDF y las
  5 fechas de Azvalor aparecen en su PDF. Los tres servidores envían `ETag` y `Last-Modified`.
- **Revisión de los 49 PDF del 19/11:** los 49 son KID PRIIPs (indicador resumido de riesgo) y cada uno trae un solo
  ISIN. `ES_KIID-BESTINVER-SHARPE-HIGH-YIELD-CL-B2.pdf` es un KID PRIIPs en español pese al nombre (SICAV
  luxemburguesa, ISIN `LU3334273896`, clase B2, sociedad gestora Waystone; la etiqueta «Nombre del producto del PRIIP» trae por
  error el nombre de Bestinver). `..._datos_fundamentales.pd_.pdf` es el KID de Bestinver Corto Plazo clase B: solo
  cambia la extensión.
- **Estado:** CERRADA

### D-1.5 · El PDF se lee al capturarlo: procedencia completa y nada que no sea un KID

- **Fecha:** 2026-11-19
- **Contexto:** 6 fichas de Bestinver no muestran el ISIN, pero el PDF sí lo trae; un enlace con el rótulo esperado
  podría apuntar a otro documento (folleto, informe), y el Taller 2 necesita saber qué ISIN y qué clase esperar.
- **Decisión:** al descargar, `capture.huella` lee el texto con pypdf y el manifiesto guarda `isin_pdf`, `paginas` y
  `tipo_documento` («KID PRIIPs» si tiene el indicador resumido de riesgo; «KIID UCITS» si es el DFI antiguo). Un
  PDF legible sin las marcas del KID, o con más de 12 páginas, se rechaza con un error en el informe. La web sigue
  mandando (`isin_web`): `isin_pdf` solo la completa y la contrasta.
- **Parseo común a las tres fuentes:** el enlace se reconoce por su rótulo normalizado (sin tildes ni mayúsculas:
  «Datos fundamentales», «DFI», «KID», «PRIIP», «DFP», «Folleto simplificado») o, si el rótulo no dice nada, por el
  nombre del fichero; se descartan los rótulos de otros documentos («Folleto completo», «Informe», «Escenarios»). A
  cada KID se le asigna el ISIN de su bloque solo si el bloque tiene un único ISIN y un único KID: con dos KID y un
  ISIN se deja a null en vez de adivinar. La clase sale del nombre del PDF (`clase_b`, `Clase+A`, `CL-B2`), del bloque
  o de la URL de la ficha.
- **Estado:** CERRADA

### D-1.6 · Capturas incrementales y aviso de cambios

- **Fecha:** 2026-11-19
- **Decisión:** cada manifiesto es una foto de lo que publicaba cada gestora capturada. Al capturar se compara con la
  última foto de esa gestora (local o en S3) y se informa de los KID **nuevos**, **cambiados** (mismo ISIN, o misma
  URL si no hay ISIN, con otro SHA-256) y **desaparecidos** (solo si la gestora se capturó sin errores). Es la base de
  la ampliación «alertas cuando cambia un KID».
- **Peticiones condicionales:** el manifiesto guarda `etag` y `last_modified` de cada PDF, y la siguiente captura lo
  pide con `If-None-Match` / `If-Modified-Since`. Con un 304 se reutiliza la copia guardada si su SHA-256 coincide
  (si no, descarga normal); la línea del manifiesto conserva el `descargado_en` original y añade `comprobado_en` y
  `http: 304`. Menos carga para las gestoras y la misma trazabilidad.
- **Evidencia (tercera captura real, 19/11/2026):** los 68 PDF respondieron 304 (ninguno se volvió a bajar), 0
  errores; frente a la anterior, 0 nuevos, 0 cambiados, 68 sin cambios y 0 desaparecidos. `verificar` sigue en OK.
- **`verificar`:** la integridad (fichero, SHA-256, PDF, clave) se comprueba en todo el histórico; el contenido, en lo
  vigente: ISIN de la web dentro del PDF y coincidente con `isin_pdf`, clase de la web en la sección «Producto» del
  PDF, fecha del nombre del PDF dentro del PDF, y cada ISIN y cada clase una sola vez.
- **Estado:** CERRADA

---

### D-2.1 · Forma de la salida estructurada en Bedrock

- **Fecha:** 2026-11-19
- **Contexto:** el enunciado exige salidas estructuradas (esquema JSON o herramientas en modo estricto), no pedir "JSON"
  y parsear el texto.
- **Alternativas** (confirmadas en la documentación de la Converse API, ver
  [06_piezas_de_la_practica.md](teoria/06_piezas_de_la_practica.md) §4):
  - Formato de respuesta: `outputConfig.textFormat` con `type: json_schema` y el esquema como cadena.
  - Herramienta en modo estricto: `toolSpec.strict: true` con `inputSchema.json`, y `toolChoice: {tool: {name}}`
    para forzar su uso.
- **Decisión (2026-11-20):** herramienta estricta (`toolSpec.strict: true`, `toolChoice: {tool: {name}}`): la
  respuesta llega como objeto en `toolUse.input`. `extract.peticion(..., mecanismo="formato")` deja implementada la
  alternativa (`outputConfig.textFormat` con `json_schema`) por si el modelo elegido no acepta `toolChoice.tool`.
- **Esquema:** sale de `schema.Kid` adaptado al modo estricto (`additionalProperties: false`, sin `minimum`/`maximum`,
  SRI como `enum` 1-7). `schema.comprobar_estricto` comprueba en los tests que cumple los límites: 20 propiedades,
  0 opcionales (máximo 12) y 10 uniones (máximo 16). Los rangos los valida Pydantic al leer la respuesta.
- **Entrada:** el modelo recibe el Markdown del KID (D-2.3), no el PDF. Se mira `stopReason`: con `max_tokens` el JSON
  llega incompleto y se descarta.
- **Solución de referencia del profesor:** LangChain (`ChatBedrockConverse.with_structured_output`, método
  `json_schema`) sobre el Markdown, con un modelo de terceros en `eu-west-3`. Usamos boto3 directamente: una
  dependencia menos y el mecanismo de salida estructurada a la vista.
- **Estado:** ABIERTA hasta comprobar `toolChoice.tool` con el modelo real (D-2.2)

### D-2.2 · Modelo de Bedrock

- **Fecha:** 2026-11-19
- **Alternativas:** el modelo es libre. Criterios: salidas estructuradas en la región elegida, coste por documento
  (entrada de unos 4-6 mil tokens de Markdown por KID) y precisión en el conjunto de referencia (D-2.5).
- **Dato:** la solución de referencia del profesor usa un perfil de inferencia `global.` en `eu-west-3`, lo que apunta a
  que París sirve como región (D-0.2).
- **Cómo se elige:** `pipeline.py evaluar --predicciones data/extraccion/<modelo>.jsonl` compara cada candidato con la
  referencia y con las reglas, sin volver a llamar a Bedrock.
- **Qué permite la cuenta del máster** (probado en `eu-west-3` el 26/11/2026):
  - Bloqueados ("not available for this account"): Anthropic, OpenAI, xAI y Z.AI. Se contratan por AWS Marketplace,
    que la cuenta no permite.
  - Nova (Amazon) y Mistral: responden, pero no admiten `strict` ni `outputConfig`. Solo tienen herramienta sin modo
    estricto, que no cumple la regla 5 del enunciado.
  - **Kimi K3.1 (Moonshot):** admite la herramienta estricta y `outputConfig`, pero no `temperature`.
    `extract.LIMITACIONES` lo recoge.
- **Evidencia** (los 68 KID; los 17 de referencia, D-2.5):

  | | Kimi K3.1 (`global.`) | Nova 2 Lite (`eu.`, sin modo estricto) | Reglas |
  |---|---|---|---|
  | Exactitud en la referencia | **170/170** | 159/170 (un SRI 7 en lugar de 5 y un KID vacío) | 170/170 |
  | Evidencias que aparecen y cuadran | **680/680** | 443/670 | — |
  | ISIN y clase frente al manifiesto | 68/68 y 47/47 | 58/67 (9 KID sin datos) y 38/46 | 68/68 y 47/47 |
  | Fallos | 0 | 1 (respuesta en bucle, cortada por `maxTokens`) | 0 |
  | Tiempo medio por KID | 7,4 s | 4,0 s | < 0,1 s |
  | Coste aproximado de los 68 KID | ~3,5 $ (6,5 mil tokens de entrada y ~1,9 mil de salida por KID) | céntimos | 0 |

- **Decisión (2026-11-26):** **Kimi K3.1** (`global.moonshotai.kimi-k3.1`), el modelo de la solución de referencia.
  Es el único de la cuenta que cumple la regla 5, y acierta todo con sus evidencias. Que Kimi, las reglas y la
  referencia anotada a mano coincidan en los 170 campos, siendo tres fuentes independientes, refuerza también la
  referencia.
- **Coste asumido:** el perfil `global.` puede procesar los datos fuera de la UE. Son documentos públicos, así que es
  aceptable, pero un modelo con perfil `eu.` lo evitaría si la cuenta lo permitiera.
- **Estado:** CERRADA

### D-2.3 · El modelo lee el Markdown de las páginas del KID

- **Fecha:** 2026-11-20
- **Decisión:** `texto.kid_markdown` convierte el PDF a Markdown con `pymupdf4llm`, como la solución de referencia, que
  conserva títulos, listas y las tablas de costes y escenarios. Solo se convierten las **3 primeras páginas**: el
  Reglamento PRIIPs limita el KID a 3 caras A4, y Cobas añade en el mismo PDF un anexo de escenarios y rentabilidades
  pasadas que el modelo no debe leer.
- **Evidencia:** los 46 KID de Bestinver y Azvalor tienen 3 páginas, y en los 22 de Cobas la página 4 empieza el anexo.
  Los 68 tienen capa de texto: no hace falta OCR, a diferencia de la solución de referencia (RapidOCR). Conversión: 68 de
  68, 1-2,5 s por KID.
- **Cómo se usa:** `pipeline.py markdown` deja la caché en `data/markdown/<gestora>/<sha256>.md`. `pipeline.extract`
  convierte cada PDF de S3 antes de llamar a Bedrock.
- **Coste asumido:** PyMuPDF tiene licencia AGPL, aceptable en un proyecto académico de código abierto.
- **Estado:** CERRADA

### D-2.4 · Evidencias literales por campo

- **Fecha:** 2026-11-20
- **Contexto:** la salida estructurada asegura la forma, no el contenido (06 §4.4). La solución de referencia acompaña
  cada campo con el fragmento del documento del que sale y comprueba que ese fragmento está en el texto.
- **Alternativas:**
  - (a) Un objeto por campo `{evidencia, valor}`.
  - (b) Un objeto `evidencias` con los 10 fragmentos.
  - (c) Campos planos `<campo>_evidencia`.

  Con evidencias que admiten null, (b) y (c) suman 20 uniones, por encima del límite de 16 del modo estricto. (a)
  cumple, pero añade 10 objetos anidados.
- **Decisión:** (c). Cada evidencia es una cadena que no admite null (vacía si el dato no aparece) y va justo antes de
  su campo, para que el modelo cite primero y extraiga después: 20 propiedades, 0 opcionales y 10 uniones.
- **Comprobación:** tras extraer, `extract.revisar` mira dos cosas por campo:
  - Que la evidencia aparece en el Markdown, sin formato, tildes ni espacios.
  - Que el valor está dentro de ella: el número del SRI o del porcentaje, la fecha, el ISIN o el nombre. Un 0 % cuadra
    con «no se cobra».

  Se guarda en `kid.evidencias` (JSONB), con `evidencias_ok` como resumen. Una evidencia que no cuadra se registra,
  no se corrige: es la lista de KID que hay que revisar a mano.
- **Estado:** CERRADA (se revisa con los resultados de Bedrock real)

### D-2.5 · Extractor por reglas y conjunto de referencia

- **Fecha:** 2026-11-20
- **Contexto:** la ampliación del enunciado pide «comparar la calidad de extracción de varios modelos» y «medir la
  precisión con un conjunto de KID revisados a mano». Hace falta una referencia fija y una línea base sin coste.
- **Decisión:**
  - **Extractor:** `kid_pipeline/reglas.py` extrae los 10 campos del Anexo A con expresiones regulares sobre el
    Markdown del KID (D-2.3). Cada campo se busca con varias pistas y queda a null si no hay ninguna o se contradicen.
    Es la línea base frente a la que se mide Bedrock, y una segunda opinión.
  - **Referencia:** `data/referencia.json` tiene 17 KID de las tres gestoras. No se versiona, porque los datos solo se
    exponen por la API y la aplicación. Cubre varias clases de Bestinver y Cobas, los tres Sharpe High Yield
    luxemburgueses, renta fija, comisiones de entrada y salida distintas de 0 y un KID con el periodo contradictorio.
    Cada valor guarda su fragmento del KID y la página del PDF.
  - **Evaluador:** `pipeline.py evaluar` compara cualquier extractor (las reglas o un JSONL por modelo en
    `data/extraccion/`) campo a campo, con tolerancia de 0,01 en números y comparación normalizada en textos. En los 68
    KID comprueba además el ISIN y la clase frente al manifiesto y la cobertura por campo.
- **Criterios de anotación:**
  - Nombre tal y como aparece, sin la clase. Clase como «Clase X», o null.
  - Gestora = productor del PRIIP o «Entidad».
  - Gastos corrientes = solo comisiones de gestión y costes administrativos, en %.
  - Costes de entrada y salida = el % del cuadro de costes únicos, 0 si dice que no se cobran.
- **Evidencia (20/11/2026):** las reglas aciertan 170 de 170 campos de la referencia y, en los 68 KID, el ISIN (68/68)
  y la clase (47/47) del manifiesto, con cobertura completa salvo la clase (47/68; los demás no tienen clase).
  **Ese 100 % está sobreajustado:** las reglas se escribieron estudiando estos mismos 68 Markdown, y la referencia la
  anotó la misma persona. Vale como línea base, no como estimación de lo que generaliza.
- **Pendiente:** que el grupo confirme la referencia (`revisado_por`), en especial:
  - La gestora de los Sharpe: Bestinver como productor o Waystone como sociedad gestora; se aceptan ambas.
  - La salida de Azvalor: 0 % en el cuadro, 3 % en el texto para menos de un año.
  - La salida de Cobas: 4 % para menos de un año.
  - Las comisiones temporales de los Bonos Institucional.
- **Modelos (26/11/2026):** Kimi K3.1 también acierta 170/170 y Nova 2 Lite 159/170 (tabla en D-2.2).
- **Estado:** ABIERTA (se cierra cuando el grupo confirme la referencia)

---

### D-3.1 · Motor de base de datos

- **Fecha:** 2026-11-19
- **Contexto:** la referencia es Aurora PostgreSQL Serverless v2 con RDS Data API: no hace falta VPC ni driver desde
  Lambda, y escala a cero si se pausa.
- **Alternativas:** RDS PostgreSQL clásico con conexión por VPC.
- **Comprobado (26/11/2026):** la Data API acepta el secreto que gestiona RDS (`manage_master_user_password`):
  `init-db` y `cargar` funcionan con él. Aurora Serverless v2 tardó unos 7 minutos en crearse. Con `min_capacity = 0`
  se pausa sola, y la primera consulta tras la pausa tarda más mientras despierta.
- **Decisión:** Aurora PostgreSQL Serverless v2 con Data API, como la referencia.
- **Estado:** CERRADA

---

### D-4.1 · La aplicación solo lee de la API

- **Fecha:** 2026-11-19
- **Decisión:** Streamlit consulta la API HTTP y no accede a la base de datos ni a S3. Cumple la regla 5 (los datos solo
  se exponen por la API y la aplicación) y deja una única puerta de acceso a los datos.
- **Estado:** CERRADA

### D-4.2 · FastAPI en Lambda con Mangum e imagen de contenedor

- **Fecha:** 2026-11-19
- **Decisión:** la API se empaqueta como imagen (`public.ecr.aws/lambda/python:3.13`), como en las lecciones 18 y 22
  del curso, y Mangum traduce el evento de la Function URL a ASGI. La imagen evita el problema de compilar dependencias
  para Linux desde Windows (lección 13).
- **Alternativa descartada por ahora:** AWS Lambda Web Adapter, que ejecuta uvicorn sin tocar el código pero añade una
  capa más que explicar.
- **Estado:** CERRADA (se revisa si el Taller 2 usa otra opción)

---

### D-5.1 · Terraform en dos raíces

- **Fecha:** 2026-11-19
- **Decisión:** `infra/bootstrap/` crea, una sola vez y desde local, el bucket del estado, el proveedor OIDC y el rol de
  GitHub. `infra/` contiene todo lo demás y lo aplica GitHub Actions con el estado en S3 (`use_lockfile`).
- **Por qué:** el rol con el que Actions se autentica no puede crearse desde el propio Actions.
- **Aprendido en el primer despliegue (26/11/2026):**
  - **Sujeto inmutable de GitHub.** GitHub firma el token OIDC con el sujeto inmutable, que lleva los ID numéricos del
    usuario y del repositorio (`repo:Romequinco@236243639/fund-kid-pipeline-aws@1464495334:…`). La condición de
    confianza acepta ese formato y el antiguo. Es más seguro: un repositorio nuevo con el mismo nombre tendría otros ID.
  - **Rol vinculado al servicio ECS.** En una cuenta que nunca ha usado ECS, ECS Express falla con «Unable to assume
    the service linked role». AWS lo crea en el primer intento, pero no a tiempo. El bootstrap lo declara
    (`aws_iam_service_linked_role.ecs`), y aquí se importó porque ya existía.
- **Estado:** CERRADA

### D-5.2 · Coste de los servicios con precio por hora

- **Fecha:** 2026-11-19
- **Contexto:** ECS Express cuesta del orden de 2-3 $ al día (curso, lección 17), y Aurora cobra por capacidad mientras
  no se pausa.
- **Alternativas:** desplegar solo para las pruebas y la exposición, y apagarlo con `terraform destroy` el resto del
  tiempo, o mover la aplicación a una opción sin coste fijo.
- **Primer despliegue (26/11/2026):** 19 recursos. El cuadro de mando tardó unos 15 minutos en responder la primera
  vez, mientras se creaban el balanceador y el certificado HTTPS. `DESPLEGAR=true` está activado: cada push que toque
  `src/`, `infra/` o `pyproject.toml` vuelve a desplegar. Para dejar de pagar el cuadro de mando sin borrar los datos:
  `terraform -chdir=infra apply -var desplegar_dashboard=false` (o ponerlo en el workflow).
- **Interruptor (2026-11-26):** `deploy.yml` no despliega ni corre el lote hasta que exista la variable de repositorio
  `DESPLEGAR=true`. Con el rol de GitHub ya creado, cualquier push a `main` desplegaría si no. La variable `desplegar_dashboard` permite apagar solo el
  cuadro de mando, y Aurora se pausa sola a los 10 minutos sin uso (`min_capacity = 0`).
- **Estado:** ABIERTA

### D-5.3 · Permisos del rol de GitHub

- **Fecha:** 2026-11-19
- **Decisión provisional:** `PowerUserAccess` + `IAMFullAccess`, porque `infra/` crea roles y Terraform necesita
  gestionarlos. La confianza ya está limitada a este repositorio (`repo:Romequinco/fund-kid-pipeline-aws:*`).
- **Pendiente:** el curso pide, "para nota", limitar los permisos a los recursos propios (lección 28). Opción: una
  política propia por prefijo `fund-kid-*` y restringir la condición a la rama `main`.
- **Estado:** ABIERTA

### D-5.4 · Terraform como único dueño del despliegue

- **Fecha:** 2026-11-19
- **Decisión:** las imágenes se etiquetan con el SHA del commit y esa etiqueta entra en Terraform
  (`api_image_tag`, `dashboard_image_tag`). `deploy.yml` crea primero los repositorios ECR con `-target`, sube las
  imágenes y aplica el resto. No se usa `aws lambda update-function-code` ni la action de ECS Express, porque el
  siguiente `apply` desharía su cambio.
- **Estado:** CERRADA
