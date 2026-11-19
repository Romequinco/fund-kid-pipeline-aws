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
- **Decisión:** la lógica vive en `src/kid_pipeline/` (captura, S3, extracción, base de datos). `scripts/` la ejecuta por
  lotes, y `api/` y `dashboard/` son capas finas que se despliegan como imágenes. Así se prueba sin AWS y no se
  duplica código entre el lote, la API y la aplicación.
- **Estado:** CERRADA

### D-0.4 · Sin credenciales en el repositorio

- **Fecha:** 2026-11-19
- **Decisión:** en local, `aws login` (como en el curso). En GitHub Actions, **OIDC** con un rol limitado a este
  repositorio. La contraseña de la base de datos la gestiona RDS en Secrets Manager. La configuración no secreta (nombres
  de bucket, ARN, región) entra por variables de entorno y `.env.example` documenta cuáles.
- **Estado:** CERRADA

---

### D-1.1 · Captura responsable

- **Fecha:** 2026-11-19
- **Decisión:** respetar `robots.txt`, identificarse con un `User-Agent` propio, hacer una pausa entre peticiones y
  descargar solo los PDF públicos del KID. Para cada documento se guarda su origen (URL de la ficha y del PDF) y cuándo
  se descargó (exigido por el enunciado, §4).
- **Estado:** CERRADA

### D-1.2 · Identidad del documento e idempotencia

- **Fecha:** 2026-11-19
- **Decisión:** el documento se identifica por el **SHA-256 del PDF**. La clave en S3 y la fila en la base de datos se
  derivan de él, así que procesar dos veces el mismo PDF no crea duplicados. Si una gestora publica un KID nuevo para
  el mismo ISIN, es otro documento: se conserva el histórico.
- **Estado:** CERRADA

---

### D-2.1 · Forma de la salida estructurada en Bedrock

- **Fecha:** 2026-11-19
- **Contexto:** el enunciado exige salidas estructuradas (esquema JSON o herramientas en modo estricto), no pedir "JSON"
  y parsear el texto.
- **Alternativas:** formato de respuesta con esquema JSON en la Converse API, o una herramienta con `inputSchema` y
  `toolChoice` forzado. El esquema sale en los dos casos de un único modelo Pydantic (`schema.py`).
- **Estado:** ABIERTA (se cierra en el Taller 2 con la solución de referencia)

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
- **Estado:** ABIERTA (pendiente de ver el coste real con los créditos de la cuenta)

---

### D-4.1 · La aplicación solo lee de la API

- **Fecha:** 2026-11-19
- **Decisión:** Streamlit consulta la API HTTP y no accede a la base de datos ni a S3. Cumple la regla 5 (los datos solo
  se exponen por la API y la aplicación) y deja una única puerta de acceso a los datos.
- **Estado:** CERRADA

---

### D-5.1 · Terraform en dos raíces

- **Fecha:** 2026-11-19
- **Decisión:** `infra/bootstrap/` crea, una sola vez y desde local, el bucket del estado, el proveedor OIDC y el rol de
  GitHub. `infra/main/` contiene todo lo demás y lo aplica GitHub Actions con el estado en S3 (`use_lockfile`).
- **Por qué:** el rol con el que Actions se autentica no puede crearse desde el propio Actions.
- **Estado:** CERRADA

### D-5.2 · Coste de los servicios con precio por hora

- **Fecha:** 2026-11-19
- **Contexto:** ECS Express cuesta del orden de 2-3 $ al día (curso, lección 17), y Aurora cobra por capacidad mientras
  no se pausa.
- **Alternativas:** desplegar solo para las pruebas y la exposición, y apagarlo con `terraform destroy` el resto del
  tiempo, o mover la aplicación a una opción sin coste fijo.
- **Estado:** ABIERTA
