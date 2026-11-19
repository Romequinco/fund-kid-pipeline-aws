# Cobertura del material de clase

> **Fuentes:** T13 = `docs/raw/26 11 13.pdf` (transcripción del 13/11/2026; versión compacta en `docs/raw/transcripciones/T13.txt`), T14 = `docs/raw/26 11 14.pdf` (14/11/2026; `T14.txt`), WEB = `docs/raw/miax-cloud-main/` (lecciones en `content/`, ejemplos en `ejemplos/`, `CAMBIOS.md`), ENUNCIADO = `docs/raw/Practica_KID_AWS.docx`.
> **Convenciones:** cada fila dice en qué documento y sección (§) de `docs/teoria/` está cada tramo de transcripción, lección o ejemplo. Los tramos son de ~5-10 min y las horas, aproximadas. "descartado" = sin contenido útil (ruido, descanso, logística o datos personales). El glosario ([07_glosario.md](07_glosario.md)) remite a todos y no se repite aquí. Abreviaturas de documento: **P** = [practica_partida.md](practica_partida.md), **00**-**06** = los documentos numerados.
>
> Escrito el 19/11/2026.

## 1. Qué cubre cada fuente, en una tabla

| Fuente | Contenido | Documento principal |
|---|---|---|
| T13 00:00-02:30 | Web del curso, AWS, regiones, modelos de servicio, cuenta, costes, IAM, CLI, boto3, VPC | 00 |
| T13 02:30-04:50 | EC2, SSH, SCP, VS Code remoto, introducción a cron | 01 |
| T14 00:00-00:05 | Repaso del día anterior | 00 §7 |
| T14 00:05-03:08 | VS Code remoto, cron, variables de entorno, FastAPI en EC2, uv | 01 |
| T14 03:08-04:50 | S3 (consola, CLI, extensión, boto3, pandas, rol en EC2), práctica y talleres | 02, P §3 |
| WEB L00-L04 | Uso de la web, introducción, costes, IAM, VPC | 00 |
| WEB L05-L10 | EC2 a FastAPI en EC2 | 01 |
| WEB L11, L11b | S3 y Streamlit | 02 |
| WEB L12-L18, L29, L30 | Lambda, Docker, ECR, ECS Express, ALB y API Gateway | 03 (aún no dado en clase) |
| WEB L19-L23, L27 | DevOps, tests, Actions, CD con OIDC, Terraform | 04 (aún no dado en clase) |
| WEB L24-L26, L28 | DynamoDB, Athena, Textract, proyecto final del curso | 05 (aún no dado en clase) |
| ENUNCIADO | Práctica B7 completa | P; "Para la práctica" de cada documento; 06 |
| Documentación oficial externa | PRIIPs, scraping, Bedrock, Aurora con Data API, FastAPI en Lambda | 06 |

## 2. Transcripciones

### 2.1 T13 (13/11/2026)

| Tramo | Tema | Destino |
|---|---|---|
| ~00:00-00:03 | Inicio, enlace a la web, presentación | descartado: logística y datos personales (solo "web en GitHub Pages": 00 §1.1, P §3) |
| ~00:03-00:09 | Uso de la web: vistas, botones, alias y región, bloques | 00 §1.1 |
| ~00:09-00:14 | Limpieza y coste; qué instalar (CLI, Python, Docker/WSL, Terraform) | 00 §1.2, §3.3; 03 §5.2 |
| ~00:14-00:21 | Historia de AWS, ingresos y cuota de mercado | 00 §2.1; 02 §1.2; 05 §1 |
| ~00:21-00:28 | Regiones, zonas, caídas, precio y latencia | 00 §2.2 |
| ~00:28-00:35 | On-site, IaaS, PaaS y SaaS; orden del curso | 00 §2.3; 03 §1, §5.1 |
| ~00:35-00:44 | Documentación, modelos de precio, calculadora | 00 §3.4 |
| ~00:44-00:52 | Alta, verificación, planes | 00 §3.1, §3.3 |
| ~00:52-01:02 | Consola, región, raíz frente a IAM, MFA | 00 §3.1, §3.2 |
| ~01:02-01:07 | Qué se paga, IP públicas, región del plan gratuito | 00 §3.3, §2.2 |
| ~01:07-01:14 | Capa gratuita, Budgets, servicios globales, créditos | 00 §3.5, §3.6; 03 §2.1 |
| ~01:14-01:19 | IAM: conceptos, roles, mínimo privilegio, Deny | 00 §4.1-§4.3 |
| ~01:19-01:23 | `aws login` y métodos de acceso | 00 §5.1, §5.2 |
| ~01:23-01:34 | Crear grupo y usuario IAM, entrar con él, MFA | 00 §4.4, §3.2, §3.3 |
| ~01:34-01:40 | CLI con el usuario nuevo; CloudShell | 00 §5.2, §5.3 |
| ~01:40-01:54 | boto3 en notebook, AWS Toolkit, entornos virtuales; Docker en Windows | 00 §5.4, §5.5; 03 §5.1 |
| ~01:54-02:18 | Descanso | descartado: descanso |
| ~02:18-02:30 | VPC, CIDR, subredes, Internet Gateway, NAT, endpoint de S3 | 00 §6.1-§6.3; 02 §2.2, §4.3 |
| ~02:30-02:33 | Demo de la VPC por defecto | 00 §6.5; 01 §2.6 |
| ~02:33-02:41 | Qué es EC2, AMI, EBS, familias de instancia | 01 §1, §2.1-§2.3 |
| ~02:41-02:50 | Bloque, fichero y objeto; par de claves, puertos, grupos de seguridad | 01 §2.3, §2.4; 00 §6.4; 02 §3.2; 05 §1 |
| ~02:50-03:03 | Lanzar una instancia, Instance Connect, stop y terminate, IP | 01 §2.5, §2.7, §2.8, §3.1 |
| ~03:03-03:08 | NAT frente a Internet Gateway | 01 §2.4, §2.6 |
| ~03:08-03:22 | Ejercicio de créditos | 01 §2.9; descartado 03:10-03:14 y 03:20-03:22: ruido |
| ~03:22-03:36 | Crear imagen propia, lanzar desde AMI, snapshot | 01 §2.1, §2.7, §2.9 |
| ~03:36-03:48 | SSH y SCP; preferencia por S3 | 01 §3.2, §3.4; 02 §1.2 |
| ~03:48-03:58 | Ejercicio individual | 01 §2.5; resto descartado: ruido |
| ~03:58-04:15 | Permisos de la `.pem` en Windows, SCP, nano | 01 §3.3-§3.5 |
| ~04:15-04:33 | VS Code Remote-SSH: arquitectura, config, conexión, trucos | 01 §4, §2.4 |
| ~04:33-04:38 | Vercel frente a AWS; pipelines de GitHub a Lambda | 01 §7.7; 03 §2.1; 04 §1.4 |
| ~04:38-04:46 | cron, sintaxis, zonas horarias; Lambda por horario o fichero; scraping a S3 | 01 §5.1, §5.4; 03 §2.1; 02 §1.2; 06 §1 |
| ~04:46-04:50 | Qué preparar para el día siguiente; anuncio de Streamlit | descartado: logística (salvo el anuncio: 02 §7) |

### 2.2 T14 (14/11/2026)

| Tramo | Tema | Destino |
|---|---|---|
| ~00:00-00:05 | Repaso de T13, región de Estocolmo, foco del curso | 00 §7, §2.2; 02 §2.4; 03 §1 |
| ~00:05-00:07 | Contacto del profesor | descartado: datos personales |
| ~00:07-00:16 | Reconexión de VS Code, descarga de ficheros, repaso de cron | 01 §3.4, §4.2, §5.1, §5.4 |
| ~00:16-00:34 | Demo de cron, `>` frente a `>>`, ejercicio | 01 §5.2, §5.3, §3.1; descartado 00:31-00:34: ruido |
| ~00:34-01:02 | Config SSH, cron en remoto con venv y script | 01 §4.2, §3.3, §5.3, §4.3; 03 §5.1 |
| ~01:02-01:12 | Variables de entorno, `.env`, secretos (Lambda, ECS, GitHub) | 01 §6; 03 §3.4, §4.1; 04 §4.1; 05 §1 |
| ~01:12-01:42 | FastAPI en local y en EC2, puerto 8080, curl | 01 §7.1-§7.4; 03 §4.3 |
| ~01:42-01:48 | uv | 01 §7.5 |
| ~01:48-02:14 | Descanso | descartado (salvo un consejo de energía: 01 §4.1) |
| ~02:14-03:08 | Ejercicio GitHub → EC2, ayuda con claves y conexión, solución de un alumno | 01 §7.6, §3.3, §2.4, §2.7, §3.2; 04 §4.1 |
| ~03:08-03:15 | Qué es S3, durabilidad, consistencia, versionado, cifrado, acceso público | 02 §1.1, §2.4, §3.3, §3.4 |
| ~03:15-03:24 | Crear un bucket, formulario, coste por descarga, Intelligent-Tiering | 02 §3.1, §4.1, §4.2, §4.3, §5.1 |
| ~03:24-03:29 | Precios, Glacier, mínimos de permanencia, RGPD | 02 §4.1, §4.2, §2.4 (anécdota personal: descartada) |
| ~03:29-03:45 | URL `s3://`, carpetas virtuales, metadatos, requisitos legales, nombres de bucket | 02 §2.1-§2.4, §3.4, §3.5 |
| ~03:45-04:05 | Extensión de VS Code; CLI (mb, ls, cp, mv, sync, rm) | 02 §5.1, §5.2, §8 |
| ~04:05-04:18 | boto3, `aws login`, bots que buscan claves; pandas con s3fs | 02 §5.3, §5.4, §6.1, §6.2; 04 §4.1 |
| ~04:18-04:41 | EC2 sin credenciales, rol con acceso a S3, pandas desde EC2 | 02 §6.3, §8; incidencias técnicas descartadas |
| ~04:41-04:46 | Ejercicios, práctica, talleres, grupos del TFM, limpieza | P §2, §3; 02 §8; 04 §1.4 |
| ~04:47-04:50 | Conversación tras la clase | 02 §7, 03 §5.2 *(dudoso)*; resto descartado |

## 3. Web del curso

| Lección | Título | Destino |
|---|---|---|
| L00 | Cómo usar esta web | 00 §1 |
| L01 | Introducción a AWS | 00 §2, §3.1, §3.2 |
| L02 | Cuenta, costes y alertas | 00 §3.3-§3.6; 05 §1 (actividades de Aurora y Bedrock) |
| L03 | IAM, CLI y boto3 | 00 §4, §5; 01 §2.10 |
| L04 | Redes: VPC | 00 §6 |
| L05 | Amazon EC2 | 01 §1-§3.1; 00 §6.4 |
| L06 | Conexión SSH y SCP | 01 §3 |
| L07 | Desarrollo remoto con VS Code | 01 §4 |
| L08 | Cronjobs | 01 §5 |
| L09 | Variables de entorno | 01 §6 |
| L10 | Primer API en EC2 | 01 §7 |
| L11 | Amazon S3 | 02 §1-§6; 01 §2.10 |
| L11b | Aplicaciones de datos con Streamlit | 02 §7 |
| L12 | Primeros pasos con Lambda | 03 §1, §2 |
| L13 | Empaquetado y buenas prácticas | 03 §3 |
| L14 | Disparadores: cron, S3 y HTTP | 03 §4; 01 §5.4 |
| L15a, L15, L30 | Docker en tu ordenador, en EC2 y básico | 03 §5 |
| L16 | Amazon ECR | 03 §6 |
| L17 | ECS Express Mode | 03 §7 |
| L18 | Lambda con Docker | 03 §8 |
| L19 | Filosofía DevOps | 04 §1 |
| L20 | Tests y calidad de código | 04 §2 |
| L21 | GitHub Actions | 04 §3 |
| L22 | Despliegue continuo de Lambda (OIDC) | 04 §4, §5 |
| L23 | Despliegue continuo en ECS | 04 §6 |
| L24 | Amazon DynamoDB | 05 §1-§4 |
| L25 | Amazon Athena | 05 §5 |
| L26 | Amazon Textract | 05 §6 |
| L27 | Terraform | 04 §7, §8 |
| L28 | Proyecto final (casos de uso) | 05 §8, §9 |
| L29 | Load Balancer y API Gateway | 03 §9, §4.3 |
| CAMBIOS.md | Cambios por obsolescencia y errores corregidos | Transversal (00-05) |

## 4. Ejemplos de la web

| Ejemplo | Destino |
|---|---|
| `api-suma/` | 01 §7.1; 03 §5.3, §6, §7.3 |
| `lambda-docker/` | 03 §8 |
| `tests/` | 04 §2 |
| `s3/boto3_s3_example.ipynb` | 02 §5.3, §5.4 |
| `streamlit/` (01-05, `app.py`, `.service`) | 02 §7 |
| `github-actions/` (ci, deploy-lambda, deploy-ecs) | 04 §3, §5, §6, §8.3 |
| `terraform/` (1_bucket a 5_lambda) | 03 §7.2, §8; 04 §7, §8 |
| `dynamodb/`, `athena/`, `textract/` | 05 §3-§7 (de los JSON de Textract solo la estructura) |
| `market_data/market_data_proc.csv` | 05 §4 (recuentos de comprobación) |

## 5. Fuentes externas (solo en 06)

| Fuente | Tema | Destino |
|---|---|---|
| Reglamento (UE) 1286/2014 y Reglamentos Delegados 2017/653 y 2021/2268 (DOUE) | Qué es el KID, secciones, SRI, periodo de mantenimiento, costes, paso de KIID a KID | 06 §2 |
| Webs públicas y robots.txt de las tres gestoras (19/11/2026) | Cómo se llega al PDF; prohibición de PDF en Bestinver | 06 §3; [D-1.3](../DECISIONES.md) |
| RFC 9309, requests, robotparser, BeautifulSoup, Playwright | Scraping responsable | 06 §3 |
| Documentación de Amazon Bedrock (Converse, DocumentBlock, salidas estructuradas, herramientas, inferencia entre regiones, cuotas, precios) | Extracción | 06 §4; [D-2.1](../DECISIONES.md) |
| Documentación de Aurora Serverless v2 y RDS Data API; proveedor de Terraform | Base de datos | 06 §5; [D-3.1](../DECISIONES.md) |
| Documentación de PostgreSQL (`INSERT ... ON CONFLICT`) | Carga idempotente | 06 §6 |
| Documentación de Lambda Function URL, Mangum y Lambda Web Adapter | API | 06 §7; [D-4.2](../DECISIONES.md) |

## 6. Huecos conocidos

- **Lambda, contenedores, DevOps, Terraform, DynamoDB, Athena y Textract no se han dado en clase todavía.** Los documentos 03, 04 y 05 salen de la web del curso; cuando se den, hay que añadir los tramos nuevos y lo que diga el profesor.
- **Bedrock, Aurora con Data API y el scraping no están en la web del curso.** El documento 06 sale de documentación oficial y marca *(por verificar en el Taller 2)* lo que no se pudo confirmar.
- **Talleres 1 y 2:** cuando se publiquen sus transcripciones, irán a `docs/raw/` y a un documento nuevo con la solución de referencia.
