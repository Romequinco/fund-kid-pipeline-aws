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

Una carpeta por fase del pipeline. La lógica vive en un único paquete y el resto son capas finas que la ejecutan o la
sirven ([D-0.3](docs/DECISIONES.md)).

```
├── src/kid_pipeline/          # lógica común: única fuente de verdad
│   ├── schema.py              # campos del Anexo A (Pydantic) -> esquema JSON para Bedrock, validación del ISIN
│   ├── capture/
│   │   ├── base.py            # sesión educada (User-Agent, robots.txt, pausa), KidEnlace, Documento (SHA-256)
│   │   └── gestoras.py        # Bestinver, Azvalor y Cobas (se completan en el Taller 1)
│   ├── storage.py             # S3: kid/<gestora>/<sha256>.pdf con metadatos de origen, y manifiesto JSONL
│   ├── extract.py             # Bedrock Converse: PDF como documento, salida forzada con herramienta
│   ├── db.py                  # RDS Data API: parámetros tipados y upsert idempotente
│   └── config.py              # configuración por variables de entorno
├── scripts/pipeline.py        # lote: init-db | capture | extract
├── db/schema.sql              # documentos, kid y la vista kid_vigente
├── api/                       # FastAPI + Mangum en Lambda (imagen) con Function URL
├── dashboard/                 # Streamlit en ECS Express Mode; solo lee de la API
├── infra/
│   ├── bootstrap/             # una vez y en local: bucket del estado, OIDC y rol de GitHub
│   └── main/                  # S3, Aurora Serverless v2, Lambda + URL, ECR y ECS Express
├── .github/workflows/
│   ├── ci.yml                 # ruff, pytest, terraform fmt y validate
│   ├── deploy.yml             # push a main: imágenes a ECR y terraform apply (OIDC)
│   └── pipeline.yml           # lote a mano o cada lunes (OIDC)
├── tests/                     # sin AWS: clientes falsos de Bedrock, Data API y base de datos
└── docs/
    ├── DECISIONES.md          # registro de decisiones D-X.n
    ├── teoria/                # síntesis del material de clase
    └── raw/                   # material de clase (local, no versionado)
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
3. **Push a `main`**: `deploy.yml` sube las imágenes y aplica `infra/main`. Después, `pipeline.yml` (Actions > Pipeline >
   Run workflow) con `init-db` la primera vez y `capture-extract` a partir de ahí.

Mientras `AWS_ROLE_ARN` no exista, los workflows de despliegue y del lote no hacen nada y solo corre la CI. El material
de clase no se versiona: quien lo necesite lo copia en `docs/raw/`.

## Contrato común

- **Un único esquema.** Los campos salen de `schema.Kid`, que da el esquema de Bedrock, la validación y las columnas de
  `kid`. Añadir un campo es tocar `Kid`, `db/schema.sql` y `UPSERT_KID`.
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
- [`docs/teoria/`](docs/teoria/): síntesis del material de clase, con la fuente citada en cada concepto.

## Estado

- [x] Repositorio y material de clase (local, en `docs/raw/`, no versionado)
- [x] Mini base: carpetas por fase y decisiones iniciales
- [x] Estructura completa: paquete común, API, cuadro de mando, Terraform, workflows y tests
- [ ] Documentación de teoría (`docs/teoria/`)
- [ ] Taller 1: captura, manifiesto, conexión GitHub-AWS, bucket y base de datos con Terraform
- [ ] Taller 2: extracción con Bedrock, carga en PostgreSQL, API y aplicación desplegadas
- [ ] Taller 3: exposición
