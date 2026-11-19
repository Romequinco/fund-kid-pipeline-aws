<div align="center">

# Fund KID Pipeline AWS

**Del KID en PDF al cuadro de mando: pipeline de datos de fondos de inversión en AWS con IA generativa**

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-S3%20·%20Bedrock%20·%20Aurora%20·%20Lambda%20·%20ECS-FF9900?logo=amazonwebservices&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-OIDC-2088FF?logo=githubactions&logoColor=white)
![Estado](https://img.shields.io/badge/estado-en%20curso-D9A400)

Máster MIAX · Módulo Cloud · Práctica B7 · Noviembre 2026<br>
Óscar Romero Quincoces · Fernando Dapena Tauste · Daniel García López

</div>

---

## El problema

Todo fondo que se vende a minoristas en la UE publica un **KID** (*Key Information Document*): unas tres páginas con
el ISIN, la gestora, el indicador de riesgo (SRI 1-7), el periodo de mantenimiento recomendado y los costes. La
información existe, pero está encerrada en PDF dispersos por la web de cada gestora y con formatos distintos.

Este repositorio la saca de ahí: **captura** los KID de varias gestoras, los guarda en **S3**, extrae sus campos con
un modelo de **Amazon Bedrock con salidas estructuradas**, los carga en **PostgreSQL** sin duplicados y los sirve con
una **API** y una **aplicación web**. Toda la infraestructura se define con **Terraform** y se despliega desde
**GitHub Actions**.

## Enunciado (resumen)

| Fase | Mínimo exigido |
|---|---|
| Captura | KID de al menos **2 fuentes** y **15 documentos**, con origen y fecha de descarga de cada uno |
| Almacenamiento | PDF en Amazon S3 |
| Extracción con IA | Campos del Anexo A con un modelo de Bedrock y **salidas estructuradas** (no "devuelve JSON" y parsear) |
| Base de datos | PostgreSQL en AWS, **sin duplicados** si un documento se procesa dos veces |
| API | API HTTP sobre los datos |
| Visualización | Aplicación web para explorarlos |
| Infraestructura | Terraform desplegado desde GitHub Actions |

**Campos mínimos (Anexo A):** `isin`, `nombre_producto`, `nombre_clase`, `gestora`, `fecha_documento`, `sri`,
`periodo_mantenimiento_anios`, `gastos_corrientes_pct`, `costes_entrada_pct`, `costes_salida_pct`. Si un campo no
aparece en el KID queda a `null`: el modelo no lo inventa.

**Fuentes de los talleres:** Bestinver (dificultad baja), Azvalor (media) y Cobas AM (media-alta).

**Reglas:** sin credenciales en el repositorio, y los datos y documentos solo se exponen a través de la API y la
aplicación.

**Entrega:** el **2/12/2026** por el aula virtual: repositorio (compartido con el profesor) con un README de
arquitectura, decisiones y despliegue, las URL de la aplicación y de la API y los nombres del grupo. Exposición en el
taller 3 con demo en directo.

## Arquitectura de referencia

| Capa | Referencia de los talleres | Alternativas válidas |
|---|---|---|
| Captura | Python con `requests` + BeautifulSoup | Scrapy, Playwright |
| Almacenamiento | Amazon S3 | — |
| Extracción | Bedrock (Converse API) con salidas estructuradas, script por lotes | Lambda disparada por S3, Step Functions |
| Base de datos | Aurora PostgreSQL Serverless v2 con RDS Data API | RDS PostgreSQL, conexión por VPC |
| API | FastAPI en Lambda con Function URL | API Gateway, contenedor en ECS |
| Visualización | Streamlit en ECS Express Mode | Dash, React |
| Despliegue | Terraform + GitHub Actions (OIDC, estado en S3) | Libre |

## Estructura

Tres carpetas, como en los talleres de RL ([D-0.5](docs/DECISIONES.md)): el código, la infraestructura y la
documentación. La lógica vive en un único paquete y el resto son capas finas que la ejecutan o la sirven
([D-0.3](docs/DECISIONES.md)).

```
├── src/                        # todo el código
│   ├── kid_pipeline/           # lógica común: única fuente de verdad
│   │   ├── schema.py           # campos del Anexo A (Pydantic), esquema estricto para Bedrock, ISIN
│   │   ├── capture.py          # sesión educada (User-Agent, robots.txt, pausa) y una fuente por gestora
│   │   ├── storage.py          # S3: kid/<gestora>/<sha256>.pdf con metadatos de origen, y manifiesto JSONL
│   │   ├── extract.py          # Bedrock Converse: PDF como documento, herramienta en modo estricto
│   │   ├── db.py  schema.sql   # RDS Data API: upsert idempotente; tablas documentos y kid, vista kid_vigente
│   │   └── __init__.py         # Config por variables de entorno
│   ├── pipeline.py             # lote: init-db | capture | extract
│   ├── api.py                  # FastAPI + Mangum en Lambda con Function URL
│   ├── dashboard.py            # Streamlit en ECS Express Mode; solo lee de la API
│   └── test_pipeline.py        # tests sin AWS (clientes falsos)
├── infra/                      # todo el despliegue
│   ├── main.tf  datos.tf  servicios.tf   # proveedor y variables · S3 y Aurora · Lambda, ECR y ECS Express
│   ├── api.Dockerfile  dashboard.Dockerfile
│   └── bootstrap/main.tf       # una vez y en local: bucket del estado, OIDC y rol de GitHub
├── docs/
│   ├── DECISIONES.md           # registro de decisiones D-X.n
│   ├── teoria/                 # síntesis del material de clase
│   └── raw/                    # material de clase (local, no versionado)
└── .github/workflows/          # ci.yml (ruff, pytest, imágenes, terraform validate) · deploy.yml (despliegue y lote)
```

## Flujo de datos

```
web de la gestora --capture--> S3 kid/<gestora>/<sha256>.pdf + manifest/*.jsonl + tabla documentos
                  --extract--> Bedrock (salida estructurada) --> tabla kid (upsert por sha256)
                                 vista kid_vigente --> API (Lambda) --> cuadro de mando (ECS)
```

## Puesta en marcha

En Windows (PowerShell), desde la carpeta del proyecto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

Despliegue, en tres pasos:

1. **Bootstrap, una vez y en local** (`aws login`):
   `terraform -chdir=infra/bootstrap init` y `terraform -chdir=infra/bootstrap apply -var="alias=<iniciales>"`.
2. **Variables del repositorio** (Settings > Secrets and variables > Actions > Variables): `AWS_ROLE_ARN` (salida del
   bootstrap), `AWS_REGION`, `TF_STATE_BUCKET` (salida del bootstrap), `ALIAS` y `BEDROCK_MODEL_ID`. No son secretos:
   con OIDC no hay claves que guardar.
3. **Push a `main`**: `deploy.yml` sube las imágenes y aplica `infra/`. Después, Actions > AWS > Run workflow con la
   fase `init-db` la primera vez y `capture-extract` a partir de ahí (también corre solo cada lunes).

Mientras `AWS_ROLE_ARN` no exista, `deploy.yml` no hace nada y solo corre la CI. El material
de clase no se versiona: quien lo necesite lo copia en `docs/raw/`.

## Contrato común

- **Un único esquema.** Los campos salen de `schema.Kid`, que da el esquema de Bedrock, la validación y las columnas de
  `kid`. Añadir un campo es tocar `Kid`, `schema.sql` y `UPSERT_KID`.
- **Null antes que inventar.** Todo campo es opcional en la extracción. Los obligatorios del Anexo A se comprueban
  después (`faltan_obligatorios`) y se registran, no se rellenan.
- **El SHA-256 del PDF es la identidad** del documento en S3 y en la base de datos. Procesar dos veces no duplica.
- **La lógica no depende de AWS.** Las funciones reciben el cliente de boto3 como argumento, y los tests usan clientes
  falsos.
- **Sin secretos en Git.** Configuración por variables de entorno (`.env.example`), OIDC en Actions y contraseña de la
  base de datos en Secrets Manager.
- **Terraform es el único dueño de la infraestructura**, incluida la versión de cada imagen (`*_image_tag` = commit).
  Nada se cambia a mano en la consola.

## Documentación

- [`docs/DECISIONES.md`](docs/DECISIONES.md): decisiones del proyecto, cerradas y abiertas.
- [`docs/teoria/`](docs/teoria/): síntesis del material de clase, con la fuente citada en cada concepto. Se empieza
  por [`practica_partida.md`](docs/teoria/practica_partida.md) (enunciado, entrega y lo que dijo el profesor).

| Documento | Contenido |
|---|---|
| [`00_fundamentos_aws.md`](docs/teoria/00_fundamentos_aws.md) | Regiones, modelos de servicio, cuenta y costes, IAM, CLI, boto3 y VPC |
| [`01_ec2_y_desarrollo_remoto.md`](docs/teoria/01_ec2_y_desarrollo_remoto.md) | EC2, SSH y SCP, VS Code remoto, cron, variables de entorno y FastAPI en EC2 |
| [`02_s3_y_streamlit.md`](docs/teoria/02_s3_y_streamlit.md) | S3 y aplicaciones de datos con Streamlit |
| [`03_lambda_y_contenedores.md`](docs/teoria/03_lambda_y_contenedores.md) | Lambda, disparadores, Docker, ECR y ECS Express Mode |
| [`04_devops_y_terraform.md`](docs/teoria/04_devops_y_terraform.md) | Tests, GitHub Actions, despliegue con OIDC y Terraform |
| [`05_datos_y_documentos.md`](docs/teoria/05_datos_y_documentos.md) | DynamoDB, Athena, Textract y el proyecto final del curso |
| [`06_piezas_de_la_practica.md`](docs/teoria/06_piezas_de_la_practica.md) | Lo que el curso no cubre: KID y PRIIPs, scraping, Bedrock y Aurora con Data API |
| [`07_glosario.md`](docs/teoria/07_glosario.md) · [`COBERTURA.md`](docs/teoria/COBERTURA.md) | Términos, y qué tramo de cada fuente está en qué documento |

## Estado

- [x] Repositorio y material de clase (local, en `docs/raw/`, no versionado)
- [x] Mini base: carpetas por fase y decisiones iniciales
- [x] Estructura completa y compacta: paquete común, API, cuadro de mando, Terraform, workflows y tests
- [x] Documentación de teoría (`docs/teoria/`), hasta la clase del 14/11 y la web del curso
- [ ] Taller 1: captura, manifiesto, conexión GitHub-AWS, bucket y base de datos con Terraform
- [ ] Taller 2: extracción con Bedrock, carga en PostgreSQL, API y aplicación desplegadas
- [ ] Taller 3: exposición
