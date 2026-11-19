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

## Estado

- [x] Repositorio y material de clase (local, en `docs/raw/`, no versionado)
- [ ] Estructura del repositorio
- [ ] Documentación de teoría (`docs/teoria/`)
- [ ] Taller 1: captura, manifiesto, conexión GitHub-AWS, bucket y base de datos con Terraform
- [ ] Taller 2: extracción con Bedrock, carga en PostgreSQL, API y aplicación desplegadas
- [ ] Taller 3: exposición
