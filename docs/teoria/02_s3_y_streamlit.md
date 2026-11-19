# Amazon S3 y aplicaciones de datos con Streamlit

> **Fuentes:**
> - **L11** = `docs/raw/miax-cloud-main/content/11-s3.md`, lección «Amazon S3» de la web del curso (leída completa; cada `---` es una diapositiva y se cita por su título).
> - **L11b** = `docs/raw/miax-cloud-main/content/11b-streamlit.md`, lección «Aplicaciones de datos con Streamlit» (leída completa).
> - **EJ** = ejemplos del curso: `docs/raw/miax-cloud-main/ejemplos/s3/boto3_s3_example.ipynb` (`EJ s3/boto3`) y `docs/raw/miax-cloud-main/ejemplos/streamlit/` (`01_hola.py` a `05_ficheros.py`, `app.py`, `miax-streamlit.service`, `requirements.txt`).
> - **CAMBIOS** = `docs/raw/miax-cloud-main/CAMBIOS.md` (diferencias con la presentación original).
> - **T14** = `docs/raw/transcripciones/T14.txt`, transcripción automática de la clase del 14/11/2026. Tramo principal **~03:08:42-04:47:50** (S3 completo y cierre de la clase). Antes de ~03:08 se cierra el ejercicio de FastAPI en EC2, que corresponde a otro documento. Menciones sueltas: ~00:00:27, ~00:23:17.
> - **T13** = `docs/raw/transcripciones/T13.txt`, clase del 13/11/2026. Menciones de S3 y del panel: ~00:14:37, ~02:27:06-02:29:46, ~02:41:07-02:42:20, ~02:53:13, ~03:47:09-03:47:28, ~04:42:28-04:42:50, ~04:44:52-04:45:13 (zonas horarias en cron), ~04:46:31.
> - **ENUNCIADO** = `docs/raw/transcripciones/enunciado.txt` (práctica B7, §1, §4-§7).
> - **DEC** = `docs/DECISIONES.md` (decisiones ya tomadas en este repositorio: D-0.2, D-0.4, D-1.2, D-4.1, D-5.1).
>
> **Convenciones:** "(T14 ~03:40)" = hora aproximada en la transcripción; lo que viene de ella es **paráfrasis** de un texto automático muy ruidoso ("ese tres", "backet", "baquet" = S3, bucket), y lo que no se entiende bien va marcado *(dudoso)*. "(L11 «Clases de almacenamiento»)" = diapositiva por su título. "(EJ streamlit/03_filtros.py)" = fichero de ejemplo. **Nota:** = contenido propio (conexiones, correcciones, cálculos), no del material de clase. Los nombres de bucket se escriben con el marcador `miax-<alias>-datos` de la web.
>
> Escrito el 19/11/2026.

---

## 1. Qué es S3

**Idea.** S3 (*Simple Storage Service*) es el almacenamiento de **objetos** de AWS: guardas ficheros enteros (con sus metadatos) bajo un nombre dentro de un contenedor, y los recuperas por ese nombre. No es un disco ni un sistema de ficheros (L11 «Qué es S3»; T14 ~03:08:42-03:09:11).

### 1.1 Propiedades básicas

| Propiedad | Valor en la lección | Lo que añadió el profesor |
|---|---|---|
| Durabilidad (Standard) | 99,999999999 % ("once nueves") | La comparó con los "tres o cuatro nueves" del EBS visto el día anterior; aun así se pueden perder datos (T14 ~03:09:29-03:09:48; T13 ~02:45:25) |
| Disponibilidad (Standard) | 99,99 % al año | Hizo la cuenta en clase: "prácticamente una hora" al año sin servicio sin que te devuelvan nada; recordó caídas reales de una zona de EE. UU. (T14 ~03:09:48-03:11:39) |
| Replicación | Al menos 3 zonas de disponibilidad, salvo clases de una zona | Igual (T14 ~03:11:48) |
| Tamaño máximo de objeto | **50 TB** | "Una burrada"; puedes subir 800 ficheros de 1 TB sin problema; los pequeños se suben y bajan "en nada" (T14 ~03:12:26-03:12:45) |
| Consistencia | Fuerte: tras escribir, toda lectura ve la versión nueva | Lo enlazó con el versionado (§3.4) (T14 ~03:12:53) |
| Cifrado | Todos los objetos, por defecto | §3.3 |
| Acceso público | Bloqueado por defecto | "Antes era público"; ahora, para abrirlo, "lo tienes que hacer de verdad" (T14 ~03:13:53-03:14:22) |

(L11 «Qué es S3»; CAMBIOS: el límite subió de 5 TB a 50 TB.)

**Nota (cálculo).** 0,01 % de 365 × 24 h = 0,876 h, unos **53 minutos** al año. El acuerdo de nivel de servicio (SLA) con devolución de créditos es un documento aparte, con umbrales propios; la cifra de disponibilidad de diseño no es lo mismo que lo que AWS compensa.

### 1.2 Para qué lo usa la gente

- En T13 el profesor lo presentó como "una carpetita en la nube" donde dejar y coger información, lanzada en 2006 y "superrápida y superfiable" (T13 ~00:14:37, ~00:16:53).
- Hubo empresas montadas solo sobre S3 con "una interfaz bonita por delante" (T13 ~02:41:26-02:41:36).
- Su forma de trabajar preferida: procesar en una máquina, guardar los resultados en un bucket y "bajarlos, subirlos, borrarlos" desde ahí, en lugar de dejarlos en el disco de la instancia (T13 ~03:47:09-03:47:28).
- El patrón que anticipó varias veces: un script programado que descarga datos de una web, los comprueba y los deja en S3 para consumirlos después con otra cosa (T13 ~04:42:28-04:42:50; T14 ~00:23:17). Es exactamente la fase de captura de la práctica (§9).

---

## 2. Buckets, objetos, claves y regiones

**Idea.** S3 es en el fondo un **mapa de «bucket + clave + versión» a objeto**. Todo lo demás (carpetas, URL, rutas `s3://`) es una forma de escribir esa clave (L11 «Claves»).

### 2.1 Los cuatro conceptos

| Concepto | Qué es | Detalle |
|---|---|---|
| **Bucket** | Contenedor de objetos | Nombre **único en todo AWS**, no solo en tu cuenta; vive en una región; se le conceden o deniegan permisos con políticas de IAM y del bucket (L11 «Buckets») |
| **Objeto** | Datos + metadatos | Los datos son opacos para S3 (L11 «Objetos»); §3.5 |
| **Clave** | Identificador del objeto dentro del bucket | Exactamente una por objeto (L11 «Claves») |
| **Versión** | Historial de un objeto | Solo si activas el versionado (L11 «Claves»; §3.4) |

Ejemplo de la lección (L11 «Buckets»):

```text
https://miax-<alias>-datos.s3.<region>.amazonaws.com/market/2018/datos.csv
        └──── bucket ─────┘                          └──── clave ─────────┘
```

El profesor desmontó la URL en la consola: lo que va antes de `.s3` es el bucket, en medio aparece la región (`eu-west-3`) y el servicio, y lo que va después de `.com/` es la clave (él la llamó *path*). Como el bucket bloqueaba el acceso público, la URL existía pero no se podía abrir (T14 ~03:29:58-03:30:29, ~03:32:47-03:33:50). Con versionado, la versión se añadiría al final (T14 ~03:33:50).

### 2.2 Las «carpetas» no existen

- `market/2018/` es solo parte de la clave, un **prefijo**; la consola lo pinta como carpetas por comodidad (L11 «Claves»).
- En clase: **Create folder** crea una "carpeta virtual", una ruta que "realmente no existe", pero en la práctica es lo mismo que trabajar con carpetas (T14 ~03:30:49-03:31:21). Si necesitas un sistema de ficheros de verdad, AWS ofrece EFS u otros servicios de ficheros (T14 ~03:30:29-03:30:47; T13 ~02:41:44-02:42:20).
- En T13 mencionó que AWS ha añadido hace poco una forma de usar S3 como sistema de ficheros compartido entre máquinas, que aparece al crear una instancia (T13 ~02:53:13) *(dudoso: no dijo el nombre del servicio)*. Al crear un bucket se ve también el tipo **directorio** junto al **general purpose**, que es el que se usa siempre (T14 ~03:17:11).

**Nota.** Que las carpetas sean prefijos tiene consecuencias prácticas: `aws s3 ls s3://bucket/market/` y `list_objects_v2(Prefix="market/")` filtran por el principio de la clave; "borrar una carpeta" es borrar todos los objetos con ese prefijo (`--recursive`, §4.2); y renombrar una "carpeta" es copiar y borrar cada objeto.

### 2.3 Nombres únicos

- En clase la creación de un bucket falló porque el nombre ya existía en otra cuenta: los nombres compiten con los de todo el mundo, así que **cuanto más largo, más difícil que coincida**; el profesor recomendó añadir algo propio o números (T14 ~03:40:19-03:40:43).
- Motivo que dio: S3 "estaba creado para exponerse a Internet"; en cuanto creas el bucket ya tienes tu URL, aunque lo bloquees (T14 ~03:40:52-03:41:11).
- Dudó en voz alta si la unicidad era absolutamente global o por región, porque la URL lleva la región; recordó que "antes" era global y que los nombres eran cada vez más largos (T14 ~03:41:31-03:41:56) *(dudoso)*.
- Un alumno comentó el problema de los buckets expuestos que recibían peticiones fallidas de terceros y aun así se cobraban (T14 ~03:42:07-03:43:01) *(dudoso: tramo muy ruidoso)*.

**Nota.** La lección es la referencia: el nombre de un bucket de propósito general es único en todo AWS (L11 «Buckets»). Que la URL lleve la región no cambia eso. En la web del curso los nombres siguen el patrón `miax-<alias>-datos`, con el alias que cada uno configura en la página (T14 ~03:50:34).

### 2.4 Regiones y requisitos legales

- Cada bucket vive en la región que elijas, para optimizar **latencia**, **coste** o cumplir **requisitos legales** (por ejemplo, datos en la UE); los objetos **nunca salen** de la región salvo que los copies o repliques (L11 «Regiones»).
- El profesor insistió en lo legal: si los datos no pueden salir de Europa, el bucket va en una región europea y además se restringe el acceso a quien no esté en Europa; si alguien lo salta con una VPN, el infractor es él, pero tú tienes que poner "los máximos cortafuegos posibles" (T14 ~03:34:07-03:35:34).
- En sanidad a veces se exige hasta el **hospital o el edificio** donde pueden estar los datos (T14 ~03:35:34).
- Sobre datos personales y RGPD recordó que, si alguien pide que se borren sus datos, deben desaparecer en un plazo corto (citó 30 días), aunque los logs puedan guardarse más; remitió a la asignatura de derecho de datos e IA (T14 ~03:28:40-03:29:14).
- Contó también que en clase se habilitó Estocolmo para quien no podía seleccionar París (T14 ~00:00:27; DEC D-0.2).

**Nota.** En clase el profesor dijo también que S3 "es un producto global, no definido por la región" (T14 ~03:11:48). Eso choca con la lección y con lo que él mismo mostró en la URL: el **espacio de nombres** es global y la consola lista los buckets de todas las regiones en una sola vista, pero cada bucket y sus datos están en **una** región. Sobre el RGPD, el plazo general para atender una solicitud de supresión es de un mes (ampliable en casos complejos); no es asesoramiento jurídico.

---

## 3. Configuración de un bucket

**Idea.** Al crear un bucket desde la consola se deciden pocas cosas, pero importantes: tipo, propiedad de los objetos, acceso público, versionado, etiquetas y cifrado. El profesor recorrió el formulario en directo (T14 ~03:17:06-03:19:17; L11 «Desde la consola»).

### 3.1 Recorrido por el formulario

| Opción | Qué eligió en clase | Comentario |
|---|---|---|
| Tipo | *General purpose* | El de directorio es para otros usos (T14 ~03:17:11) |
| Nombre | Uno largo y propio | §2.3 |
| Copiar ajustes | Se puede partir de otro bucket | (T14 ~03:17:47) |
| Propiedad de objetos | ACL desactivadas, *Bucket owner enforced* | El dueño del bucket es dueño de todos los objetos (T14 ~03:17:47-03:18:05) |
| **Block all public access** | Activado | Desactivarlo abre el bucket a todo el mundo; se deja bloqueado (T14 ~03:18:05-03:18:25; L11 «Desde la consola») |
| Versionado | Se puede activar o desactivar con un clic | (T14 ~03:18:30-03:18:36) |
| Etiquetas (*tags*) | Opcionales | Metadatos del **recurso**; servirán con Terraform (T14 ~03:18:41-03:18:54) |
| Cifrado | Claves gestionadas por Amazon | (T14 ~03:18:59-03:19:17) |

Después subió `market_data` arrastrándolo a la consola ("eso es lo que hemos tardado en subir un archivo") y mostró las propiedades: propietario (el ID de la cuenta) y clase de almacenamiento Standard (T14 ~03:19:20-03:20:27). Para descargar, se pulsa el objeto y el botón de descarga; funciona porque estás dentro de la consola con tus credenciales (T14 ~03:37:30-03:37:55).

### 3.2 Bloqueo de acceso público y políticas

- El bloqueo de acceso público viene activado por defecto (L11 «Qué es S3»). Antes los buckets quedaban expuestos y había que cerrarlos a mano (T13 ~02:27:42-02:27:52; T14 ~03:14:10).
- S3 es uno de los servicios con un punto de acceso **siempre público** en Internet que tú restringes. Lo bueno: si quieres publicar un dato, ya está ahí. Lo malo: si se cuela un dato privado en algo expuesto, "la hemos liado", sobre todo con datos personales (T13 ~02:27:25-02:29:05).
- Quién puede leer y escribir se controla con políticas de IAM (de usuarios y roles) y con la política del propio bucket (L11 «Buckets»).

**Nota (ejemplo de política de bucket).** La lección no muestra ninguna. Una política habitual, que no abre nada y solo endurece el acceso, es denegar cualquier petición que no vaya por HTTPS:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "SoloHTTPS",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::miax-<alias>-datos", "arn:aws:s3:::miax-<alias>-datos/*"],
    "Condition": {"Bool": {"aws:SecureTransport": "false"}}
  }]
}
```

Una denegación explícita gana siempre a cualquier permiso; por eso este patrón es seguro de añadir.

### 3.3 Cifrado

- Todo objeto se cifra por defecto (L11 «Qué es S3»).
- En clase: dejó que Amazon gestione las claves; el tráfico va cifrado y "se las podemos pedir en cualquier momento" (T14 ~03:19:08-03:19:17). Llegó a decir que "Amazon no ve lo que subimos" y que S3 no puede leer los metadatos porque se cifran (T14 ~03:13:46, ~03:32:37-03:32:47) *(dudoso)*.

**Nota (corrección).** Con el cifrado por defecto (claves gestionadas por S3), AWS cifra los datos en disco y los descifra de forma transparente para cualquiera que tenga permiso de lectura. Protege frente al robo de discos, no frente a un acceso con permisos: la protección real son las políticas y el bloqueo público. Los metadatos del sistema (tamaño, fecha, tipo) los usa S3 para funcionar. Si se quiere controlar quién puede descifrar, existe el cifrado con claves de KMS propias, que la lección no trata.

### 3.4 Versionado

- Funciona "como un Git, pero por objeto": si sobrescribes un objeto, ves siempre la última versión, pero S3 guarda el histórico y puedes volver a una anterior; se activa y desactiva a voluntad (T14 ~03:12:53-03:13:42; L11 «Claves»).
- Anécdota de trazabilidad: una plataforma de recuento electoral montada en AWS donde, con metadatos y versionado, cada fichero era trazable hasta su origen sin dejar de ser anónimo (T14 ~03:43:23-03:44:52) *(dudoso en los detalles)*.

**Nota.** Con versionado activado, cada sobrescritura y cada borrado (que deja un "marcador de borrado") conservan las versiones antiguas, que **también se cobran**. Si se activa, conviene una regla de ciclo de vida que caduque versiones no actuales. Una vez activado, el versionado solo se puede **suspender**, no quitar.

### 3.5 Metadatos del objeto

- Un objeto son **datos** (el contenido; si es un PDF, el PDF) más **metadatos**: del sistema (última modificación, tamaño, `Content-Type`…) y personalizados, que defines al subir con cabeceras `x-amz-meta-...` (L11 «Objetos»; T14 ~03:32:00-03:32:26).
- El profesor sugirió usarlos para saber quién escribió o cambió un fichero, "cualquier cosa" (T14 ~03:32:26).
- No confundir con las **etiquetas del recurso** (§3.1), que describen el bucket; los objetos también admiten etiquetas propias.

**Nota (con boto3).** Los metadatos personalizados se pasan al subir y se leen sin descargar el objeto:

```python
s3.put_object(
    Bucket=bucket, Key=clave, Body=contenido, ContentType="application/pdf",
    Metadata={"source-url": url_pdf, "downloaded-at": "2026-11-19T10:00:00Z"},
)
cabecera = s3.head_object(Bucket=bucket, Key=clave)
print(cabecera["Metadata"])          # {'source-url': ..., 'downloaded-at': ...}
```

Tres límites conviene saberlos: los metadatos de usuario ocupan como mucho unos 2 KB, conviene que sean ASCII (las URL lo son; nombres con tildes, mejor en la base de datos) y **no se pueden modificar**: cambiarlos obliga a copiar el objeto sobre sí mismo. Las etiquetas del objeto, en cambio, sí se cambian.

---

## 4. Clases de almacenamiento y costes

**Idea.** Cuanto menos accedes a los datos, menos pagas por guardarlos y más pagas (o esperas) por leerlos (L11 «Clases de almacenamiento»). El profesor lo resumió así: **almacenar siempre es más barato; acceder es la parte cara** (T14 ~03:25:07-03:25:24).

### 4.1 Las clases

| Clase | Para (L11) | Lo que dijo el profesor |
|---|---|---|
| **Standard** | Uso general, acceso frecuente | La que sale por defecto; para datos que se leen a diario (T14 ~03:20:11-03:20:41, ~03:21:25) |
| **Express One Zone** | Latencia muy baja, una zona | Mucho más cara de almacenar; puso como ejemplo servir vídeo con latencias muy bajas (T14 ~03:27:03-03:27:34) |
| **Intelligent-Tiering** | Patrón de acceso desconocido o cambiante | Mueve los objetos de nivel según el uso; si empiezas a leer mucho algo que estaba en un nivel infrecuente, lo sube y lo cobra como tal (T14 ~03:21:34-03:22:25) |
| **Standard-IA / One Zone-IA** | Larga duración, acceso poco frecuente | Cada vez menos por guardar y más por cada llamada (T14 ~03:27:34-03:27:51) |
| **Glacier Instant / Flexible / Deep Archive** | Archivado a largo plazo | Para lo que se guarda por cumplimiento (puso 7 años) y solo se saca si lo pide una auditoría o el Estado; recuperar tiene coste por petición (T14 ~03:23:19-03:23:48, ~03:27:51-03:28:58) |

Las reglas de **ciclo de vida** mueven o borran objetos solas (L11 «Clases de almacenamiento»); el profesor lo mencionó como algo que se puede hacer "de manera automática" (T14 ~03:28:20).

### 4.2 Qué se cobra

Lo que se dijo en clase, sobre una tabla de precios que el profesor generó en directo con un asistente de IA y que advirtió que había que confirmar con la documentación de AWS (T14 ~03:24:31-03:28:07):

- **Subir es gratis**; se cobra al **descargar** hacia Internet, por GB. Cuidado con las copias de seguridad: recuperar 20 TB "empieza a costar dinero" (T14 ~03:20:41-03:21:08).
- **Almacenar**: unos 0,021-0,023 $ por GB y mes en Standard, "dos céntimos de dólar" (T14 ~03:25:37-03:25:45).
- **Peticiones**: las de escritura y listado, del orden de medio céntimo por cada 1.000; las de lectura, menos (T14 ~03:25:51-03:26:42) *(dudoso: cifras mal transcritas)*.
- **Archivo**: recuperar tiene un coste por petición y por GB; habló de duraciones mínimas de 30, 90 y 180 días según el nivel (T14 ~03:27:51-03:28:40) *(dudoso)*.
- El coste **es acumulativo**: si un mes guardas datos por 20, el siguiente pagas esos más los nuevos (20, 40, 60…) si nunca borras (T14 ~03:36:05-03:36:34).
- Hay una cantidad gratuita de almacenamiento y operaciones al mes que en el curso no se llegará a pasar (T14 ~03:35:51-03:36:05).
- Las tres cosas a pensar al elegir: **requisitos legales, dinero y latencia** (T14 ~03:34:07, ~03:35:46, ~03:36:38-03:37:04).
- Sobre la dependencia del proveedor (*vendor lock-in*): cuando lo tienes todo en un cloud, cambiarte cuesta tiempo, gente y código, y si suben precios "te lo comes" (T14 ~03:38:49-03:39:35).

**Nota.** Las "duraciones mínimas" de 30, 90 y 180 días corresponden, según la página de precios de AWS, al cobro mínimo de Standard-IA, Glacier Flexible Retrieval y Glacier Deep Archive: si borras antes, pagas igual ese tiempo. Intelligent-Tiering, en cambio, no cobra por recuperar, sino una pequeña tarifa de monitorización por objeto. Para KID de unos cientos de KB, Standard es la elección obvia: el coste será de céntimos.

### 4.3 Desde dónde se accede

- Por Internet, o desde una VPC de forma privada con un **endpoint de puerta de enlace** (L11 «Cómo se llega a S3»).
- En clase: desde una instancia EC2 se va por la red interna con el *gateway endpoint* y no se cobra; desde tu ordenador (cliente de Internet) sí, a partir de un límite (T14 ~03:15:01-03:15:43; T13 ~02:29:10-02:29:46).

---

## 5. Cinco formas de trabajar con S3

**Idea.** Las mismas operaciones se hacen desde la consola, la CLI, la extensión AWS Toolkit de VS Code, boto3 y pandas (L11 «Cómo trabajar con S3»; T14 ~03:14:24-03:15:01). El ejercicio de la lección es hacer el mismo recorrido (crear, subir, descargar) por tres caminos (L11 «Ejercicio: tres caminos»).

### 5.1 Consola y VS Code

- **Consola**: §3.1. Para borrar un bucket, la consola exige vaciarlo primero (con una confirmación escrita) y después escribir su nombre (T14 ~03:16:13-03:17:06).
- **AWS Toolkit en VS Code**: en el explorador de AWS, región, S3; crear bucket, subir con clic derecho y descargar (L11 «Desde VS Code»). En clase fue "bastante más rápido" que la consola: crear un bucket, subir un fichero y abrir su contenido con un clic (T14 ~03:46:24-03:48:32).
- Si la extensión aparece en rojo, lo normal es que hayan **caducado las credenciales** (duran entre 8 y 24 h): se reintenta, se abre el navegador y se vuelve a iniciar sesión (T14 ~03:45:12-03:45:47).
- Desde la extensión llegó a editar un fichero en S3 "en caliente" y comprobó con boto3 que el tamaño había cambiado; avisó de que no es lo recomendable, aunque alguna vez sea útil (T14 ~04:07:39-04:08:31).
- Intentó borrar una "carpeta" desde la consola y no le dejó, aunque a un alumno sí (T14 ~04:04:17-04:05:33) *(dudoso)*.

### 5.2 CLI

```bash
aws --version                                     # comprobar que está instalada (T14 ~03:50:08)
aws s3 mb s3://miax-<alias>-datos --region eu-west-3   # crear ("make bucket")
aws s3 ls                                         # tus buckets
aws s3 ls s3://miax-<alias>-datos/market/         # objetos con un prefijo
aws s3 cp hola.txt s3://miax-<alias>-datos/       # local -> bucket (y al revés, o entre buckets)
aws s3 cp s3://bucket-a/market/ s3://bucket-b/ --recursive
aws s3 mv fichero.txt s3://miax-<alias>-datos/    # copia y borra el origen
aws s3 sync ./datos s3://miax-<alias>-datos/datos/   # solo lo que ha cambiado
aws s3 rm s3://miax-<alias>-datos/datos/ --recursive
aws s3 rb s3://miax-<alias>-datos --force         # vacía y borra el bucket
```

(L11 «CLI: buckets y listados», «CLI: copiar y mover», «CLI: borrar y `--recursive`».)

Lo que añadió en clase (T14 ~03:49:03-04:04:17):
- Si no indicas región al crear, el bucket va a la región por defecto (**us-east-1**) (T14 ~03:49:22-03:49:39).
- Los comandos imitan a los de Linux (`ls`, `cp`, `mv`, `rm`), igual que `scp` entre local y servidor (T14 ~03:52:39).
- **Cuidado con `--force`**: borra todo lo que haya dentro sin preguntar y después el bucket (T14 ~03:53:30-03:54:03).
- `mv` sirve para subir lo que no quieres conservar en local o para reorganizar datos entre buckets (T14 ~03:57:28-03:58:02).
- `sync` le parece "muy interesante": lo probó creando y modificando ficheros y solo subía lo nuevo o cambiado. Propuso sincronizar una carpeta al encender y apagar la máquina como "sistema de ficheros" mucho más barato que un servidor de ficheros (T14 ~03:58:06-04:02:29).
- `--recursive` aplica el comando a todos los objetos con ese prefijo (T14 ~04:03:47-04:04:15; L11 «CLI: borrar y `--recursive`»).

### 5.3 boto3

```python
import boto3

s3 = boto3.client("s3", region_name="eu-west-3")
s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
s3.upload_file("market_data.txt", bucket, "market_data.txt")
s3.download_file(bucket, "market_data.txt", "copia.txt")
for objeto in s3.list_objects_v2(Bucket=bucket).get("Contents", []):
    print(objeto["Key"], objeto["Size"])
```

(L11 «Desde Python: boto3»; EJ s3/boto3, celdas 1-8; en clase, T14 ~04:05:42-04:08:35.)

- `LocationConstraint` es obligatorio salvo en `us-east-1`; `list_objects_v2` devuelve **como mucho 1.000 claves**, y para más hay que paginar (L11 «Desde Python: boto3»).
- `upload_fileobj` sube un fichero ya abierto en binario (L11 «boto3: ficheros abiertos y recursos»).
- Dos interfaces: el **cliente** (`boto3.client`), que refleja la API una a una, y el **recurso** (`boto3.resource`), más orientado a objetos; "son equivalentes" (T14 ~04:08:41-04:09:23).

**Nota.** CAMBIOS aclara que `boto3.resource("s3").download_file` no existe; lo que sí existe es `s3r.Bucket(bucket).download_file(...)`, que es lo que pone la diapositiva. AWS ha dejado de añadir funciones nuevas a la interfaz de recursos, así que para código nuevo conviene el cliente. El paginador:

```python
paginas = s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="kid/")
claves = [o["Key"] for p in paginas for o in p.get("Contents", [])]
```

### 5.4 pandas

```python
import pandas as pd                     # pip install pandas s3fs
df = pd.read_csv(f"s3://{bucket}/market_data.txt", sep=";")
df.loc[:, ["FECHA", "HORA", "VALOR", "PRECIO", "VOLUMEN"]].to_csv(f"s3://{bucket}/market_data_mod.csv", index=False)
```

(L11 «Desde pandas»; EJ s3/boto3, celdas 9-11.)

- pandas lee y escribe rutas `s3://` con la librería **s3fs**; las credenciales se buscan igual que en boto3 (L11 «Desde pandas»). Si hace falta pasar credenciales temporales concretas, se usa `storage_options` leyéndolas de variables de entorno (L11 «pandas con credenciales explícitas»).
- En clase falló varias veces antes de funcionar: primero pedía `fsspec`, luego `s3fs`, y al final el nombre del fichero no coincidía con el subido (T14 ~04:13:40-04:17:52). Moraleja: "no hay que conectarse a nada", pero sí instalar las librerías que pide.

---

## 6. Credenciales y acceso desde EC2

**Idea.** boto3, pandas y la CLI buscan las credenciales solas; en AWS la forma correcta es un **rol de IAM** y en tu ordenador `aws login`. Nunca claves en el código (L11 «Credenciales en Python», «Claves en el código: no»).

### 6.1 Orden de búsqueda

1. Parámetros explícitos en el código.
2. Variables de entorno (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`).
3. `~/.aws/config` y `~/.aws/credentials` (los crean `aws login` o `aws configure`).
4. El rol de IAM de la instancia EC2, la Lambda o el contenedor.

"Si la CLI funciona en tu máquina, boto3 y pandas también" (L11 «Credenciales en Python»). En clase: tras `aws login`, cualquier programa que lea esas credenciales (boto3, pandas) puede usarlas (T14 ~04:10:26-04:11:08).

### 6.2 Claves en el código: nunca

- Las claves en el código acaban en Git, en capturas y en logs (L11 «Claves en el código: no»).
- El profesor lo repitió con énfasis: hay **bots que recorren GitHub buscando credenciales** porque "es dinero gratis" (T14 ~04:11:08-04:11:37).
- El enunciado lo convierte en regla: "Sin credenciales en el repositorio" (ENUNCIADO §5; DEC D-0.4).

### 6.3 Dar acceso a S3 a una instancia

Pasos (L11 «Dar acceso a S3 a EC2»; en clase, T14 ~04:34:10-04:37:09):

1. IAM, **Roles**, *Create role*, servicio **EC2**.
2. Política `AmazonS3FullAccess` (o `AmazonS3ReadOnlyAccess` si solo lee, L11b «Preparar la instancia»); nombre `miax-ec2-s3`.
3. En la instancia: **Actions**, **Security**, **Modify IAM role**, elegir el rol.
4. Comprobar con `aws s3 ls`.

Lo que se vio en directo:
- Antes del rol, `aws sts get-caller-identity` y `aws s3 ls` decían que **no había credenciales** en la instancia (T14 ~04:19:10-04:19:34, ~04:34:22-04:34:42). Iniciar sesión con tu usuario dentro de la máquina funciona, pero deja tus credenciales en ella; el rol es la opción limpia (T14 ~04:19:35-04:20:22, ~04:34:46).
- Con el rol asignado, `aws s3 ls` devolvía los buckets sin configurar nada más (T14 ~04:36:33-04:37:09).
- **Error típico**: el script con pandas daba un error de permisos hasta que se configuró la **región**; sin ella intentaba ir a `us-east-1`, donde no había nada (T14 ~04:39:03-04:41:19). En el servicio de Streamlit la lección lo evita con `AWS_DEFAULT_REGION` (§7.6).
- La instancia se saturó (disco lleno por VS Code Server y extensiones) y hubo que crear otra; consejo general: reiniciar antes de nada, y no quedarse corto de disco (T14 ~04:25:17-04:27:23).

**Nota.** `AmazonS3FullAccess` sirve para clase, pero da permiso sobre **todos** los buckets de la cuenta. En la práctica, el rol de cada pieza debería limitarse a su bucket y a las acciones que necesita (por ejemplo `s3:PutObject` y `s3:GetObject` sobre `arn:aws:s3:::<bucket>/kid/*`), y Terraform permite escribirlo así desde el principio.

---

## 7. Aplicaciones de datos con Streamlit

**Idea.** Streamlit convierte un script de Python en una aplicación web (tablas, gráficos, filtros, formularios) sin HTML ni JavaScript. Su modelo es muy simple: **cada vez que el usuario toca algo, se vuelve a ejecutar el script entero, de arriba abajo** (L11b «Qué es Streamlit»).

Esta lección es nueva en la web del curso: no viene de la presentación original (CAMBIOS, «Caso de uso de Streamlit»). En T13 el profesor anunció que, si daba tiempo, después de EC2 y S3 vería "Streamlit o algo de contenedores" (T13 ~04:46:31), pero en T14 no llegó a explicarlo; solo hubo una conversación de pasillo al final sobre hacer páginas web y desplegarlas en un contenedor o en EC2 abriendo los puertos (T14 ~04:47:09-04:48:07) *(dudoso)*. Todo lo de esta sección sale de L11b y de los ejemplos.

### 7.1 Instalar y arrancar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install streamlit pandas boto3
streamlit hello                                     # demo oficial
streamlit run 01_hola.py                            # http://localhost:8501
```

Necesita Python 3.11 o superior. Al guardar cambios se pulsa **Rerun** (o **Always rerun**); se para con Ctrl+C (L11b «Instalar y arrancar»).

### 7.2 Mostrar texto, datos y gráficos

| Función | Muestra |
|---|---|
| `st.title`, `st.header`, `st.subheader` | Títulos |
| `st.write` | Casi cualquier cosa: texto, números, diccionarios, DataFrames |
| `st.markdown`, `st.caption`, `st.code` | Texto con formato, notas y código |
| `st.metric` | Un número destacado, con variación opcional (`delta`) |
| `st.dataframe` | Tabla que se ordena, busca y amplía |
| `st.line_chart`, `st.bar_chart`, `st.area_chart`, `st.scatter_chart` | Gráficos rápidos desde un DataFrame |
| `st.plotly_chart`, `st.pyplot` | Figuras de Plotly o Matplotlib |

(L11b «Tu primera aplicación», «Datos, métricas y gráficos»; EJ streamlit/01_hola.py, 02_datos.py.)

### 7.3 Widgets

Cada widget **devuelve el valor** elegido; al cambiarlo, el script se reejecuta con el valor nuevo (L11b «Widgets: la parte interactiva»).

| Widget | Devuelve |
|---|---|
| `st.selectbox`, `st.radio` | Una opción |
| `st.multiselect` | Una lista |
| `st.slider` | Un valor, o una tupla si das un rango |
| `st.number_input`, `st.text_input`, `st.date_input` | Número, texto o fecha |
| `st.checkbox`, `st.toggle` | `True` o `False` |
| `st.button` | `True` **solo en la ejecución del clic** |

```python
valor = st.selectbox("Valor", sorted(datos["VALOR"].unique()))
desde, hasta = st.slider("Horas", hora_min, hora_max, (hora_min, hora_max))
seleccion = datos[(datos["VALOR"] == valor) & datos["TIME"].dt.hour.between(desde, hasta)]
st.line_chart(seleccion, x="TIME", y="PRECIO")
```

(EJ streamlit/03_filtros.py.) La lección da un valor de control: con `SAN`, de 9 a 17 h y sin más filtros, salen **9.585** operaciones (L11b «Ejercicio: filtros»).

### 7.4 Layout y caché

- `st.set_page_config(page_title=..., layout="wide")` va **antes que cualquier otro `st.*`** (EJ streamlit/04_layout.py).
- `st.sidebar` (barra lateral para los controles), `st.columns` (métricas en fila), `st.tabs` (pestañas, solo se ve una), `st.expander` (desplegable cerrado por defecto) (L11b «Organizar la página»).
- **`@st.cache_data`**: como el script se ejecuta en cada clic, sin caché leería el CSV cada vez. El decorador guarda el resultado mientras los argumentos no cambien; con `ttl=300` caduca a los 5 minutos (L11b «Organizar la página»). El ejercicio propone quitarlo, poner un `print` dentro y contar en la terminal cuántas lecturas hace al mover un filtro (L11b «Ejercicio: tu panel»).

**Nota.** `st.cache_data` guarda una copia de los **datos** devueltos (DataFrames, listas, JSON) y la clave de la caché incluye los argumentos, por eso `cargar_datos(clave)` recibe la clave como parámetro. Para objetos que no se deben copiar, como un cliente de boto3 o una sesión HTTP, Streamlit tiene `st.cache_resource`.

### 7.5 Ficheros y estado

- `st.file_uploader` devuelve un objeto que pandas lee como un fichero local; `st.stop()` corta la ejecución hasta que haya fichero; `st.download_button` ofrece un resultado para descargar (L11b «Ficheros y estado»; EJ streamlit/05_ficheros.py).
- Las variables normales se pierden en cada ejecución; para conservar algo entre clics está **`st.session_state`** (un contador, una lista de favoritos) (L11b «Ficheros y estado», «Ejercicio: subir y descargar»).

### 7.6 Panel sobre S3 y despliegue en EC2

El panel definitivo lee el CSV del bucket, y el nombre del bucket llega por **variable de entorno** (L11b «Leer los datos de S3»; EJ streamlit/app.py):

```python
BUCKET = os.environ["BUCKET"]

@st.cache_data(ttl=300)                       # vuelve a leer S3 como mucho cada 5 minutos
def cargar_datos(clave: str) -> pd.DataFrame:
    objeto = boto3.client("s3").get_object(Bucket=BUCKET, Key=clave)
    return pd.read_csv(objeto["Body"], parse_dates=["TIME"])
```

- En local basta la sesión de `aws login` y `BUCKET=... streamlit run app.py` (en PowerShell, `$env:BUCKET="..."`). Valores de control: `SAN` con 9.585 operaciones y precio medio **5,3936** (L11b «Ejercicio: panel con datos de S3»).
- En EC2 el flujo es navegador, puerto 8501 en el grupo de seguridad, Streamlit, rol de IAM sin claves y S3 (L11b «Publicarlo en EC2»).
- Preparar la instancia: regla **Custom TCP 8501** con origen **My IP** y el rol de S3. Aviso: **Streamlit no pide contraseña**; quien llegue al puerto ve el panel y los datos (L11b «Preparar la instancia»).
- Amazon Linux 2023 trae Python 3.9, así que se instala 3.13 con **uv**; se arranca con `--server.address 0.0.0.0` (aceptar conexiones de fuera) y `--server.headless true` (no abrir navegador ni pedir correo) (L11b «Instalar y arrancar en la instancia»).
- Para que siga vivo al cerrar SSH y arranque solo tras un reinicio, se crea un **servicio de systemd** (L11b «Que siga funcionando»; EJ streamlit/miax-streamlit.service):

```ini
[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/streamlit
Environment=BUCKET=miax-<alias>-datos
Environment=AWS_DEFAULT_REGION=eu-west-3
ExecStart=/home/ec2-user/streamlit/.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
Restart=always
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now miax-streamlit
systemctl status miax-streamlit         # active (running)
journalctl -u miax-streamlit -f         # logs
sudo systemctl restart miax-streamlit   # tras desplegar un cambio
```

- Limpieza: `systemctl disable --now`, borrar la regla del 8501 y detener o terminar la instancia (L11b «Limpieza»).

---

## 8. Errores y avisos que conviene recordar

| Situación | Qué pasa | Fuente |
|---|---|---|
| Nombre de bucket ya usado | No deja crearlo: el nombre es global; usar nombres largos y propios | T14 ~03:40:19-03:40:43; L11 «Buckets» |
| Crear sin `--region` / sin `LocationConstraint` | Va a `us-east-1`, o falla la creación fuera de esa región | T14 ~03:49:22; L11 «Desde Python: boto3» |
| Script en EC2 sin región | Error de acceso aunque el rol sea correcto | T14 ~04:39:03-04:41:19 |
| `rb --force` / `rm --recursive` | Borran todo sin preguntar | T14 ~03:53:30-03:54:03 |
| pandas sin `s3fs` | Pide instalar `fsspec` y `s3fs` | T14 ~04:14:34-04:17:21 |
| Credenciales caducadas en VS Code | La extensión sale en rojo; volver a iniciar sesión | T14 ~03:45:12 |
| Claves en el código | Bots en GitHub las encuentran | T14 ~04:11:08-04:11:37 |
| Más de 1.000 objetos | `list_objects_v2` corta; paginar | L11 «Desde Python: boto3» |
| Streamlit con el puerto abierto a todos | Cualquiera ve los datos | L11b «Preparar la instancia» |
| Recursos olvidados | Instancias, *snapshots* y volúmenes siguen cobrando; el panel de EC2 resume lo que hay | T14 ~04:43:53-04:45:02; L11 «Ejercicio: pandas desde EC2» |

---

## 9. Para la práctica

**Idea.** El enunciado pide guardar los PDF de los KID en S3 "con una organización y unos metadatos coherentes", registrar de dónde viene cada uno y cuándo se descargó, evitar duplicados y no exponer datos ni documentos salvo por la API y la aplicación (ENUNCIADO §1, §4, §5). Todo lo de esta sección es **Nota** salvo donde se cita.

### 9.1 Organización de las claves

**Nota.** Una organización coherente con D-1.2 (identidad por SHA-256 del PDF):

```text
s3://<bucket-datos>/
  kid/bestinver/<sha256>.pdf
  kid/azvalor/<sha256>.pdf
  kid/cobas/<sha256>.pdf
  manifiestos/<fecha-ejecucion>.jsonl      # una línea por documento capturado
```

- **Prefijo por gestora**: permite listar, contar o reprocesar una fuente con `Prefix="kid/azvalor/"` o `aws s3 ls`, y limitar permisos por prefijo (§2.2).
- **Clave derivada del SHA-256**: el mismo PDF da siempre la misma clave, así que subirlo dos veces no duplica nada; un KID nuevo del mismo ISIN tiene otro hash y se conserva como otro documento (DEC D-1.2). Antes de subir se puede comprobar si existe con `head_object`, o usar una escritura condicional (`put_object(..., IfNoneMatch="*")`, disponible en versiones recientes de boto3) para que S3 rechace la segunda.
- **Sin nombres originales en la clave**: el nombre del PDF de algunas gestoras cambia con la fecha (ENUNCIADO §3, Azvalor), y puede llevar espacios o tildes; mejor guardarlo como dato.

### 9.2 Metadatos de origen

**Nota.** Lo mínimo que pide el enunciado (origen y fecha de descarga) cabe en los metadatos del objeto (§3.5) y además en el manifiesto y en la base de datos:

| Metadato (`x-amz-meta-`) | Ejemplo |
|---|---|
| `source-page` | URL de la ficha del fondo |
| `source-url` | URL del PDF |
| `downloaded-at` | `2026-11-19T10:00:00Z` (UTC, ISO 8601) |
| `gestora` | `cobas` |
| `sha256` | el hash, para verificar |

Más `ContentType="application/pdf"`. Los metadatos van pegados al fichero (si alguien copia el objeto, viajan con él), pero no se pueden consultar en bloque: para buscar o filtrar, la fuente es el manifiesto o PostgreSQL. La fecha en UTC evita el problema de zonas horarias que el profesor contó con los cron (T13 ~04:44:52-04:45:13).

### 9.3 Bucket privado

- Regla del enunciado: los datos y documentos **no se exponen públicamente** salvo a través de la API y la aplicación (ENUNCIADO §5).
- **Nota.** Por tanto: *Block all public access* activado (§3.2), ninguna URL pública de objeto, acceso solo mediante roles (el del scraper y la extracción escriben y leen; la API, si sirve PDFs, lee). Si la aplicación tuviera que ofrecer el PDF original, lo correcto sería una URL prefirmada de corta duración generada por la API, no abrir el bucket.
- **Nota.** Versionado: no hace falta para los KID (la clave por hash ya es inmutable), pero sí en el bucket del **estado de Terraform**, que el enunciado también pone en S3 (ENUNCIADO §6; DEC D-5.1). Región europea, por coherencia con lo dicho sobre ubicación de datos (§2.4; DEC D-0.2).
- **Nota.** Si se hace la ampliación "S3 → Lambda" (ENUNCIADO §4), los resultados no deben escribirse bajo el mismo prefijo que dispara la función, o se crea un bucle; CAMBIOS lo recoge como aviso añadido a la lección de disparadores, junto con decodificar la clave con `unquote_plus`.

### 9.4 Streamlit como dashboard

- En la arquitectura de referencia la visualización es **Streamlit en Amazon ECS Express Mode** (ENUNCIADO §6), no en EC2 como en la lección. App Runner ya no admite clientes nuevos y ECS Express es su sustituto en el curso (CAMBIOS).
- La aplicación **lee de la API**, no de S3 ni de la base de datos (DEC D-4.1): una sola puerta a los datos, coherente con la regla 5.
- **Nota.** Lo de L11b se traslada casi tal cual, cambiando la fuente de datos:

```python
API_URL = os.environ["API_URL"]               # como BUCKET en app.py: configuración por entorno

@st.cache_data(ttl=300)
def cargar_fondos() -> pd.DataFrame:
    respuesta = requests.get(f"{API_URL}/fondos", timeout=10)
    respuesta.raise_for_status()
    return pd.DataFrame(respuesta.json())
```

  Los widgets (§7.3) filtran por gestora o SRI, `st.metric` resume (número de fondos, SRI medio, gastos corrientes medios), `st.dataframe` muestra la tabla y `st.tabs` separa vistas. El `ttl` hace que un KID recién cargado aparezca en minutos, igual que el ejercicio de S3 de la lección (L11b «Ejercicio: panel en EC2», punto 6).
- **Nota.** De la lección de EC2 se mantienen en el contenedor `--server.address 0.0.0.0`, `--server.headless true` y el puerto 8501; systemd ya no hace falta porque ECS mantiene vivo el proceso. El aviso de que Streamlit no pide contraseña sigue valiendo: la URL de ECS Express es pública. Y ECS Express comprueba `/` por defecto (CAMBIOS), que Streamlit sirve sin cambios.
- Coste: ECS Express cobra por hora mientras está desplegado; conviene levantarlo para las pruebas y la exposición (DEC D-5.2).

---

## 10. Preguntas de repaso

1. **¿Qué identifica de forma única un objeto en S3?** El bucket, la clave y, si hay versionado, la versión. Las "carpetas" son solo prefijos de la clave (§2.1-§2.2).
2. **¿Por qué falla a veces la creación de un bucket con un nombre corto?** Porque el nombre es único en todo AWS y probablemente ya lo usa otra cuenta; se recomienda un nombre largo y propio (§2.3).
3. **¿Qué protege el cifrado por defecto y qué no?** Protege los datos en disco; no impide que quien tenga permisos lea el objeto. El acceso se controla con IAM, la política del bucket y el bloqueo público (§3.2-§3.3).
4. **¿Qué clase de almacenamiento elegirías para los KID y para unos registros que hay que guardar siete años sin leerlos?** Standard para los KID, que se leen a menudo y pesan poco; Glacier (Flexible o Deep Archive) para el archivo por cumplimiento, sabiendo que recuperar cuesta y tarda (§4.1).
5. **¿Cómo da acceso a S3 una instancia EC2 sin claves, y qué error típico apareció en clase?** Con un rol de IAM asignado a la instancia; aun con el rol, el script fallaba hasta configurar la región (§6.3).
6. **¿Por qué hace falta `@st.cache_data` en Streamlit?** Porque el script se reejecuta entero en cada interacción; sin caché descargaría los datos en cada clic. Con `ttl` se refrescan cada cierto tiempo (§7.4).
7. **¿Qué ventaja tiene derivar la clave de S3 del SHA-256 del PDF?** Que el mismo documento da siempre la misma clave, así que reprocesar no duplica y un KID nuevo nunca pisa al anterior (§9.1).
8. **¿Por qué el dashboard de la práctica no lee directamente de S3, como `app.py` de la lección?** Porque el enunciado solo permite exponer datos a través de la API y la aplicación, y la decisión del repositorio es dejar la API como única puerta (§9.4).
