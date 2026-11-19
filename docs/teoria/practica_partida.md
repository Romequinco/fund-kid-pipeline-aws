# Empezad por aquí: enunciado, entrega y lo que dijo el profesor

> **Fuentes:**
> - **ENUNCIADO** (`docs/raw/Practica_KID_AWS.docx`; texto en `docs/raw/transcripciones/enunciado.txt`): «Práctica B7 · Módulo Cloud · Pipeline de datos de fondos: del KID al dashboard en AWS». **Es la fuente que manda.**
> - **T14** (`docs/raw/26 11 14.pdf`; versión compacta en `docs/raw/transcripciones/T14.txt`): transcripción automática de la clase del 14/11/2026. Tramo usado: ~04:41-04:46 (ejercicios, práctica y talleres).
> - **T13** (`docs/raw/26 11 13.pdf`; `docs/raw/transcripciones/T13.txt`): clase del 13/11/2026, solo para la organización del curso (~00:02-00:04).
> - **WEB** (`docs/raw/miax-cloud-main/`): web del curso; `content/curso.json` (índice de lecciones) y `content/28-proyecto.md` (proyecto final del curso, distinto de esta práctica).
>
> **Convenciones:** `(T14 ~04:42)` = hora aproximada en la transcripción; todo lo que viene de ella es **paráfrasis** de un texto automático muy ruidoso. `(ENUNCIADO §4)` = apartado del enunciado. **Nota:** = contenido propio (interpretaciones, propuestas). Cuando ENUNCIADO y clase difieren, se dice y **prevalece el ENUNCIADO**.
>
> Escrito el 19/11/2026.

---

## 1. La práctica en una página

**Idea.** Construir un pipeline de datos completo en AWS: capturar de la web los KID (PDF) de varias gestoras de fondos, guardarlos en S3, extraer sus campos con un modelo de Amazon Bedrock con **salidas estructuradas**, cargarlos en PostgreSQL sin duplicados y servirlos con una API y una aplicación web, con toda la infraestructura en Terraform desplegada desde GitHub Actions (ENUNCIADO §1, §4).

| Fase | Mínimo exigido (ENUNCIADO §4) | Referencia de los talleres (ENUNCIADO §6) | Código del repo |
|---|---|---|---|
| Captura | ≥ **2 fuentes** y ≥ **15 documentos**, con origen y fecha de descarga de cada uno | Python con `requests` + BeautifulSoup | `src/kid_pipeline/capture/` |
| Almacenamiento | PDF en S3 | Amazon S3 | `src/kid_pipeline/storage.py`, `infra/main/storage.tf` |
| Extracción | Campos del Anexo A con Bedrock y salidas estructuradas | Converse API, script por lotes | `src/kid_pipeline/extract.py`, `schema.py` |
| Base de datos | PostgreSQL en AWS, sin duplicados al reprocesar | Aurora Serverless v2 con RDS Data API | `src/kid_pipeline/db.py`, `db/schema.sql` |
| API | API HTTP | FastAPI en Lambda con Function URL | `api/` |
| Visualización | Aplicación web para explorar los datos | Streamlit en ECS Express Mode | `dashboard/` |
| IaC | Terraform desplegado desde GitHub Actions | OIDC, estado en S3 | `infra/`, `.github/workflows/` |

- La arquitectura de referencia es solo eso: "todas las piezas son sustituibles", siempre que se justifique (ENUNCIADO §4, §6). Cada cambio va a [`docs/DECISIONES.md`](../DECISIONES.md).
- El enunciado no da un reparto de puntos por fase. Sí dice que las ideas para ir más allá "puntúan en el apartado de ampliaciones" (ENUNCIADO §4); ver §7.

---

## 2. Entrega, exposición y grupo

**Idea.** Se entrega el repositorio funcionando en AWS y se defiende en directo en el taller 3.

| Qué | Detalle | Fuente |
|---|---|---|
| Fecha | **2/12/2026**, por el aula virtual | ENUNCIADO, datos básicos |
| Repositorio | En GitHub, **compartido con el profesor**, con un README que explique la arquitectura, las decisiones y cómo desplegar | ENUNCIADO §7 |
| URLs | De la aplicación y de la API | ENUNCIADO §7 |
| Grupo | Nombres de los integrantes. Los grupos son los del TFM | ENUNCIADO §7; T14 ~04:42:40, ~04:45:21 |
| Exposición | En el taller 3, con demo en directo y reflexión sobre decisiones y dificultades | ENUNCIADO §7 |

- **Duración de la exposición: el enunciado se contradice.** En "Datos básicos" y en §7 pone "5 minutos y 5 minutos de preguntas"; el último párrafo de §7 habla de "10 minutos con una demostración en directo". En clase el profesor dijo "entre 5 y 10 minutos por grupo" (T14 ~04:42:40). **Nota:** preparar una versión de 5 minutos con la demo dentro, que cabe en los dos formatos.
- **¿Grupal o individual?** El enunciado dice "práctica por grupos" pero también "cada estudiante expone la suya" y "cada estudiante deberá entregar". En clase quedó claro que se trabaja y expone por grupo (T14 ~04:42:40-04:42:53). Ver §8.

---

## 3. Lo que dijo el profesor sobre la práctica

**Idea.** La práctica se construye en los dos primeros talleres siguiendo al profesor, y el tercero es para presentar.

- **Tres talleres** (T14 ~04:42:29-04:42:53; ENUNCIADO §6):
  - **Taller 1, captura e infraestructura base:** inspección de las webs, scraper, manifiesto, repositorio plantilla, conexión GitHub-AWS y primer despliegue con Terraform (bucket y base de datos).
  - **Taller 2, IA, datos y aplicación:** extracción con Bedrock, carga en PostgreSQL, API y aplicación, desplegadas desde GitHub Actions.
  - **Taller 3, exposición:** cada grupo presenta su solución funcionando.
- **Cómo se trabaja.** Él construye una solución de referencia y los alumnos deben fijarse para llegar a una "similar". Calcula "un par de horas más por la tarde" (T14 ~04:43:01). En los talleres dará tiempo para ir montándolo (T14 ~04:45:51).
- **El caso de uso** sale de su trabajo diario: datos **no estructurados** obtenidos con scraping, procesados con IA para extraer la información, guardados y "disponibilizados" en una web o como mejor encaje (T14 ~04:43:19-04:43:50).
- **Esfuerzo fuera de clase.** Todo el código y el despliegue se verá en los dos talleres, pero "seguro" que el grupo tendrá que juntarse una tarde, una o dos horas, para terminar y decidir qué presenta (T14 ~04:46:08-04:46:22).
- **Limpieza.** Hay que borrar instancias, pares de claves, *snapshots* y volúmenes, porque se siguen cobrando. El panel de cada servicio resume lo que hay creado (T14 ~04:43:53-04:45:02).
- **Dudas:** por contacto directo con el profesor, que ofrece una llamada si hace falta (T14 ~04:42:03-04:42:20, ~04:45:34).
- **El curso** se centra en AWS; las últimas clases tocarán Google Cloud y Azure (T13 ~00:02:49). La web de clase está publicada en GitHub Pages (T13 ~00:00:52).

---

## 4. El KID y los campos del Anexo A

**Idea.** El KID tiene una estructura común de unas tres páginas, así que los campos mínimos aparecen casi siempre en el mismo sitio. El riesgo no es encontrarlos, sino que el modelo **invente** los que faltan.

| Campo | Tipo | Dónde suele estar en el KID (**Nota:**) | Trampas (**Nota:**) |
|---|---|---|---|
| `isin` | texto, 12 | Cabecera, junto al nombre del producto | Varias clases por fondo (Cobas): un KID por clase. Se valida el dígito de control (`schema.isin_valido`) |
| `nombre_producto` | texto | Cabecera | Tal y como aparece en el KID, sin normalizar |
| `nombre_clase` | texto, opcional | Cabecera o nombre del producto | A veces va dentro del nombre del producto |
| `gestora` | texto | "Productor" en la cabecera | Gestora frente a comercializador o depositario |
| `fecha_documento` | fecha, opcional | Pie de la cabecera ("fecha de elaboración" o "válido a") | Formatos españoles (`31/01/2026`, "enero de 2026") |
| `sri` | entero 1-7 | "¿Qué riesgos corro?", la escala del 1 al 7 | Es un gráfico: el valor marcado puede no estar en el texto |
| `periodo_mantenimiento_anios` | número, opcional | Mismo apartado o "¿Cuánto tiempo debo mantener la inversión?" | En años o meses |
| `gastos_corrientes_pct` | número, opcional | "Composición de los costes" | No confundir con el coste total en euros del escenario de 10.000 € |
| `costes_entrada_pct`, `costes_salida_pct` | número, opcional | "Composición de los costes" | "No cobramos comisión de entrada" = 0, no null |

- **Regla del Anexo A:** si un campo no aparece en el documento, queda **vacío (null)**; el modelo no debe inventarlo. Se pueden añadir todos los campos que se quiera: escenarios de rentabilidad, distribución de activos, objetivo de inversión, divisa (ENUNCIADO, Anexo A).
- **Contexto normativo** (ENUNCIADO §2): desde 2023 el KID sustituye también al antiguo DFI/KIID de los UCITS, aunque algunas gestoras españolas siguen llamándolo «DFI» o «datos fundamentales». El detalle normativo (PRIIPs) está en [06_piezas_de_la_practica.md](06_piezas_de_la_practica.md).

---

## 5. Las tres fuentes de los talleres

**Idea.** Están ordenadas por dificultad, y la del enunciado no es una descripción eterna: "las webs pueden cambiar en cualquier momento; detectarlo y adaptarse forma parte de la práctica" (ENUNCIADO §3).

| Gestora | Entrada | Cómo se llega al PDF | Dificultad |
|---|---|---|---|
| Bestinver | `bestinver.es/fondos-de-inversion/` | Ficha por fondo con enlace «Datos fundamentales». Una clase por ficha | Baja |
| Azvalor | `azvalor.com/fondos/` | Ficha con «Folleto simplificado (DFP)». El nombre del PDF lleva la fecha, así que la URL se lee del HTML | Media |
| Cobas AM | `cobasam.com/productos/` | Ficha con un bloque por clase (A, B, C, D), cada una con su ISIN y su «PRIIP pdf» | Media-alta |

- Se pueden usar otras fuentes públicas: otras gestoras, plataformas de distribución o el registro de la CNMV (ENUNCIADO §3).
- **Nota:** con Bestinver y Cobas se superan holgadamente los mínimos (2 fuentes y 15 documentos), porque Cobas da varios KID por fondo. Azvalor sería la tercera.

---

## 6. Reglas

**Idea.** Pocas reglas, y todas comprobables en la exposición (ENUNCIADO §5).

1. **Salidas estructuradas de verdad:** esquema JSON o herramientas en modo estricto de Bedrock. No vale pedir al modelo que "devuelva JSON" y parsear el texto. El modelo es libre. Ver [D-2.1](../DECISIONES.md).
2. **Sin credenciales en el repositorio.** En el repo: OIDC, Secrets Manager y `.gitignore` ([D-0.4](../DECISIONES.md)).
3. **Los datos y documentos no se exponen públicamente** salvo a través de la API y la aplicación. Por eso el bucket es privado y el cuadro de mando solo lee de la API ([D-4.1](../DECISIONES.md)).
4. **Asistentes de programación permitidos**, pero hay que saber explicar cualquier parte de la solución.

Lo demás (lenguaje, librerías, servicios, diseño) es libre.

---

## 7. Ampliaciones que propone el enunciado

**Idea.** Puntúan aparte. La valoración de esfuerzo es **Nota:** propia, en función de lo que ya trae la estructura del repo.

| Ampliación (ENUNCIADO §4) | Esfuerzo | Qué hay ya en el repo |
|---|---|---|
| Webs con JavaScript (Playwright) | Medio | Una `Fuente` más en `capture/gestoras.py` |
| Arquitectura por eventos (S3 → Lambda) | Medio | `extract.extraer` ya es una función pura reutilizable desde un handler |
| Comparar varios modelos | Bajo | `modelo` se guarda en cada fila de `kid`; basta con ejecutar `extract --todos` con otro `BEDROCK_MODEL_ID` |
| Precisión frente a KID revisados a mano | Medio | Falta el conjunto revisado y un script de comparación campo a campo |
| Tests y validaciones en el pipeline de GitHub | Bajo | `ci.yml` ya corre ruff, pytest y `terraform validate` |
| Alertas cuando cambia un KID | Bajo-medio | `pipeline.yml` corre cada lunes, y un PDF nuevo es un SHA-256 nuevo |
| Buscador en lenguaje natural | Alto | Requiere otra llamada a Bedrock en la API |

---

## 8. Dudas abiertas para el profesor

**Nota:** son preguntas propias, para llevarlas al Taller 1.

1. ¿Exposición de 5 + 5 o de 10 minutos (§2)?
2. ¿Entrega por grupo o por estudiante? El enunciado mezcla ambas formas.
3. ¿Qué región usar? La web del curso trabaja en París y en clase se habilitó Estocolmo para quien no podía seleccionarla. Hay que cruzarlo con los modelos de Bedrock disponibles ([D-0.2](../DECISIONES.md)).
4. ¿La API puede ser pública sin autenticación? El enunciado solo exige que los datos no se expongan "salvo a través de la API y la aplicación".
5. ¿Hay que mantener el despliegue encendido hasta la corrección, o basta con la demo? ECS Express y Aurora tienen coste ([D-5.2](../DECISIONES.md)).

---

## 9. Orden de lectura

| Documento | Para qué |
|---|---|
| Este | Qué se pide y cómo se entrega |
| [00_fundamentos_aws.md](00_fundamentos_aws.md) | Cuenta, costes, IAM, CLI, boto3 y VPC (T13) |
| [01_ec2_y_desarrollo_remoto.md](01_ec2_y_desarrollo_remoto.md) | EC2, SSH, VS Code remoto, cron, variables de entorno y FastAPI (T13-T14) |
| [02_s3_y_streamlit.md](02_s3_y_streamlit.md) | S3 y Streamlit (T14) |
| [03_lambda_y_contenedores.md](03_lambda_y_contenedores.md) | Lambda, Docker, ECR y ECS Express (web del curso) |
| [04_devops_y_terraform.md](04_devops_y_terraform.md) | Tests, GitHub Actions, OIDC y Terraform (web del curso) |
| [05_datos_y_documentos.md](05_datos_y_documentos.md) | DynamoDB, Athena, Textract y el proyecto final del curso |
| [06_piezas_de_la_practica.md](06_piezas_de_la_practica.md) | Lo que el curso no cubre: KID/PRIIPs, scraping, Bedrock, Aurora con Data API |
| [07_glosario.md](07_glosario.md) | Términos y siglas |
| [COBERTURA.md](COBERTURA.md) | Qué tramo de cada fuente está en qué documento |
