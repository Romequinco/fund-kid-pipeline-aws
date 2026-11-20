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
- **Estado:** ABIERTA (se cierra al elegir el modelo, D-2.2)

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
- **Decisión provisional (2026-11-19):** herramienta estricta (`extract.py`). El esquema sale de `schema.Kid` pero se
  adapta al modo estricto (`additionalProperties: false`, sin `minimum`/`maximum`); los rangos los valida Pydantic al
  leer la respuesta.
- **Por verificar en el Taller 2:** que `toolChoice.tool` funcione con el modelo elegido y la versión mínima de boto3.
- **Estado:** ABIERTA (se cierra con la solución de referencia del Taller 2)

### D-2.2 · Modelo de Bedrock

- **Fecha:** 2026-11-19
- **Alternativas:** el modelo es libre. Criterios: que admita PDF como entrada y salidas estructuradas en la región
  elegida, su coste por documento y su precisión en un conjunto de KID revisados a mano (ampliación del enunciado).
- **Estado:** ABIERTA

---

### D-3.1 · Motor de base de datos

- **Fecha:** 2026-11-19
- **Contexto:** la referencia es Aurora PostgreSQL Serverless v2 con RDS Data API: no hace falta VPC ni driver desde
  Lambda, y escala a cero si se pausa.
- **Alternativas:** RDS PostgreSQL clásico con conexión por VPC.
- **Por verificar:** que la Data API acepte el secreto que gestiona RDS (`manage_master_user_password`, nombre
  `rds!cluster-...`). Los ejemplos de AWS usan un secreto propio; si falla, se crea el secreto en Terraform.
- **Estado:** ABIERTA (pendiente de ver el coste real con los créditos de la cuenta)

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
- **Estado:** CERRADA

### D-5.2 · Coste de los servicios con precio por hora

- **Fecha:** 2026-11-19
- **Contexto:** ECS Express cuesta del orden de 2-3 $ al día (curso, lección 17), y Aurora cobra por capacidad mientras
  no se pausa.
- **Alternativas:** desplegar solo para las pruebas y la exposición, y apagarlo con `terraform destroy` el resto del
  tiempo, o mover la aplicación a una opción sin coste fijo. La variable `desplegar_dashboard` permite apagar solo el
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
