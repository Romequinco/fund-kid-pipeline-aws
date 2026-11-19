# Piezas de la práctica que el curso no cubre: KID, scraping, Bedrock, Aurora y FastAPI en Lambda

> **Fuentes:**
> - **ENUNCIADO** = `docs/raw/transcripciones/enunciado.txt` (práctica B7): §2 contexto, §3 fuentes, §4 tareas, §5 reglas, §6 arquitectura de referencia y Anexo A. **DEC** = `docs/DECISIONES.md`.
> - **R1286** = Reglamento (UE) n.º 1286/2014 (PRIIPs), texto en español del DOUE L 352 de 9.12.2014, art. 4, 5, 6, 8, 32 y 34. **RD653** = Reglamento Delegado (UE) 2017/653, DOUE L 100 de 12.4.2017, art. 3, 5 y 6 y anexos II y III. **RD2268** = Reglamento Delegado (UE) 2021/2268 en su versión corregida (corrección de errores en DOUE L 115 de 13.4.2022, que sustituye el texto entero), anexos IV y VI-VII. **RD975** = Reglamento Delegado (UE) 2022/975 (DOUE L 167 de 2022). **DIR2261** = Directiva (UE) 2021/2261 (DOUE L 455 de 20.12.2021). EUR-Lex respondió a la descarga automática con un reto antibots, así que se leyeron las copias oficiales del DOUE que publica el BOE (URL en Referencias).
> - **T13** = `docs/raw/transcripciones/T13.txt` (clase del 13/11/2026), ~04:40:59: el scraping aparece solo como ejemplo de tarea programada con cron (paráfrasis).
> - **L14**, **L18**, **L24**, **L26** = lecciones del curso en `docs/raw/miax-cloud-main/content/` (disparadores HTTP de Lambda, Lambda con Docker, actividades de Aurora y Bedrock). **EJ** = `ejemplos/textract/salida/` (un KIID de 2022 extraído con Textract; ver [05_datos_y_documentos.md](05_datos_y_documentos.md), §7).
> - **WEB** = fichas públicas de las tres gestoras y sus `robots.txt`, consultadas el 19/11/2026 solo para ver cómo se llega al PDF (no se ha descargado ningún KID).
> - Documentación técnica: AWS (Bedrock, RDS/Aurora, Lambda), Anthropic (soporte de PDF en Claude), PostgreSQL, IETF (RFC 9309), requests, Mangum y AWS Lambda Web Adapter. Cada dato lleva su etiqueta entre corchetes, p. ej. **[AWS Bedrock Converse]**, y la URL está en **Referencias** al final.
>
> **Convenciones:** "(R1286 art. 8.3.d)" = artículo y letra; "(RD653 anexo II, p. 2)" = punto del anexo. **Nota:** = contenido propio (cálculos, conexiones, recomendaciones), no de las fuentes. *(por verificar en el Taller 2)* = detalle de API que no se ha podido confirmar en la documentación oficial o que depende de la cuenta; no se rellena con suposiciones. Los precios y límites son los publicados a 19/11/2026 y cambian a menudo. Las salidas estructuradas de Bedrock son de febrero de 2026: cualquier material anterior que diga que la Converse API "no tiene modo JSON" está desfasado.
>
> Escrito el 19/11/2026.

---

## 1. Qué exige la práctica y qué cubre el curso

**Idea.** El curso enseña la infraestructura (S3, Lambda, contenedores, Terraform, Actions); la práctica añade un dominio (el KID de los fondos) y cuatro piezas técnicas que no tienen lección propia.

| Fase (ENUNCIADO §4) | Referencia (ENUNCIADO §6) | ¿Lo cubre el curso? | Aquí |
|---|---|---|---|
| Captura | requests + BeautifulSoup | Solo como ejemplo de tarea programada con cron (T13 ~04:40:59) | §3 |
| Almacenamiento | S3 | Sí (S3, metadatos) | — |
| Extracción con IA | Bedrock (Converse) con salidas estructuradas, script por lotes | Solo una actividad de créditos en el *playground* (L26) | §4 |
| Base de datos | Aurora PostgreSQL Serverless v2 con RDS Data API | Solo una actividad de créditos de Aurora (L24) | §5, §6 |
| API | FastAPI en Lambda con Function URL | FastAPI en EC2/ECS; Function URL con un controlador a mano (L14) | §7 |
| Visualización, IaC y despliegue | Streamlit en ECS Express; Terraform + Actions (OIDC) | Sí | — |
| Dominio | El KID (Anexo A) | No | §2 |

---

## 2. El KID: qué documento estamos leyendo

**Idea.** El KID (*Key Information Document*, en español «documento de datos fundamentales») es un documento precontractual **obligatorio, breve y normalizado** que el productor de un PRIIP debe publicar en su web. Al estar normalizado por reglamento, todos los KID tienen las mismas secciones en el mismo orden, y eso es lo que hace viable extraer los mismos campos de gestoras distintas.

### 2.1 Marco normativo

| Norma | Qué aporta | Fecha |
|---|---|---|
| R1286 (PRIIPs) | Obligación de elaborar y **publicar en su sitio web** el KID antes de ofrecer el producto a minoristas (art. 5.1); forma y contenido (art. 6 y 8) | Aplicable desde 31/12/2016 en el texto original (art. 34) *(fecha aplazada después por otra norma, no consultada)* |
| RD653 | Normas técnicas: método del indicador de riesgo, presentación de escenarios y costes, plantillas | DOUE de 12.4.2017 |
| RD2268 | Revisa escenarios de rentabilidad, presentación de costes, rentabilidad histórica | Aplicable desde **1/1/2023** (RD975 art. 2 cambió el 1/7/2022 original) |
| DIR2261 | Un KID conforme al R1286 **cumple** los requisitos del antiguo KIID de la Directiva UCITS (nuevo art. 82 bis de la Directiva 2009/65/CE) | Aplicable desde **1/1/2023** (DIR2261 art. 2) |

- Las gestoras de UCITS estaban exentas del R1286 hasta el 31/12/2019 en el texto original (R1286 art. 32.1); la exención se prorrogó hasta el **31/12/2022** por el Reglamento (UE) 2021/2259 (DIR2261 considerando 6). Para no entregar dos documentos del mismo producto, desde el 1/1/2023 el minorista recibe solo el KID (DIR2261 considerando 7).
- Definiciones: un PRIIP es, entre otros, una inversión cuyo importe reembolsable fluctúa por la exposición a valores de referencia o a activos que el inversor no compra directamente; **productor** es quien lo crea o modifica su perfil de riesgo o sus costes (R1286 art. 4). En un fondo, el productor es la **gestora**: el campo `gestora` del Anexo A.

### 2.2 Estructura: tres caras de A4, secciones fijas

El KID es "un documento breve, redactado de forma concisa y en tres caras de tamaño A4 como máximo en versión impresa" (R1286 art. 6.4). Lleva el título «Documento de datos fundamentales» en la parte superior de la primera página y una declaración explicativa fija debajo (R1286 art. 8.1-8.2). Después, en este orden (R1286 art. 8.3):

| Bloque (R1286 art. 8.3) | Contenido | Campos del Anexo A que suelen estar ahí |
|---|---|---|
| a) Cabecera | Nombre del producto, identidad y contacto del productor, autoridad competente, **fecha del documento** | `nombre_producto`, `gestora`, `fecha_documento`, y en fondos también la clase y su código (`isin`, `nombre_clase`): RD2268 añade la identificación del OICVM "incluida la clase de acciones" y su código (art. 1.1.g) |
| c) «¿Qué es este producto?» | Tipo, objetivos y política, inversor al que se dirige, plazo | (la *allocation*, cuando aparece; ENUNCIADO §2) |
| d) «¿Qué riesgos corro y qué podría obtener a cambio?» | **Indicador resumido de riesgo**, pérdida máxima, **escenarios de rentabilidad** | `sri`, y a menudo `periodo_mantenimiento_anios` |
| e) «¿Qué pasa si [productor] no puede pagar?» | Si existe un régimen de garantía | — |
| f) «¿Cuáles son los costes?» | Costes únicos y recurrentes, en indicadores resumidos, en dinero y en % | `costes_entrada_pct`, `costes_salida_pct`, `gastos_corrientes_pct` |
| g) «¿Cuánto tiempo debo mantener la inversión, y puedo retirar dinero de manera anticipada?» | **Periodo de mantenimiento recomendado**, condiciones de desinversión | `periodo_mantenimiento_anios` |
| h) «¿Cómo puedo reclamar?» / i) «Otros datos de interés» | Reclamaciones; documentos adicionales | — |

(La letra b es una advertencia de comprensión para productos complejos.) RD653 repite el límite: "no podrá tener más de tres páginas de tamaño A4 una vez impreso".

### 2.3 El indicador resumido de riesgo (SRI, 1-7)

- Escala numérica **de 1 a 7** (RD653 art. 3.2.a). La versión española lo llama **IRR** (indicador resumido de riesgo); el Anexo A usa la sigla inglesa SRI.
- Combina una **clase de riesgo de mercado** y una **clase de riesgo de crédito** con una tabla de doble entrada (RD653 anexo II, p. 52). La de mercado sale de la volatilidad equivalente al VaR al 97,5 % sobre el periodo de mantenimiento recomendado (anexo II, p. 1-2):

| Clase de mercado | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| Volatilidad equivalente (VEV) | < 0,5 % | 0,5-5 % | 5-12 % | 12-20 % | 20-30 % | 30-80 % | > 80 % |

- Con riesgo de crédito bajo (clases 1-2 de crédito), el SRI coincide con la clase de mercado; con crédito alto, sube (p. ej., crédito 4 lleva cualquier clase de mercado 1-5 a SRI 5) (RD653 anexo II, p. 52).
- **Presentación**: se dibuja la escala completa y "el número correspondiente se pondrá de relieve"; **inmediatamente debajo** se indica la duración del periodo de mantenimiento recomendado (RD653 anexo III, p. 1 y 3).

**Nota:** esto explica dos cosas de la extracción. (1) Con texto plano se leen las siete cifras pero no cuál está resaltada (EJ: el KIID de ejemplo, [05](05_datos_y_documentos.md) §7.2); un modelo que vea la página puede distinguirlo, pero conviene comprobarlo con KID revisados a mano. (2) El periodo de mantenimiento suele aparecer dos veces (bajo el SRI y en la sección g): si no coinciden, es señal de error de extracción.

### 2.4 Periodo de mantenimiento recomendado y escenarios

- El KID indica el **periodo de mantenimiento recomendado** y, si existe, el mínimo exigido (R1286 art. 8.3.g.ii), con una breve explicación de por qué se eligió (RD653 art. 6.a). Se expresa en años ("5 años"); el Anexo A lo quiere como número.
- **Escenarios de rentabilidad** desde 2023: **favorable, moderado, desfavorable y de tensión** (RD2268 anexo IV, p. 1). En los fondos con historial suficiente, desfavorable, moderado y favorable son la **peor, la mediana y la mejor** evolución en subintervalos históricos de la duración del periodo recomendado, sobre los últimos 10 años (o el periodo recomendado más 5, si este supera 5 años) (RD2268 anexo IV, p. 6-10); para ciertos productos de las categorías 1, 3 y 4 se usan los percentiles 10, 50 y 90 de una distribución estimada (p. 21-23). El de tensión "no será mejor" que el desfavorable (p. 20).
- Las tablas usan un **ejemplo de inversión de 10.000 EUR** y muestran resultados "en caso de salida después de 1 año" y al final del periodo recomendado (RD2268, modelos de la parte 3).

**Nota:** los escenarios no están en el Anexo A, pero son la ampliación natural ("escenarios de rentabilidad", ENUNCIADO, Anexo A) y un buen test de extracción: cuatro filas por dos columnas, con importes en euros y rentabilidades en %.

### 2.5 Costes: el campo que más se equivoca

RD2268 fija dos cuadros en «¿Cuáles son los costes?» (anexos VI-VII):

- **«Costes a lo largo del tiempo»**: costes totales en euros e **«Incidencia anual de los costes»** en %, para el ejemplo de 10.000 EUR.
- **«Composición de los costes»**:

| Fila del cuadro (RD2268) | Grupo | Campo del Anexo A |
|---|---|---|
| Costes de entrada | Costes únicos de entrada o salida | `costes_entrada_pct` |
| Costes de salida | Costes únicos de entrada o salida | `costes_salida_pct` |
| **Comisiones de gestión y otros costes administrativos o de funcionamiento** | Costes corrientes (detraídos cada año) | `gastos_corrientes_pct` (la descripción del Anexo A es literalmente este rótulo) |
| Costes de operación | Costes corrientes | — (ampliación) |
| Comisiones de rendimiento [y participaciones en cuenta] | Costes accesorios | — (ampliación) |

- **Trampa:** en los productos que no son de seguros (los fondos), la columna de la derecha del cuadro va **en EUR** («[Hasta] [] EUR (PRIP) o [] % (productos de inversión basados en seguros)»), y el porcentaje aparece dentro del texto descriptivo de la columna central («[] % del importe que pagará usted al realizar esta inversión», «[] % del valor de su inversión al año») (RD2268, cuadro 2). Un extractor que lea "la cifra de la fila" devolverá euros sobre 10.000, no el porcentaje.
- Fórmulas habituales de las plantillas para costes nulos: «No cobramos comisión de entrada», «No cobramos una comisión de salida por este producto» (RD2268, cuadro 2). La regla del Anexo A es `null` **solo si el campo no aparece**: "no cobramos comisión" es un 0 explícito.

**Nota:** para un fondo con gastos corrientes del 1,5 %, la fila mostrará unos 150 EUR. Si el modelo devuelve `150` en `gastos_corrientes_pct`, una validación de rango (p. ej. rechazar > 10 %) lo detecta.

### 2.6 Del KIID (DFI) al KID desde 2023

| | KIID / DFI de UCITS (hasta 2022) | KID PRIIPs (desde 1/1/2023) |
|---|---|---|
| Título visible | «Key Investor Information» / «Datos fundamentales para el inversor» (EJ) | «Documento de datos fundamentales» (R1286 art. 8.1) |
| Riesgo | «Risk and reward profile», escala 1-7 basada en datos históricos (EJ) | SRI 1-7: mercado + crédito (RD653 anexo II) |
| Costes | «Entry charge», «Exit charge», «Ongoing charges» en % (EJ: 0.18 %) | Cuadros de RD2268: importes en EUR y % (§2.5) |
| Rentabilidad | Gráfico de rentabilidad histórica fondo/índice (EJ) | Escenarios (§2.4); la histórica, por referencia (RD2268) |
| Extensión | 2 páginas en el ejemplo (EJ) | Máximo 3 caras de A4 (R1286 art. 6.4) |

Nombres en las webs (WEB, 19/11/2026): Bestinver enlaza «Datos fundamentales»; Azvalor, «Folleto simplificado (DFP)»; Cobas, «PRIIP pdf» con ficheros llamados `dfi-*.pdf`. Es lo que avisa el ENUNCIADO (§2): algunas gestoras siguen llamando «DFI» al KID.

**Nota:** un PDF de una fuente alternativa (otra plataforma, un archivo antiguo) puede ser todavía un KIID. Conviene guardar un campo `tipo_documento` y no forzar campos que no existen en ese formato (en el KIID no hay periodo de mantenimiento en una sección propia).

---

## 3. Web scraping responsable con requests y BeautifulSoup

**Idea.** Capturar es leer el HTML de la ficha de cada fondo, encontrar el enlace al PDF y descargarlo, **identificándose, despacio y respetando lo que pide el sitio**. Es la decisión DEC D-1.1.

### 3.1 robots.txt

- Va en `/robots.txt` de cada host; se agrupan reglas por `User-agent` (si ninguna coincide se aplica `*`); entre `Allow` y `Disallow` gana la regla **más específica** (la coincidencia más larga) [RFC 9309].
- **No es un mecanismo de autorización**: es una petición del administrador, no una barrera [RFC 9309].
- Si `robots.txt` da un error 4xx se puede rastrear todo; si da 5xx hay que suponer **prohibición total**; la copia se puede cachear hasta 24 horas [RFC 9309]. `Crawl-delay` no está en el estándar [RFC 9309].
- En Python: `urllib.robotparser.RobotFileParser` con `can_fetch(user_agent, url)` y `crawl_delay(user_agent)` [Python robotparser].

Lo que dicen hoy los de las tres gestoras (WEB, 19/11/2026):

| Gestora | robots.txt | Implicación |
|---|---|---|
| Bestinver | Para `*` (y Googlebot): `Disallow: /wp-admin/`, `Disallow: /xmlrpc.php`, **`Disallow: /*.pdf$`**; bloquea por completo a varios robots (`HTTrack`, `libwww`...) | Pide que los robots no descarguen PDF |
| Cobas | `User-agent: *` con `Disallow:` vacío | Todo permitido en la web; los PDF están en otro host (un bucket S3 de la gestora), al que se aplica su propio `robots.txt` (si no existe y responde 4xx, el RFC permite el acceso) |
| Azvalor | La petición automática de `robots.txt` recibió **HTTP 418** | El servidor rechaza ciertos clientes no navegador; no se ha insistido |

**Nota (Bestinver).** El enlace al PDF lleva un parámetro (`...datos_fundamentales.pdf?h=...`), y `$` ancla el final de la URL: con coincidencia literal la regla no aplica a la URL con parámetro. Comprobado con Python 3.13: `can_fetch` devuelve `False` para `/x/a.pdf` y `True` para `/x/a.pdf?h=0.41`. Pero la intención del sitio es clara. No es una cuestión que resuelva este documento: hay que **decidirlo y justificarlo en DEC D-1.1** (p. ej., que el R1286 art. 5.1 obliga a publicar el KID en la web, volumen mínimo, una descarga por documento y con pausa; o buscar una fuente alternativa). Lo que no es aceptable es saltarse un bloqueo (cambiar el `User-Agent` para hacerse pasar por un navegador, rotar IP) si un servidor rechaza al scraper.

### 3.2 Peticiones educadas

```python
SESION = requests.Session()
SESION.headers["User-Agent"] = "kid-pipeline-miax/0.1 (+URL del repositorio)"

def get(url: str) -> requests.Response:
    r = SESION.get(url, timeout=(5, 30))   # sin timeout, requests puede esperar para siempre
    r.raise_for_status()                   # 4xx/5xx -> excepción
    time.sleep(PAUSA_S)                    # p. ej. 2-5 s entre peticiones al mismo host
    return r
```

- Cabeceras propias con `headers=`; un `User-Agent` que identifique el proyecto [requests quickstart].
- "Nearly all production code should use this parameter in nearly all requests": el `timeout`; sin él no hay límite [requests quickstart].
- `raise_for_status()` convierte un 4xx/5xx en excepción; `r.content` da los bytes del PDF [requests quickstart].

### 3.3 Leer la URL del PDF del HTML

Cómo están hoy las fichas (WEB, 19/11/2026; ENUNCIADO §3):

| Gestora | Listado → ficha | Enlace al KID | Patrón de la URL del PDF |
|---|---|---|---|
| Bestinver | `/fondos-de-inversion/` → `/fondos-de-inversion/<fondo>/`, HTML estático | Texto «Datos fundamentales» | `/wp-content/uploads/<fondo>_fi_datos_fundamentales.pdf?h=<valor que cambia en cada carga>` |
| Azvalor | `/fondos/` → `/fondos-de-inversion/<fondo>/` | Texto «Folleto simplificado (DFP)» | `/wp-content/uploads/AAAA/MM/DFP-<Fondo>-DD.MM.AAAA.pdf`: **la fecha va en el nombre** |
| Cobas | `/productos/` → `/productos/inversion-libre/<fondo>/` | Un bloque por clase (A-D), cada uno con su ISIN y un enlace «PRIIP pdf» | Bucket S3 público de la gestora: `.../<Fondo>/Clase+A/dfi-<fondo>.pdf` |

```python
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def url_kid(html: str, base: str, texto: str) -> str | None:
    sopa = BeautifulSoup(html, "html.parser")
    for a in sopa.find_all("a", href=True):
        if texto.lower() in a.get_text(" ", strip=True).lower():
            return urljoin(base, a["href"].strip())
    return None
```

- `find_all("a", href=True)` y `get_text()` son la API básica de BeautifulSoup [BeautifulSoup docs]; `urljoin` resuelve enlaces relativos [Python urllib.parse].

**Nota:** buscar por **texto del enlace** aguanta mejor un rediseño que buscar por clases CSS. En Cobas hay que recorrer los bloques de clase y guardar el ISIN de la ficha junto a cada PDF: sirve para validar después el ISIN que extraiga el modelo. En Bestinver el parámetro `?h=` cambia en cada carga: **la URL no sirve como identificador** (de ahí el SHA-256, DEC D-1.2).

### 3.4 Webs que cambian

- Validar lo descargado: `Content-Type` de PDF y bytes iniciales `%PDF`; tamaño razonable (decenas o centenas de KB: el KIID de EJ pesa 80 KB).
- Guardar en el manifiesto la URL de la ficha, la del PDF, la fecha y hora de descarga y el SHA-256 (ENUNCIADO §4; DEC D-1.1, D-1.2).
- Fallar de forma visible: si una ficha no tiene el enlace esperado, registrar el error y seguir con las demás; contar cuántos KID se esperaban y cuántos llegaron.
- Ejemplo de cambio ya visible: el ENUNCIADO da `/fondos/` como punto de entrada de Azvalor, y las fichas cuelgan hoy de `/fondos-de-inversion/` (WEB).

### 3.5 Cuándo hace falta Playwright

Hace falta un navegador automatizado cuando el enlace **no está en el HTML que devuelve el servidor** sino que lo genera JavaScript (pestañas que cargan por AJAX, botones que montan la URL, banners que bloquean el contenido). Prueba rápida: si `requests` + BeautifulSoup no ven el enlace que sí se ve en el navegador, es contenido dinámico. Playwright para Python controla Chromium, Firefox o WebKit y espera a que la página cargue [Playwright Python]. En las tres fuentes del taller los enlaces aparecían en la respuesta del servidor (WEB), así que Playwright queda como **ampliación** (ENUNCIADO §4).

---

## 4. Amazon Bedrock: Converse, PDF y salidas estructuradas

**Idea.** Bedrock da acceso por API a modelos de varios proveedores. La **Converse API** ofrece la misma interfaz de mensajes para todos ellos; se le envía el PDF del KID como bloque `document` y se le impone un **esquema JSON** para la respuesta.

### 4.1 Converse API

- Operación `Converse` (y `ConverseStream`) del endpoint `bedrock-runtime`; requiere el permiso `bedrock:InvokeModel` [AWS Bedrock Converse].
- Campos del cuerpo: `messages`, `system`, `inferenceConfig` (`maxTokens`, `temperature`, `topP`, `stopSequences`), `toolConfig` (`tools`, `toolChoice`), **`outputConfig`** (`textFormat`), `additionalModelRequestFields` y otros [AWS Bedrock Converse].
- `modelId` admite un identificador de modelo **o de perfil de inferencia** [AWS Bedrock Converse].
- Respuesta: `output.message.content`, `stopReason` (`end_turn`, `tool_use`, `max_tokens`, `malformed_model_output`, `malformed_tool_use`...) y `usage` (`inputTokens`, `outputTokens`, `totalTokens`) [AWS Bedrock Converse].
- Bedrock "no almacena" el texto, las imágenes ni los documentos enviados: solo los usa para generar la respuesta [AWS Bedrock Converse].

### 4.2 El PDF como bloque `document`

| Campo de `DocumentBlock` | Qué dice la documentación |
|---|---|
| `format` | `pdf`, `csv`, `doc`, `docx`, `xls`, `xlsx`, `html`, `txt`, `md` [AWS DocumentBlock]. **Obligatorio en la práctica**: si falta, `ValidationException` "Document format is required." [AWS Converse guía] |
| `name` | 1-200 caracteres: alfanuméricos, espacios (no dos seguidos), guiones, paréntesis y corchetes. "Vulnerable a inyección de prompt": usar un nombre neutro [AWS DocumentBlock] |
| `source` | Unión: `bytes` (con un SDK no hace falta base64), `s3Location` (**solo modelos Amazon Nova**; los demás lo rechazan), `text`, `content` [AWS Converse guía] |
| `citations`, `context` | Citas sobre el documento [AWS DocumentBlock] |

- El mensaje debe incluir además un bloque `text` con la instrucción [AWS Converse guía]. Documentos solo en mensajes de rol `user` [AWS Bedrock restricciones].
- Límites: hasta **5 documentos** por petición y **4,5 MB** por documento, salvo PDF en Claude 4 y posteriores y PDF/DOCX en Nova; Claude admite como máximo **100 páginas de PDF** por petición [AWS Bedrock restricciones]. Anthropic añade que Bedrock limita la carga útil a 20 MB [Anthropic Claude en Bedrock].
- Cómo procesa Claude un PDF: convierte cada página en imagen y extrae su texto, y recibe ambos; cada página cuesta típicamente 1.500-3.000 tokens de texto más hasta 1.568 de imagen [Anthropic PDF]. Anthropic indica que el soporte de PDF en Bedrock está disponible tanto por Converse como por InvokeModel [Anthropic Claude en Bedrock]. **No se ha podido confirmar** en la documentación oficial si un bloque `document` por Converse, sin `citations`, llega al modelo con las imágenes de las páginas o solo con el texto extraído *(por verificar en el Taller 2)*. Importa para el SRI resaltado (§2.3).
- **Citas y salidas estructuradas son incompatibles** en modelos de Anthropic: activar ambas da error 400 [AWS salidas estructuradas].

### 4.3 Salidas estructuradas: los dos mecanismos

Según el anuncio del 4/2/2026, Bedrock ofrece salidas estructuradas en Converse, ConverseStream, InvokeModel e InvokeModelWithResponseStream, para los modelos Claude 4.5 y algunos modelos abiertos, en todas las regiones comerciales con Bedrock [AWS novedades 2026-02]. Para cada modelo concreto hay que mirar su ficha [AWS salidas estructuradas].

| | Formato de respuesta con esquema JSON | Herramienta en modo estricto |
|---|---|---|
| Dónde (Converse) | `outputConfig.textFormat` | `toolConfig.tools[].toolSpec.strict = true` |
| Estructura | `{"type": "json_schema", "structure": {"jsonSchema": {"schema": <cadena>, "name": ..., "description": ...}}}` | `toolSpec` con `name` (`[a-zA-Z0-9_-]+`, máx. 64), `description`, `inputSchema: {"json": <objeto>}`, `strict` |
| Esquema | **Cadena** con el JSON Schema (`schema`, obligatorio; `name` y `description`, opcionales) | Objeto JSON |
| Respuesta | Texto que cumple el esquema | Bloque de uso de herramienta con su entrada |
| Fuente | [AWS OutputFormat], [AWS JsonSchemaDefinition], [AWS salidas estructuradas] | [AWS ToolSpecification], [AWS salidas estructuradas] |

- `type` solo admite `json_schema` [AWS OutputFormat]. Los dos mecanismos se pueden usar por separado o juntos [AWS salidas estructuradas].
- Para forzar que se llame a la herramienta: `toolChoice` con `{"tool": {"name": ...}}` (o `any`). La referencia de la API dice que `tool` solo lo admiten "Anthropic Claude 3 and Amazon Nova models" [AWS ToolChoice]; el texto parece anterior a Claude 4 *(por verificar en el Taller 2 con el modelo elegido)*.

```python
from botocore.config import Config

cliente = boto3.client("bedrock-runtime", region_name=REGION,
                       config=Config(read_timeout=180))      # la 1.ª compilación tarda
resp = cliente.converse(
    modelId=MODELO,                                        # p. ej. un perfil "eu.<proveedor>.<modelo>"
    system=[{"text": "Extraes datos de un KID. Si un campo no aparece, devuelve null."}],
    messages=[{"role": "user", "content": [
        {"text": "Extrae los campos del documento adjunto."},
        {"document": {"format": "pdf", "name": "kid", "source": {"bytes": pdf}}},
    ]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0},
    outputConfig={"textFormat": {"type": "json_schema", "structure": {
        "jsonSchema": {"schema": json.dumps(ESQUEMA), "name": "kid_anexo_a"}}}},
)
if resp["stopReason"] != "end_turn":                       # p. ej. max_tokens -> JSON incompleto
    raise RuntimeError(resp["stopReason"])
campos = KID.model_validate_json(resp["output"]["message"]["content"][0]["text"])
```

Los nombres de parámetros del ejemplo son los de la referencia de la API; que el JSON llegue en el primer bloque `text` de `content` y la versión mínima de boto3 que acepta `outputConfig` *(por verificar en el Taller 2)*.

**Restricciones del esquema** [AWS salidas estructuradas]:

- Todo `object` debe declarar `"additionalProperties": false`; si no, `ValidationException`.
- Se admiten tipos básicos (incluido `null`), `enum`, `const`, `anyOf`, `$ref` internos, `format` (`date`, `date-time`...), `pattern` (sin *lookaround*) y `minItems` 0 o 1.
- **No** se admiten `minimum`/`maximum`/`multipleOf`, `minLength`/`maxLength` ni esquemas recursivos.
- Máximo **12 propiedades opcionales** y **16 propiedades con unión de tipos**. Para campos que pueden faltar, la propia documentación recomienda ponerlos en `required` con tipo `["string", "null"]`: el modelo devuelve `null` si no puede rellenarlo.
- La primera petición con un esquema nuevo **compila una gramática** (hasta ~90 s; *timeout* de lectura ≥ 120 s); se cachea 24 horas.
- Si se agota `maxTokens`, el JSON llega **incompleto** aunque haya salida estructurada: hay que mirar `stopReason`.

**Nota (esquema para el Anexo A).** Los 10 campos en `required` y nueve con tipo `[..., "null"]` (9 uniones ≤ 16; 0 opcionales); `sri` como `{"enum": [1, 2, 3, 4, 5, 6, 7, null]}`; `isin` con `pattern` `^[A-Z]{2}[A-Z0-9]{9}[0-9]$`; `fecha_documento` con `format: date`. Como no hay `minimum`/`maximum`, los rangos (porcentajes entre 0 y, digamos, 10; periodo entre 0 y 30 años) se validan después con el mismo modelo Pydantic del que sale el esquema (DEC D-2.1), igual que el dígito de control del ISIN. Si el esquema se genera con Pydantic hay que revisarlo: añade `title` (y `default` si hay valores por defecto), expresa los opcionales con `anyOf` (que también cuenta para el límite de 16) y solo pone `additionalProperties: false` si el modelo prohíbe campos extra.

### 4.4 Por qué no vale "pide JSON y parsea"

- Es una **regla** del ENUNCIADO (§5): salidas estructuradas, no pedir que "devuelva JSON" y parsear el texto.
- Con solo un prompt, el formato es una petición: el modelo puede añadir texto alrededor, comillas o bloques de código, omitir campos o inventar otros, y cada fallo exige reintentos y código de reparación. La salida estructurada **restringe la generación** a la gramática del esquema; AWS la presenta como la forma de eliminar los errores y bucles de reintento de los enfoques basados en el prompt [AWS salidas estructuradas].
- Lo que **no** garantiza: que los valores sean correctos (un SRI de otra clase, euros en lugar de %), ni un JSON completo si se corta por `maxTokens`. El esquema asegura la **forma**; la validación y la revisión manual, el **contenido**.

### 4.5 Región, perfiles `eu.` y acceso al modelo

- Un **perfil de inferencia entre regiones** enruta la petición a una región de una geografía (`us`, `eu`, `apac`...) o a cualquiera (perfil global); no hay coste extra de enrutado: se paga el precio de la región de origen [AWS inferencia entre regiones]. El geográfico mantiene los datos dentro de la geografía; el global ahorra "aproximadamente un 10 %" [AWS inferencia entre regiones]. Anthropic lo expresa al revés: los perfiles regionales llevan un 10 % de sobreprecio frente al global, desde Claude Sonnet 4.5 [Anthropic Claude en Bedrock].
- Para los Claude recientes, llamar con el ID base del modelo da error 400 ("on-demand throughput isn't supported"): hay que usar el ID del perfil, que es el ID base con prefijo (`us.`, `eu.`, `global.`) [Anthropic Claude en Bedrock].
- **IAM con perfil geográfico**: permitir `bedrock:InvokeModel` sobre el perfil **y** sobre el modelo fundacional en la región de origen y en **todas** las regiones de destino del perfil; una SCP que bloquee regiones de destino rompe la inferencia [AWS inferencia geográfica].
- **Acceso al modelo**: la mayoría se habilitan solos en la primera invocación si el rol tiene `aws-marketplace:Subscribe`, `Unsubscribe` y `ViewSubscriptions` y la cuenta tiene un método de pago válido; para modelos de Anthropic anteriores a Claude Opus 4.7 hay que rellenar antes un formulario de caso de uso (pide una URL; vale la de un repositorio) [AWS acceso a modelos].
- Región: la de la práctica sigue abierta (DEC D-0.2). Qué regiones de destino tiene cada perfil `eu.` desde `eu-west-3` está en la tabla de perfiles soportados [AWS perfiles soportados] *(por verificar en el Taller 2 para el modelo elegido)*.

### 4.6 Cuotas y coste

- Las cuotas de inferencia son por **tokens** (y peticiones) por minuto y modelo; las cuentas nuevas pueden tener valores **inferiores** a los publicados y los aumentos no son automáticos; al superarlas, `ThrottlingException` (429) [AWS cuotas Bedrock], [AWS Bedrock Converse].
- Se paga por token de entrada y de salida, con precios distintos por modelo y región; la inferencia por lotes cuesta un 50 % menos en algunos modelos [AWS precios Bedrock].

**Nota (orden de magnitud).** Un KID de 3 páginas con Claude: 3 × (1.500-3.000) tokens de texto + hasta 3 × 1.568 de imagen ≈ 9.000-14.000 tokens de entrada, más unos cientos de salida [Anthropic PDF]. Para 15-50 documentos, la factura de Bedrock es pequeña frente al coste fijo de Aurora o ECS; el riesgo real son las **cuotas** de una cuenta nueva, que se evitan con pausa entre documentos y reintento con espera exponencial.

---

## 5. Aurora PostgreSQL Serverless v2 con RDS Data API

**Idea.** Aurora Serverless v2 es PostgreSQL gestionado cuya capacidad se mide en **ACU** y se ajusta sola; con mínimo 0 se **pausa** sin conexiones. La **Data API** permite ejecutar SQL por HTTPS con credenciales de Secrets Manager, sin VPC ni driver en la Lambda (DEC D-3.1).

### 5.1 Escalado y auto-pausa

- Capacidad entre 0 y 256 ACU en pasos de 0,5 (`serverlessv2_scaling_configuration` en Terraform, con instancias `db.serverless`) [Terraform aws_rds_cluster].
- **Mínimo 0 ACU = auto-pausa**: tras `SecondsUntilAutoPause` sin conexiones de usuario (300 s por defecto y mínimo; máximo 86.400) la instancia se pausa y **no cobra capacidad**; el almacenamiento sí se sigue cobrando [AWS Aurora auto-pausa].
- Requiere Aurora PostgreSQL 16.3, 15.7, 14.12, 13.15 o superiores [AWS Aurora auto-pausa].
- Reanudar tarda **unos 15 s**; tras más de 24 h en pausa, 30 s o más. Una petición de la **Data API reanuda** el escritor y después se procesa. Conexiones abiertas (un cliente de SQL olvidado, RDS Proxy) impiden la pausa [AWS Aurora auto-pausa].

### 5.2 Data API

- Se activa al crear el clúster (`--enable-http-endpoint`, parámetro `EnableHttpEndpoint`) o después con `aws rds enable-http-endpoint --resource-arn ...` [AWS Data API activar]; en Terraform, `enable_http_endpoint` [Terraform aws_rds_cluster].
- Llamada: cliente `rds-data`, `execute_statement(resourceArn=..., secretArn=..., database=..., sql=..., parameters=[...])`; sin `transactionId`, cada llamada se confirma sola [AWS Data API Python].
- Parámetros con nombre (`:sri`) como `{"name": ..., "value": {...}}`; el valor es uno de `stringValue`, `longValue`, `doubleValue`, `booleanValue`, `blobValue`, `arrayValue` o `isNull` [AWS Data API Field], con `typeHint` opcional `DECIMAL`, `DATE` (`YYYY-MM-DD`), `TIMESTAMP`, `TIME`, `JSON` o `UUID` [AWS Data API SqlParameter].
- Límites: solo contra el escritor, respuesta máxima **1 MiB**, no admite clases de instancia T, y en PostgreSQL 14+ solo `scram-sha-256` [AWS Data API límites]. Cada llamada se cancela a los **45 s** (salvo `continueAfterTimeout`); el *timeout* del SDK debe superar 45 s, porque si el SDK corta antes y **reintenta**, puede insertar dos veces [AWS Data API timeouts]. Una transacción caduca a los 3 minutos sin llamadas [AWS Data API Python].
- Permisos mínimos: `rds-data:ExecuteStatement` (y `BatchExecuteStatement`, `BeginTransaction`, `CommitTransaction`, `RollbackTransaction` si se usan) sobre el ARN del clúster, y `secretsmanager:GetSecretValue` sobre el secreto [AWS Data API permisos].

```python
rds = boto3.client("rds-data", region_name=REGION)
rds.execute_statement(
    resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database="kid",
    sql="INSERT INTO kid (sha256, isin, sri, gastos_corrientes_pct) "
        "VALUES (:sha, :isin, :sri, :gc) ON CONFLICT (sha256) DO NOTHING",
    parameters=[
        {"name": "sha", "value": {"stringValue": sha256}},
        {"name": "isin", "value": {"stringValue": isin} if isin else {"isNull": True}},
        {"name": "sri", "value": {"longValue": sri}},
        {"name": "gc", "value": {"stringValue": "1.78"}, "typeHint": "DECIMAL"},
    ])
```

### 5.3 El secreto, gestionado por RDS

- Con `--manage-master-user-password` (Terraform `manage_master_user_password = true`) RDS **genera la contraseña**, la guarda en Secrets Manager, la **rota cada 7 días** por defecto y borra el secreto al borrar el clúster; su ARN sale en `MasterUserSecret.SecretArn` (en Terraform, `master_user_secret[0].secret_arn`) [AWS Aurora secretos], [Terraform aws_rds_cluster]. Secrets Manager se cobra aparte [AWS Aurora secretos].
- Encaja con DEC D-0.4: la contraseña nunca pasa por el repositorio ni por Terraform.

**Nota:** el secreto gestionado se llama `rds!cluster-...`, mientras que la política de ejemplo de la Data API limita `GetSecretValue` a `secret:rds-db-credentials/*`. Copiada tal cual, la Data API daría `AccessDeniedException`: hay que poner el ARN real del secreto. Que la Data API acepte el secreto gestionado por RDS está asumido en DEC D-0.4 *(por verificar en el Taller 2)*.

### 5.4 Coste

- En los ejemplos de la página de precios (EE. UU. Este): 0,12 $ por ACU-hora (Aurora Standard), 0,10 $ por GB-mes de almacenamiento, 0,20 $ por millón de E/S; Data API facturada por petición, contando cada 32 KB de carga como una petición más, con un millón de peticiones al mes gratis el primer año [AWS precios Aurora]. Los precios de las regiones europeas no se han consultado *(por verificar)*.

**Nota:** a ese precio, 0,5 ACU encendidas 24 h son unos 1,44 $/día (≈ 43 $/mes), comparable a los 2-3 $/día de ECS Express (DEC D-5.2). Con mínimo 0 y una pausa de 5 minutos, una API consultada de vez en cuando paga minutos, no días; a cambio, la primera petición tras la pausa tarda ~15 s, y la Function URL y Streamlit deben tolerarlo (*timeouts* > 15-30 s, reintento). Para importes, `NUMERIC` (enviado con `typeHint: DECIMAL` como cadena) y no `doubleValue`.

---

## 6. Carga idempotente con `INSERT ... ON CONFLICT`

**Idea.** El ENUNCIADO pide "evitar duplicados si un documento se procesa dos veces" (§4). En PostgreSQL se consigue con una restricción única y un `INSERT ... ON CONFLICT`, que es **atómico**: o inserta o aplica la acción alternativa, "incluso con alta concurrencia" [PostgreSQL INSERT].

```sql
CREATE TABLE kid (
  sha256                 char(64) PRIMARY KEY,         -- identidad del PDF (DEC D-1.2)
  isin                   char(12),
  fecha_documento        date,
  sri                    smallint CHECK (sri BETWEEN 1 AND 7),
  gastos_corrientes_pct  numeric(6,3),
  url_pdf                text NOT NULL,
  descargado_en          timestamptz NOT NULL
);

INSERT INTO kid (sha256, isin, fecha_documento, sri, gastos_corrientes_pct, url_pdf, descargado_en)
VALUES (:sha, :isin, :fecha, :sri, :gc, :url, :ts)
ON CONFLICT (sha256) DO UPDATE
  SET sri = EXCLUDED.sri, gastos_corrientes_pct = EXCLUDED.gastos_corrientes_pct;
```

- `ON CONFLICT DO NOTHING` simplemente no inserta; `DO UPDATE` actualiza la fila existente y accede a la fila propuesta mediante la tabla especial **`EXCLUDED`**; `DO UPDATE` exige indicar el objetivo del conflicto (columnas con índice único o restricción) [PostgreSQL INSERT].
- Un mismo `INSERT` no puede afectar dos veces a la misma fila: si un lote trae dos filas con la misma clave, error de cardinalidad; hay que deduplicar antes [PostgreSQL INSERT].
- `RETURNING` devuelve solo las filas insertadas o actualizadas [PostgreSQL INSERT].

**Nota (qué elegir).** `DO NOTHING` si el PDF no cambia y la extracción tampoco (mismo SHA-256 = mismo contenido). `DO UPDATE` si se quiere **reextraer** con otro modelo o prompt y sobrescribir los campos; en ese caso conviene guardar también el modelo y la versión del esquema. Y un KID nuevo del mismo ISIN es **otro** SHA-256: otra fila, con lo que se conserva el histórico (DEC D-1.2). Esta idempotencia es también la defensa frente a los reintentos del SDK de §5.2.

---

## 7. FastAPI en Lambda con Function URL

**Idea.** Una Function URL da a la Lambda un endpoint HTTPS propio sin API Gateway. FastAPI es una aplicación ASGI y Lambda recibe eventos, así que hace falta un adaptador: **Mangum** (dentro del código) o **AWS Lambda Web Adapter** (una extensión que reenvía las peticiones a un servidor web normal).

### 7.1 Function URL

- Formato `https://<url-id>.lambda-url.<región>.on.aws`; la URL no cambia una vez creada; acepta `AuthType` `AWS_IAM` (peticiones firmadas con SigV4) o `NONE` (pública) [AWS Function URL], [AWS Function URL acceso].
- Con `NONE`, la política basada en recursos debe permitir `lambda:InvokeFunctionUrl` **y**, para URL creadas desde octubre de 2025, también `lambda:InvokeFunction` (con la condición `lambda:InvokedViaFunctionUrl`); la consola la crea sola, pero con la CLI, CloudFormation o la API (y por tanto con Terraform) hay que añadirla a mano; sin ella, 403 [AWS Function URL acceso].
- El evento sigue el **formato 2.0 de API Gateway HTTP API** [AWS Function URL invocación], el mismo que el curso usa en L14 «Exponer una función por HTTP».
- CORS configurable en la propia URL (mejor que añadir cabeceras desde la función: se duplicarían); limitar con concurrencia reservada (RPS máx. = 10 × concurrencia; con 0 se desactiva) [AWS Function URL].
- Límites de Lambda: 6 MB de petición y de respuesta en invocación síncrona, 900 s de *timeout* [AWS Lambda cuotas].

### 7.2 Mangum o Lambda Web Adapter

```python
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/fondos/{isin}")
def fondo(isin: str): ...

handler = Mangum(app, lifespan="off")     # controlador de la Lambda
```

| | Mangum | AWS Lambda Web Adapter |
|---|---|---|
| Qué es | Adaptador ASGI para Lambda; admite Function URL, API Gateway (HTTP y REST), ALB y Lambda@Edge [Mangum] | Extensión que arranca junto a un servidor web y le pasa las peticiones; admite API Gateway, Function URL y ALB [AWS LWA] |
| Código | `handler = Mangum(app)` [Mangum] | Ninguno: se arranca `uvicorn` como siempre |
| Imagen Docker (L18) | `CMD ["app.handler"]` sobre la imagen base de Lambda | `COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 /lambda-adapter /opt/extensions/lambda-adapter`; puerto en `AWS_LWA_PORT` (8080 por defecto); comprobación de arranque en `/` por defecto [AWS LWA] |
| Zip | Dependencia más | Capa del adaptador + `AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap` + script de arranque [AWS LWA] |
| A favor | Simple y explícito | La misma imagen sirve en ECS y en Lambda |

**Nota:** la regla 5 del ENUNCIADO (los datos solo se exponen por la API y la aplicación) es compatible con una Function URL `NONE` si la API es **de solo lectura** y no sirve los PDF ni el bucket. Streamlit en ECS llama a la API desde el servidor, así que no necesita CORS (DEC D-4.1). Si la API consulta Aurora por Data API, la primera llamada tras la pausa tarda ~15 s (§5.1): poner el *timeout* de la Lambda bastante por encima.

---

## 8. Para la práctica

### 8.1 Lista de comprobación por fase

| Fase | Comprobar |
|---|---|
| Captura | `robots.txt` revisado y decisión anotada (DEC D-1.1, §3.1); `User-Agent` propio, `timeout`, pausa; enlace localizado por texto; validación `%PDF`; manifiesto con URL de ficha y PDF, fecha y SHA-256; ≥ 2 fuentes y ≥ 15 documentos (ENUNCIADO §4) |
| Almacenamiento | Bucket privado en la región de trabajo; clave derivada del SHA-256; metadatos de origen en el objeto o en el manifiesto |
| Extracción | Modelo con PDF y salidas estructuradas disponible en la región o vía perfil `eu.` (§4.5); acceso al modelo habilitado; esquema con `additionalProperties: false`, campos nullable en `required` (§4.3); `stopReason` comprobado; validación posterior de rangos e ISIN; `temperature` 0 |
| Base de datos | Data API activada; secreto gestionado por RDS con su ARN real en la política (§5.3); `CHECK` y `NUMERIC`; `ON CONFLICT` sobre el SHA-256 (§6); recuentos documentos = filas |
| API | Function URL con permisos completos (§7.1); solo lectura; *timeout* que absorba la reanudación de Aurora |
| Aplicación | Lee solo de la API (DEC D-4.1) |
| IaC y despliegue | Todo en Terraform; Actions con OIDC; nada de credenciales; plan de apagado (DEC D-5.2) |

### 8.2 Riesgos

| Riesgo | Síntoma | Mitigación |
|---|---|---|
| Una web cambia o bloquea | Enlace no encontrado, 403/418 | Búsqueda por texto, error visible y recuento; no saltarse bloqueos; fuente alternativa |
| `robots.txt` restrictivo (Bestinver, §3.1) | Pregunta en la exposición | Decisión justificada en DEC D-1.1 |
| Euros leídos como % (§2.5) | `gastos_corrientes_pct` = 150 | Instrucción explícita en el prompt + validación de rango |
| SRI mal leído (§2.3) | SRI distinto del de la ficha web | Comparar con la web o con KID revisados a mano |
| KIID antiguo en lugar de KID (§2.6) | Faltan periodo y escenarios | Campo `tipo_documento`; `null` donde no exista |
| Modelo sin salidas estructuradas o sin PDF en la región | `ValidationException` | Elegir el modelo con su ficha antes de la región (DEC D-0.2, D-2.2) |
| Cuotas de cuenta nueva | `ThrottlingException` | Pausa entre documentos y espera exponencial |
| Primera compilación del esquema | *Timeout* en la primera llamada | `read_timeout` ≥ 120 s [AWS salidas estructuradas] |
| JSON cortado | `stopReason = max_tokens` | `maxTokens` holgado y comprobación |
| Reintento que duplica | Filas repetidas | `ON CONFLICT` (§6); *timeout* del SDK > 45 s |
| Coste fijo de Aurora y ECS | Factura en días sin uso | Mínimo 0 ACU; `terraform destroy` fuera de pruebas (DEC D-5.2) |
| Inyección de prompt desde el PDF o su nombre | Campos absurdos | `name` neutro; el esquema limita la forma; validar el contenido |

---

## 9. Preguntas de repaso

1. ¿Qué norma obliga a la gestora a publicar el KID en su web, cuál es su extensión máxima y por qué la estructura fija del KID facilita la extracción?
2. En el cuadro «Composición de los costes» de un fondo, ¿en qué unidad va la columna de la derecha y dónde está el porcentaje que pide el Anexo A? ¿Qué validación detecta el error?
3. ¿Qué indica `Disallow: /*.pdf$` en un `robots.txt`? ¿Por qué `can_fetch` puede dar `True` para el PDF de Bestinver y qué debería hacer el grupo?
4. Escribe la parte `outputConfig` de una llamada a Converse con esquema JSON. ¿Por qué el esquema va como cadena y qué restricciones obliga a cumplir Bedrock?
5. ¿Cómo se representa en el esquema un campo que puede no aparecer en el KID, sin superar el límite de propiedades opcionales?
6. ¿Qué garantiza una salida estructurada y qué no? Pon un ejemplo de respuesta válida según el esquema pero incorrecta.
7. ¿Qué pasa con Aurora Serverless v2 si la capacidad mínima es 0 ACU? ¿Qué se sigue cobrando y qué efecto tiene en la primera petición de la API?
8. ¿Por qué `INSERT ... ON CONFLICT` sobre el SHA-256 del PDF protege a la vez frente a reprocesar un documento y frente a un reintento automático del SDK de la Data API?

---

## Referencias

Normativa (copias oficiales del DOUE publicadas por el BOE; en EUR-Lex con el mismo número CELEX):
- **R1286** — Reglamento (UE) 1286/2014, DOUE L 352 de 9.12.2014: https://www.boe.es/doue/2014/352/L00001-00023.pdf (EUR-Lex: https://eur-lex.europa.eu/eli/reg/2014/1286/oj)
- **RD653** — Reglamento Delegado (UE) 2017/653, DOUE L 100 de 12.4.2017: https://www.boe.es/doue/2017/100/L00001-00052.pdf
- **RD2268** — Corrección de errores del Reglamento Delegado (UE) 2021/2268 (texto completo sustituido), DOUE L 115 de 13.4.2022: https://www.boe.es/doue/2022/115/L00187-00229.pdf (EUR-Lex: https://eur-lex.europa.eu/eli/reg_del/2021/2268/oj)
- **RD975** — Reglamento Delegado (UE) 2022/975, DOUE L 167 de 2022: https://www.boe.es/doue/2022/167/L00035-00037.pdf
- **DIR2261** — Directiva (UE) 2021/2261, DOUE L 455 de 20.12.2021: https://www.boe.es/doue/2021/455/L00015-00017.pdf

Scraping:
- **[RFC 9309]** — Robots Exclusion Protocol: https://www.rfc-editor.org/rfc/rfc9309.html
- **[Python robotparser]** — https://docs.python.org/3/library/urllib.robotparser.html
- **[Python urllib.parse]** — https://docs.python.org/3/library/urllib.parse.html
- **[requests quickstart]** — https://requests.readthedocs.io/en/latest/user/quickstart/
- **[BeautifulSoup docs]** — https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **[Playwright Python]** — https://playwright.dev/python/docs/intro

Bedrock:
- **[AWS Bedrock Converse]** — https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
- **[AWS Converse guía]** — https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- **[AWS DocumentBlock]** — https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_DocumentBlock.html
- **[AWS Bedrock restricciones]** — https://docs.aws.amazon.com/bedrock/latest/userguide/inference-api-restrictions.html
- **[AWS salidas estructuradas]** — https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html
- **[AWS novedades 2026-02]** — https://aws.amazon.com/about-aws/whats-new/2026/02/structured-outputs-available-amazon-bedrock
- **[AWS OutputFormat]** — https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_OutputFormat.html
- **[AWS JsonSchemaDefinition]** — https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_JsonSchemaDefinition.html
- **[AWS ToolSpecification]** — https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolSpecification.html
- **[AWS ToolChoice]** — https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolChoice.html
- **[AWS inferencia entre regiones]** — https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html
- **[AWS inferencia geográfica]** — https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
- **[AWS perfiles soportados]** — https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
- **[AWS acceso a modelos]** — https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html
- **[AWS cuotas Bedrock]** — https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html
- **[AWS precios Bedrock]** — https://aws.amazon.com/bedrock/pricing/
- **[Anthropic PDF]** — https://platform.claude.com/docs/en/build-with-claude/pdf-support
- **[Anthropic Claude en Bedrock]** — https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock-legacy

Aurora, Data API y PostgreSQL:
- **[AWS Aurora auto-pausa]** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html
- **[AWS Data API activar]** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.enabling.html
- **[AWS Data API Python]** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.calling.python.html
- **[AWS Data API límites]** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.limitations.html
- **[AWS Data API timeouts]** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api-timeouts.html
- **[AWS Data API permisos]** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.access.html
- **[AWS Data API Field]** — https://docs.aws.amazon.com/rdsdataservice/latest/APIReference/API_Field.html
- **[AWS Data API SqlParameter]** — https://docs.aws.amazon.com/rdsdataservice/latest/APIReference/API_SqlParameter.html
- **[AWS Aurora secretos]** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-secrets-manager.html
- **[AWS precios Aurora]** — https://aws.amazon.com/rds/aurora/pricing/
- **[Terraform aws_rds_cluster]** — https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster
- **[PostgreSQL INSERT]** — https://www.postgresql.org/docs/current/sql-insert.html

Lambda y FastAPI:
- **[AWS Function URL]** — https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html
- **[AWS Function URL acceso]** — https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html
- **[AWS Function URL invocación]** — https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html
- **[AWS Lambda cuotas]** — https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
- **[Mangum]** — https://mangum.fastapiexpert.com/
- **[AWS LWA]** — https://github.com/awslabs/aws-lambda-web-adapter
