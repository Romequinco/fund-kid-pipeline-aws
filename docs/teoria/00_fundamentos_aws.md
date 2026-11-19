# Fundamentos de AWS: nube, cuenta y costes, IAM, CLI y redes

> **Fuentes:**
> - **L00-L04** = lecciones de la web del curso, `docs/raw/miax-cloud-main/content/`: `00-como-usar.md` (L00), `01-intro.md` (L01), `02-cuenta-costes.md` (L02), `03-iam-cli.md` (L03) y `04-vpc.md` (L04), leídas completas. **L05** = `05-ec2.md`, solo las diapositivas «Acceso seguro» y «Direcciones IP» (grupos de seguridad e IP públicas).
> - **CAMBIOS** = `docs/raw/miax-cloud-main/CAMBIOS.md` (qué cambió respecto al material antiguo del curso).
> - **T13** = `docs/raw/transcripciones/T13.txt`, transcripción automática de la clase del 13/11/2026. Tramo **~00:00-02:33** (presentación, web del curso, introducción, cuenta y costes, IAM, CLI, boto3, descanso y VPC). Desde ~02:33 empieza EC2, que no se trata aquí.
> - **T14** = `docs/raw/transcripciones/T14.txt`, clase del 14/11/2026, tramo **~00:00-00:05** (repaso de lo visto el día 13).
> - **ENUNCIADO** = `docs/raw/transcripciones/enunciado.txt` (práctica B7, para la §8).
>
> **Convenciones:** "(T13 ~01:12)" = hora aproximada en la transcripción; todo lo que viene de ellas es **paráfrasis** de un texto automático muy ruidoso ("C 2" o "F 2" = EC2, "S Tres" = S3, "elías" = IaaS, "badget" = Budgets, "Internet Quedway" = Internet Gateway), y lo que no se entiende bien va marcado *(dudoso)*. "(L03 «Conceptos»)" = diapositiva de la lección, citada por su título. **Nota:** = contenido propio (aclaraciones, correcciones, conexiones con la práctica), no del material de clase.
>
> Escrito el 19/11/2026.

---

## 1. Antes de empezar: la web del curso y las herramientas

**Idea.** El curso se sigue con dos pestañas: la web del curso, que explica y genera los comandos, y la consola de AWS, donde se hace el trabajo (L00 «Ir y volver de AWS»; T13 ~00:05:42).

### 1.1 Cómo se usa la web

- La web es una página de GitHub Pages asociada a un repositorio (T13 ~00:04:15). Tiene dos vistas: **diapositivas** (para seguir la clase) y **guía** (tecla G, para repasar desplazándose por toda la lección) (L00 «Dos formas de verla»; T13 ~00:04:50).
- Los botones naranjas abren directamente la pantalla de la consola de AWS de la que se habla (L00 «Ir y volver de AWS»; T13 ~00:05:24). Con una sola pantalla, la tecla P abre una ventana lateral estrecha para tenerla junto a VS Code o a la consola (L00; T13 ~00:06:17).
- En la configuración se guardan **región**, **ID de cuenta** y un **alias**. Con ellos los comandos salen ya rellenos; el alias hace únicos los nombres de recursos (los nombres de bucket deben ser únicos en todo AWS). Los datos no salen del navegador (L00 «Configura tus datos»; T13 ~00:06:44-00:07:55, ~01:29:48).
- Tipos de bloque (L00 «Qué significa cada bloque»; T13 ~00:08:48-00:09:43):

| Bloque | Color en la web | Qué es |
|---|---|---|
| Demo | Naranja | El profesor hace los pasos en la consola |
| Ejercicio | Verde | Lo hace el alumno; en clase se dejan unos 5-10 min |
| Limpieza | Marrón | Borrar lo creado para que no siga cobrando |

- **Aviso recurrente.** Las pantallas de AWS cambian a menudo. Si un botón no coincide, hay que buscar la opción por su nombre (L01 «Documentación»). El profesor insiste en que dirá "juraría" o "creo" a menudo porque los proveedores cambian nombres e interfaces casi cada semana, y que Google cambia aún más (T13 ~00:08:11-00:08:46, ~00:14:58). Recomienda tener la consola **en inglés**: los nombres son más estables que en la traducción (T13 ~00:37:30, ~00:59:48).

### 1.2 Qué hay que instalar

| Herramienta | Para qué | Comentario de clase |
|---|---|---|
| VS Code (+ Remote - SSH) | Editor; conectar a EC2 | Lo usa la mayoría (L00 «Qué necesitas instalar») |
| AWS CLI v2 (≥ 2.32) | Trabajar con AWS desde terminal | Se instala con el comando oficial para cada sistema, en Windows desde PowerShell; `aws --version` comprueba la versión (T13 ~00:09:53-00:11:14) |
| Python 3.13 o 3.14 y Git | Código y boto3 | En Windows, Git Bash da una terminal tipo Linux (T13 ~00:11:20-00:11:59) |
| Docker Desktop | Contenedores (semana siguiente) | En Windows usa WSL, un Linux (Ubuntu) dentro de Windows (T13 ~00:12:15-00:13:01) |
| Terraform | Módulo final | Se explicará al llegar a ese módulo (T13 ~00:13:23) |

---

## 2. AWS y la nube

### 2.1 Historia y mercado

**Idea.** AWS nace de un problema de Amazon: dimensionar servidores para los picos de su comercio electrónico. Primero la capacidad sobrante se usó dentro de la empresa y después se alquiló al público (T13 ~00:15:29-00:16:44).

| Año | Hito (L01 «AWS en contexto») | Lo que añadió el profesor |
|---|---|---|
| 2002 | Primeros servicios para desarrolladores, uso interno | Amazon era básicamente una tienda en línea, sobre todo de libros. En Black Friday o rebajas la web se colapsaba, así que tenía servidores de sobra que solo hacían falta unos días al año (T13 ~00:15:29-00:16:11) |
| 2004 | Lanzamiento público | Empiezan a alquilar servidores y almacenamiento a terceros (T13 ~00:16:33) |
| 2006 | S3 y EC2 | S3 son "carpetas" en la nube, rápidas y muy fiables. Por los muchos nueves de durabilidad, perder un dato es muy improbable, pero no imposible (T13 ~00:16:53-00:17:35) |
| 2010 | Todo amazon.com corre en AWS | Se suman bases de datos, colas, etc. (T13 ~00:17:38) |
| Hoy | Más de 200 servicios | Cuando sale un proyecto *open source* (p. ej. Kafka), los proveedores lo integran y lo venden gestionado: no tienes que montarlo tú (T13 ~00:17:58-00:18:18) |

- **Ingresos y cuota.** Unos 46.000 M$ solo en el tercer trimestre de 2026. AWS lidera con cerca del 26 %, por delante de Microsoft (19 %) y Google (16 %), según Synergy Research (L01 «AWS en contexto»; T13 ~00:18:54-00:19:46). El profesor añadió que la cifra de ingresos podría estar inflada por los resultados de su participación en una empresa de IA, sin recordar si sobre el trimestre o el año *(dudoso)* (T13 ~00:19:03-00:19:11).
- **Tendencia.** AWS va perdiendo algo de cuota porque Azure y Google lo hacen bien y aparecen *neoclouds* centrados en GPU, que hoy es lo que más se demanda para IA (L01; T13 ~00:19:18-00:20:02).
- **Más de 200 servicios.** La "tabla periódica" de servicios da una idea del tamaño, aunque está algo desactualizada (L01 «Más de 200 servicios»; T13 ~00:20:20-00:21:14).
- **Nombres que bailan.** Un alumno que usa AWS en el trabajo para análisis de datos citó S3 y SageMaker. El profesor describió SageMaker como "la parte de IA" de Amazon y dijo que antes era Bedrock *(dudoso)* (T13 ~00:14:15-00:14:52).

**Nota:** SageMaker y Bedrock son servicios distintos. SageMaker sirve para entrenar y desplegar modelos propios. **Bedrock** da acceso por API a modelos fundacionales de terceros y de Amazon, y es el que usa la práctica (§8). AWS ha reorganizado la marca SageMaker en los últimos años, de ahí la confusión.

### 2.2 Infraestructura global: regiones y zonas

**Idea.** AWS se organiza en **regiones** (áreas geográficas aisladas entre sí), y cada región en varias **zonas de disponibilidad** (AZ), cada una con uno o más centros de datos. Son 39 regiones y 124 zonas, y la cifra sigue creciendo (L01 «Infraestructura global»).

| Nivel | Qué es | Ejemplo |
|---|---|---|
| Macroárea (solo en el mapa) | Agrupación geográfica | Europa, Norteamérica, Oriente Medio... (T13 ~00:23:09-00:23:30) |
| **Región** | Área independiente y aislada del resto | `eu-west-3` (París), `eu-north-1` (Estocolmo), `eu-south-2` (España) |
| **Zona de disponibilidad** | Ubicación aislada dentro de la región, unida a las demás por red redundante de baja latencia | Zonas A, B y C de París |
| Centro de datos | Edificio físico | Uno o más por zona |

- El profesor lo explica como cajas dentro de cajas: Europa → París → zonas → centros de datos (T13 ~00:23:30-00:24:16).
- **Para qué sirven las zonas.** Si se quema un centro de datos o falla justo tu servidor, una aplicación crítica (hospitales, datos de bolsa) tiene que estar replicada en más de una zona. Sin réplica, perder el centro de datos es como tirar un vaso de agua sobre tu portátil (T13 ~00:24:16-00:24:51). Al lanzar un recurso puedes elegir la zona o dejar que la elija AWS (L01).
- **Dónde está físicamente cada zona.** AWS no lo dice: cada zona tiene su red y su suministro eléctrico, pero no sabes si están en el mismo complejo o en ciudades distintas. El día siguiente el profesor lo presentó también como algo de seguridad por oscuridad (T13 ~00:25:05-00:25:49; T14 ~00:02:12-00:02:46). Mencionó además una supuesta alianza de AWS y Azure para compartir centros de datos en Europa *(dudoso)* (T13 ~00:25:15).
- **Anécdotas de fiabilidad** (T13 ~00:22:07-00:22:51, ~00:24:16): un centro de datos de Oriente Medio dañado por un ataque, y una caída en EE. UU. Este que tumbó "medio Internet" por un fallo en un balanceador. Lección: la nube son máquinas de otro, y también fallan.
- **Cómo elegir región** (L01 «La región importa»): latencia, coste, servicios disponibles y requisitos legales. En clase (T13 ~00:26:17-00:27:05; T14 ~00:02:02): hay regiones más caras que otras, y el precio sigue en buena medida al de la electricidad. Irse a la región más barata y lejana se paga en latencia ("como jugar con lag"). La normativa también pesa.
- La consola **solo muestra los recursos de la región seleccionada**, y los datos no se replican a otra región salvo que lo configures (L01 «La región importa»).
- **Región del curso:** `eu-west-3` (París), porque es la que tiene más servicios. La de España (`eu-south-2`) no tiene todos (p. ej., hay que comprobar Textract), y hay un gran centro previsto en Aragón (L01; T13 ~00:07:58-00:08:11). Algunos alumnos con plan gratuito no podían seleccionar París; el profesor habilitó **Estocolmo** (`eu-north-1`) como alternativa en la web (T13 ~01:04:37-01:06:15; T14 ~00:00:27).
- **Otras ubicaciones** (L01): *Local Zones* (cerca de grandes ciudades, para baja latencia; el profesor pone el ejemplo de servir vídeo en streaming), *Outposts* (hardware de AWS en tu centro de datos) y *Wavelength* (dentro de redes 5G) (T13 ~00:28:05-00:28:32).
- **Servicios globales.** IAM y facturación no dependen de región: al entrar en ellos el selector muestra "Global". Es normal y no hay que cambiarlo (L03 «AWS Identity and Access Management»; T13 ~01:10:50-01:11:14, ~01:14:15-01:14:48).

**Nota:** el profesor dijo que la región más barata "debería ser us-east-3" *(dudoso)* (T13 ~00:26:17). Esa región no existe; probablemente quiso decir `us-east-1` (N. Virginia) o `us-east-2` (Ohio), que suelen estar entre las más baratas.

### 2.3 Modelos de servicio: on-site, IaaS, PaaS y SaaS

**Idea.** Los modelos se diferencian en **de qué te encargas tú** y de qué se encarga el proveedor. Cuanto más gestiona AWS, menos operas y menos control tienes (L01 «IaaS, PaaS y SaaS», «Los modelos en AWS»).

| Modelo | Analogía (L01; T13 ~00:30:33-00:31:00) | Tú gestionas | Ejemplo general (L01; T13) | Ejemplo en AWS (L01 «Los modelos en AWS») |
|---|---|---|---|---|
| **On-site** | Tu coche | Todo: compras el servidor, lo montas y cambias el disco roto (T13 ~00:33:33-00:33:54) | Servidores propios | — |
| **IaaS** | Coche de alquiler | Sistema, runtime, datos y aplicación. AWS pone hardware, virtualización, almacenamiento y red (T13 ~00:33:54-00:34:21) | Gran parte de los servidores de Netflix | EC2, EBS, VPC |
| **PaaS / serverless** | Taxi | Tu código y tus datos | El blog en Vercel; Snapchat nació sobre Google App Engine (L01) | Lambda, ECS Fargate, DynamoDB |
| **SaaS** | Autobús | Solo el uso | Gmail, Outlook, Drive, Spotify, Microsoft 365 | Athena desde la consola, Textract |

- **Ejemplo del blog** (L01 «Los tres modelos, uno a uno»; T13 ~00:32:26-00:33:13): IaaS es alquilar un servidor e instalar WordPress; PaaS, subir el código a Vercel; SaaS, abrir una cuenta en Substack. En la práctica se cambia de modelo según lo que necesites y el dinero disponible.
- **Una empresa puede estar en dos capas.** Netflix es SaaS para quien lo ve y cliente IaaS de AWS por detrás (T13 ~00:31:06-00:31:26).
- **PaaS en clase.** Le das al proveedor tu imagen de Docker o tu código y él lo ejecuta; te olvidas del sistema operativo, el runtime y el *middleware* (T13 ~00:29:19-00:30:09, ~00:34:23-00:34:51). Para el profesor, Docker es de lo más útil que se aprende en el curso (T13 ~00:29:51).
- **Orden del curso.** Se va de abajo arriba: primero lo IaaS (EC2), "la parte más durilla", y después lo gestionado (S3, Lambda...). A veces lo IaaS sale más barato (T13 ~00:34:59-00:35:34).
- **Serverless.** L01 agrupa "PaaS / Serverless": no gestionas servidores, sistema ni escalado; pagas por uso (Lambda, Fargate, DynamoDB). En T14 el profesor resume las funciones como desplegar "nuestro pequeño código sin preocuparnos mucho del resto" (T14 ~00:00:51).

**Nota (S3 en la clasificación).** L01 no clasifica S3. En el repaso del día 14 el profesor lo puso como ejemplo de PaaS (despliegas el bucket y subes y bajas datos) (T14 ~00:02:50-00:03:06). Se suele considerar un servicio de almacenamiento gestionado, sin servidores que administrar; lo importante es eso, no la etiqueta.

---

## 3. Cuenta de AWS y costes

### 3.1 Alta de la cuenta

**Idea.** Para darse de alta hacen falta un **correo** (que será el usuario raíz), un **teléfono** que reciba SMS y una **tarjeta**. AWS retiene 1 $ para verificarla y luego lo devuelve (L01 «Crea tu cuenta de AWS»; T13 ~00:27:32-00:27:41, ~00:44:51).

Pasos (L01 «Registro: datos de acceso», «Registro: facturación y activación»; T13 ~00:45:01-00:52:03):

1. Entrar por el enlace de **registro avanzado** de la web: otros botones llevan al registro nuevo de 2026, que fija la región y no crea usuario raíz (CAMBIOS, tabla).
2. Correo y nombre de cuenta (p. ej. `nombre-apellido-miax`) → código de verificación por correo. **Mirad en spam**: al profesor le llegó allí (T13 ~00:46:34).
3. Contraseña del raíz: al menos 8 caracteres combinando tres tipos (mayúsculas, minúsculas, números o símbolos).
4. Elegir plan (§3.3): en clase se pidió **Gratuito** (T13 ~00:51:13).
5. Datos de contacto, plan de soporte **Basic**, tarjeta y, si lo pide, SMS.

- La activación suele tardar minutos, pero puede llegar a 24 h: conviene hacerlo antes de clase (L01).
- **Si durante el alta te ofrece instalar un asistente (Kiro)**, recházalo por ahora: el curso va "lo más plano posible" (T13 ~00:47:23-00:47:49).
- La disposición de la consola puede cambiar según el tamaño de pantalla o las pruebas que haga Amazon con tu cuenta. Basta con llegar a algo parecido (T13 ~00:54:25). La consola puede abrirse en otra región (p. ej. Estocolmo); se cambia arriba a la derecha (L01 «Dentro de la consola»; T13 ~00:54:44).
- Los alumnos ya tenían una cuenta del máster con unos 25 $ de crédito mensual. Pueden usarla, y el profesor recomendó recuperar sus credenciales porque viene bien para el TFM (T13 ~00:05:42, ~00:45:49, ~01:05:38-01:06:15).

### 3.2 Proteger la cuenta: usuario raíz y MFA

**Idea.** El **usuario raíz** puede hacer cualquier cosa, incluido cerrar la cuenta, y no se le pueden limitar los permisos. Hay que activarle MFA nada más entrar, **no crearle claves de acceso** y usarlo solo para tareas de cuenta (L01 «Protege la cuenta»; L03 «AWS Identity and Access Management»).

```text
Credenciales de seguridad → Multi-factor authentication (MFA) → Assign MFA device
  → clave de acceso o aplicación de autenticación → escanear QR → dos códigos seguidos
```

(L01 «Protege la cuenta», «Dónde se asigna el MFA»; T13 ~00:58:52-01:01:16, ~01:32:18-01:32:47).

- Al iniciar sesión se elige **Root user** (correo + contraseña) o **IAM user** (ID de cuenta + usuario + contraseña) (T13 ~00:57:05-00:57:54).
- Aplicaciones de autenticación: las de Google o Microsoft, mejor que una cualquiera (T13 ~00:57:59-00:58:27).
- El profesor recomienda apuntar en papel el correo, la contraseña del raíz y el ID de cuenta, y "no volver a usar nunca más" el raíz (T13 ~01:01:21-01:01:55). Ver §4.4.
- En la app de autenticación aparecerán dos entradas, raíz y usuario IAM: fijaos en cuál usáis (T13 ~01:33:37-01:33:46).

### 3.3 Qué se paga y planes de la capa gratuita

**Idea.** El modelo por defecto es **pago por uso**. Se paga por cómputo, almacenamiento, transferencia de salida a Internet y cada IPv4 pública (L02 «Qué se paga en AWS»; T13 ~01:02:48-01:04:16).

| Concepto | Ejemplo (L02) | Comentario de clase |
|---|---|---|
| Cómputo | CPU y RAM de EC2, tiempo de Lambda, Fargate | — |
| Almacenamiento | GB en S3, volúmenes EBS (usados o reservados) | — |
| Transferencia de salida | Datos que salen de AWS a Internet | Lo que se mueve dentro de AWS (servidor → bucket) no se cobra (T13 ~01:03:08-01:03:28) |
| IP pública | 0,005 $/hora por IPv4 pública, también en uso | Una IP es la dirección numérica detrás de cada web (T13 ~01:03:33-01:03:57) |

**Nota:** la regla "dentro de AWS no se cobra" es una simplificación. Lo habitual es que no se cobre el tráfico dentro de la misma región entre servicios como EC2 y S3, pero la transferencia **entre regiones** y en algunos casos **entre zonas** sí tiene coste. Además, el profesor puso de ejemplo "8.8.8.8" como IP de google.com (T13 ~01:04:02-01:04:16): esa es la del DNS público de Google, no la de su web.

**Planes desde julio de 2025** (L02 «La capa gratuita», «Qué plan elegir para el curso»; CAMBIOS):

| | Plan gratuito | Plan de pago |
|---|---|---|
| Créditos | 100 $ al registrarse + hasta 100 $ por actividades | Igual |
| Duración | 6 meses o hasta agotar créditos | Créditos válidos 12 meses |
| Al agotarse | La cuenta se cierra, sin cargos | Se factura a precio normal |
| Servicios | Algunos no disponibles | Todos |

- Las cuentas anteriores a julio de 2025 siguen con el modelo antiguo de 12 meses (L02). Si se añade una cuenta con plan gratuito a AWS Organizations, pasa a ser de pago y pierde los créditos (L02).
- En clase: con el gratuito, lo peor que puede pasar es que se cierre la cuenta y haya que crear otra. En principio todo el curso se puede hacer sin pasar a pago (T13 ~00:50:26-00:51:13, ~01:06:23, ~01:17:29-01:17:48).
- Además existen ofertas **siempre gratuitas**: todos los servicios tienen una franja gratis (cierto número de peticiones a S3 o a Lambda al mes) a partir de la cual se cobra. Se ve en la página de capa gratuita (L02; T13 ~01:07:43-01:08:22).
- **Coste real del curso.** El profesor ensaya cada clase unos días antes. Lo de una semana le costó unos 12 céntimos, y si se limpia bien no se llega ni a 5-10 $ en todo el curso (T13 ~00:09:28, ~01:26:00-01:26:16).
- **Hábito de limpieza.** Al acabar cada clase hay que repasar lo creado en la región. Una instancia detenida no paga CPU, pero su disco EBS sí (L02 «Ejercicio»).

### 3.4 Otros modelos de precio y la calculadora

**Idea.** Antes de desplegar se puede estimar el coste con la **calculadora** (`calculator.aws`) (L01 «Documentación»; T13 ~00:35:46-00:37:24).

Modelos de precio comentados (T13 ~00:35:59-00:37:11, ~00:43:09-00:43:48):

| Modalidad | Qué es | Cuándo |
|---|---|---|
| Bajo demanda (*on demand*) | Pagas lo que usas | Personas y casi cualquier proyecto pequeño |
| Compromiso (*Savings Plans*, reservas) | Te comprometes 1-3 años a cambio de descuento y precio fijado | Cargas estables; protege de subidas, por ejemplo de la electricidad |
| Spot | Capacidad sobrante; AWS te la quita si alguien la necesita | Cargas que toleran interrupciones; en el ejemplo, cerca de la mitad de precio |
| Descuento por volumen | Negociado | Gastos muy grandes |

Demo de la calculadora (T13 ~00:37:24-00:43:53): consola en inglés, *Location* → Europa → París → EC2.
- **Tenencia** (*tenancy*): instancia compartida (un trozo de un servidor partido entre clientes) o host dedicado. Para datos públicos, como en el curso, basta la compartida. Con datos sensibles (salud, información privilegiada) la regulación puede pesar más (T13 ~00:38:17-00:39:13).
- Patrón de carga (constante o con picos diarios, semanales o mensuales), número de máquinas y tipo de instancia: la familia y el tamaño fijan vCPU y RAM. Ejemplo: T4g. Las familias G son de GPU (T13 ~00:41:41-00:43:03).
- **Datos sensibles y regiones** (pregunta de un alumno, T13 ~00:39:31-00:41:09): puedes elegir región y zona y hablar con el soporte de AWS. Aun así lo correcto es **anonimizar** los datos, porque la regulación española y europea de datos personales y médicos es muy dura. Para casos como hospitales puede tener sentido montar en local (*on premise*), más por normativa que por otra cosa.

### 3.5 Presupuesto y alertas: AWS Budgets

**Idea.** **AWS Budgets** avisa cuando el gasto real o previsto supera un límite, y es la opción recomendada. CloudWatch permite alarmas sobre cualquier métrica, incluida la facturación (L02 «Presupuesto y alertas»). El material antiguo usaba una alarma de CloudWatch y ahora se usa Budgets (CAMBIOS).

Ejercicio de clase (L02 «Ejercicio: presupuesto de costes»; T13 ~01:06:47-01:10:27, ~01:09:31):

```text
Budgets → Create budget → Use a template → Zero spend budget
  → nombre (p. ej. "cero-gasto") → correo(s) → Create budget
```

- Avisa en cuanto el gasto pasa de 0,01 $. Con una cuenta de empresa o del máster, con crédito mensual, tiene más sentido un umbral (1 $, 10 $) (T13 ~01:06:55-01:07:15).
- La primera vez llega un correo para confirmar la suscripción a la alerta. Puede ir a spam (T13 ~01:10:27).
- El profesor no encontró *Billing preferences* donde estaba días antes: los menús cambian. Budgets está en el menú izquierdo de *Billing and Cost Management* (T13 ~01:08:42-01:09:42).
- Activad también **Receive AWS Free Tier alerts** (Facturación → Billing preferences → Alert preferences) (L02 «Presupuesto y alertas»).

### 3.6 Ganar 100 $ más en créditos

**Idea.** AWS da **20 $ por cada una de cinco actividades**, y el curso las convierte en ejercicios (L02 «Consigue 100 $ más en créditos»; T13 ~00:06:01, ~00:44:24-00:44:45).

| Actividad | Lección del curso |
|---|---|
| Crear un presupuesto de costes | Cuenta y costes (esta) |
| Lanzar una instancia EC2 | EC2 |
| Crear una web con Lambda | Disparadores de Lambda |
| Crear una base de datos Aurora | DynamoDB |
| Usar un modelo en Bedrock | Textract |

- Están en la página de inicio de la consola → **Explore AWS** → filtro **Earn AWS credits** (L02 «Dónde están las actividades»; T13 ~01:11:27-01:12:59).
- Reglas (L02 «Reglas de las actividades»): conviene empezar cada una con **Iniciar actividad**, aunque hacerla por tu cuenta también puede contar (el presupuesto se completa así). Hay 6 meses desde el alta y los créditos caducan a los 12. Casi todas gastan algo, así que hay que borrar lo creado. El crédito tarda unos minutos.
- Con un usuario IAM el widget puede no aparecer: entrad como raíz solo para la actividad (L02). En las cuentas del máster el profesor dedujo que las actividades estaban desactivadas, pero el ejercicio sirve igual (T13 ~01:12:59-01:13:22).

---

## 4. IAM: identidades y permisos

### 4.1 Conceptos

**Idea.** IAM (*Identity and Access Management*) es un servicio **global** que decide **quién puede hacer qué** en la cuenta. Una **identidad** recibe **políticas** (documentos JSON) que le permiten actuar sobre **recursos** (L03 «AWS Identity and Access Management»; T13 ~01:14:15-01:15:22).

| Elemento | Qué es (L03 «Conceptos») | Ejemplo |
|---|---|---|
| **Usuario** | Persona o aplicación con credenciales propias | `alumno1`, `curso-miax` |
| **Grupo** | Colección de usuarios | `administradores` |
| **Rol** | Identidad **temporal** que asume un servicio o persona; no tiene claves fijas | Rol de ejecución de una Lambda |
| **Política** | Permisos en JSON | `AdministratorAccess` |

Una política por dentro (L03 «Una política por dentro»):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "*",
    "Resource": "*"
  }]
}
```

### 4.2 Cómo se asignan los permisos

**Idea.** A las **personas**, por grupos; a los **servicios**, por roles. Los permisos se suman y un `Deny` explícito gana siempre (L03 «Políticas en usuarios, grupos y roles»).

| Patrón (L03) | Esquema | Valoración |
|---|---|---|
| Personas por grupos | Política → Grupo → Usuario (hereda) | Recomendado |
| Política directa al usuario | Política → Usuario | Funciona, pero cuesta mantenerla |
| Servicios por roles | Política de permisos + **política de confianza** (quién puede asumir el rol) → Rol → el servicio recibe credenciales temporales | Siempre para servicios |

- **Por qué grupos** (T13 ~01:16:22-01:16:48): si la persona deja el equipo o pierde la cuenta, se crea otra, se mete en el grupo y tiene lo mismo que la anterior.
- **Identidades de máquina** (T13 ~01:15:31-01:15:44, ~01:18:16-01:18:40): un servidor o una Lambda también tienen identidad y se les asignan políticas o roles.
- **`Deny` explícito** (T13 ~01:18:42-01:18:55): aunque te den administrador, si en algún sitio hay un `Deny` sobre una acción, no puedes hacerla.

**Nota (rol: web frente a clase).** En clase el profesor definió los roles como "grupos de permisos" que se asignan a grupos o a usuarios, y la buena práctica como "crear un rol, asignarlo al grupo y meter a la persona en el grupo" (T13 ~01:15:44-01:16:28). Él mismo dijo que se había liado. En IAM eso es lo que hace una **política** (gestionada) adjunta a un grupo. Un **rol** es otra cosa: una identidad sin credenciales permanentes que alguien o algo **asume** (una Lambda, una tarea de ECS, GitHub Actions por OIDC), con una política de confianza que dice quién puede asumirlo. La definición correcta es la de la web (L03 «Conceptos», «Políticas en usuarios, grupos y roles»), y es la que importa para la práctica (§8).

### 4.3 Mínimo privilegio

**Idea.** Concede solo los permisos estrictamente necesarios (L03 «Una política por dentro»).

- En clase se usa `AdministratorAccess` por sencillez. En un trabajo real, no (L03; T13 ~01:17:06).
- Ejemplo del profesor (T13 ~01:17:20-01:17:48): si diera a toda la clase permisos de administrador en su cuenta, todos gastarían "como cosacos" y la factura le llegaría a él.

### 4.4 Demo: crear el usuario de trabajo

**Idea.** Se crea un grupo `administradores` con `AdministratorAccess` y un usuario con acceso a la consola dentro de ese grupo, y a partir de ahí se trabaja siempre con él, no con el raíz (L03 «Crear tu usuario de trabajo»; T13 ~01:23:03-01:33:10).

1. IAM → *User groups* → *Create group* → `administradores` → adjuntar `AdministratorAccess`. Al buscarla aparecen dos políticas parecidas; hay que elegir la gestionada por AWS que se llama exactamente así (T13 ~01:23:33-01:24:28).
2. IAM → *Users* → *Create user* → marcar **Provide user access to the AWS Management Console** → contraseña personalizada (o autogenerada que se cambia en el primer acceso) (T13 ~01:26:57-01:27:41). El profesor dice que este es el paso que "siempre le falla".
3. Añadirlo al grupo `administradores` → *Create user* (T13 ~01:28:01-01:28:27).
4. Guardar la **URL de inicio de sesión** de la cuenta, que contiene el ID de cuenta. Con el ID basta para entrar como usuario IAM (T13 ~01:29:02-01:31:05).
5. Cerrar sesión como raíz, entrar con el usuario nuevo y **activarle su propio MFA** (T13 ~01:30:17-01:33:04).

**Errores frecuentes en clase:**
- *El enlace directo de la web da "característica no disponible"*: buscar "IAM" en el buscador de la consola y navegar a *User groups* o *Users* desde el menú izquierdo (T13 ~01:24:35-01:25:18, ~01:26:39-01:26:48).
- *IAM pide "características avanzadas" y lleva a la pasarela de pago*: el profesor lo atribuyó a no haber completado el paso de la tarjeta en el alta, que solo verifica y no te saca de la capa gratuita *(dudoso)* (T13 ~01:25:18-01:25:46).
- *El nombre del usuario ya existe*: el profesor tenía uno previo y creó otro de prueba (T13 ~01:27:53, ~01:28:43).

---

## 5. Trabajar desde tu ordenador: autenticación, CLI, CloudShell y boto3

### 5.1 Formas de autenticarse

**Idea.** Desde 2026 el curso usa `aws login`, que da a la CLI y a los SDK las mismas credenciales que la consola en forma de credenciales **temporales**, sin claves de acceso permanentes (L03 «Autenticación»; CAMBIOS: antes "claves de acceso y `aws configure`").

| Método | Uso | Recomendación (L03 «Autenticación») |
|---|---|---|
| Contraseña + MFA | Consola web | Siempre con MFA |
| `aws login` | CLI y SDK desde tu ordenador | Opción por defecto en el curso |
| Rol de IAM | EC2, Lambda, ECS | Siempre para servicios |
| OIDC | GitHub Actions | Sin secretos guardados |
| Claves de acceso | Último recurso | Evitar, y nunca subirlas a Git |

- La **clave de acceso** da entrada a la API y la **contraseña**, a la consola (L03 «Clave de acceso o contraseña»).
- En organizaciones grandes se usa IAM Identity Center con `aws sso login` (L03).
- En clase (T13 ~01:22:07-01:23:03): también se podría entrar con una API key o un JSON de credenciales, pero `aws login` es más seguro. Genera un token que caduca, según el profesor entre 8 y 24 h *(dudoso)*. Cuando un código diga que faltan credenciales, basta con repetir `aws login`.

### 5.2 AWS CLI

**Idea.** Hay que instalar la CLI **v2**, no `pip install awscli` (L03 «AWS CLI»).

```bash
aws --version                 # 2.32 o superior
aws login                     # abre el navegador; elige tu usuario
aws sts get-caller-identity   # ¿quién soy? Devuelve UserId, Account y Arn
aws configure set region eu-west-3
aws configure set output json
```

- `aws sts get-caller-identity` devuelve la identidad de quien llama. En el ARN debe salir el usuario IAM creado, no el raíz (T13 ~01:35:12-01:35:31).
- Los que crearon la cuenta en clase **no debían hacer `aws login` todavía como raíz**: había que esperar a tener el usuario IAM (T13 ~01:20:06-01:20:23).
- En una máquina sin navegador, `aws login --remote` da un enlace para autorizar desde otro dispositivo (L03; T13 ~01:35:59).
- `Invalid choice` al hacer `aws login` = CLI antigua: hay que desinstalarla e instalar la actual. Si tras instalarla no se reconoce `aws`, abrid una terminal nueva (L03; T13 ~01:36:24-01:36:46).

### 5.3 CloudShell

**Idea.** Una terminal en el navegador con la CLI ya autenticada como el usuario de la consola. Sirve para probar comandos sin instalar nada (L03 «CloudShell»; T13 ~01:37:00-01:39:36).

```bash
aws sts get-caller-identity   # mismo usuario que arriba a la derecha de la consola
aws s3 ls                     # lista los buckets; en una cuenta nueva, vacío
```

Se abre con el icono de terminal de la barra superior. La primera vez tarda un poco y ofrece un tutorial que se puede cerrar (T13 ~01:37:33-01:38:00).

### 5.4 boto3

**Idea.** boto3 es el SDK de AWS para Python: lo mismo que la CLI, desde código (L03 «Python: boto3»; T13 ~01:39:38-01:43:00).

```bash
python -m venv .venv            # buena práctica: entorno virtual propio
python -m pip install --upgrade boto3
```

```python
import boto3

sts = boto3.client("sts")
print(sts.get_caller_identity()["Arn"])
```

- **Orden de búsqueda de credenciales** (L03), entre otros: parámetros del código → variables de entorno → configuración en `~/.aws` → rol de la máquina. Por eso el mismo código funciona en local (con `aws login`) y en una Lambda (con su rol) sin cambiar nada.
- **Error en clase** (T13 ~01:41:18-01:42:27): la primera ejecución en el notebook falló pidiendo **botocore CRT**. Se instaló desde la celda (con `%pip`, no con `!`) y luego hubo que **reiniciar el kernel**.
- Si una librería no reconoce `aws login`, se exportan credenciales temporales a la sesión (L03):

```bash
eval "$(aws configure export-credentials --format env)"
```

- Si falla la autenticación, puede ser que no se haya creado la carpeta `~/.aws` del usuario (T13 ~01:43:08).
- **Entornos virtuales** (T13 ~01:50:44-01:53:58): el profesor instaló boto3 en el Python global por rapidez, pero recomienda un entorno virtual (`python -m venv`) con un `requirements.txt` de versiones fijadas. El motivo: en la nube se quiere **replicar lo que funciona en local**, y si las versiones no cuadran falla al subirlo. El siguiente paso es una imagen de Docker; con ella las diferencias que quedan son variables de entorno o credenciales distintas entre la máquina y tu portátil. En Jupyter hay que instalar también `ipykernel` en el entorno.

### 5.5 AWS Toolkit en VS Code

**Idea.** La extensión **AWS Toolkit** permite explorar y crear recursos (S3, Lambda, CloudWatch...) sin salir del editor (L03 «VS Code»; T13 ~01:43:26-01:48:25).

- Hay que instalar la que publica Amazon Web Services, verificada. Se puede crear un perfil de VS Code aparte para no mezclar extensiones (T13 ~01:43:26-01:44:13).
- Si ya se hizo `aws login`, reconoce las credenciales. Si no: Explorer → *Connect to AWS* → *New connection* → **console credentials** → nombre de perfil y región → se valida en el navegador (T13 ~01:44:35-01:45:58).
- Desde el árbol se ven y se suben o bajan ficheros de un bucket. Además de la región elegida aparece N. Virginia, donde "vive" lo global (T13 ~01:47:27-01:48:25).

**Pregunta de un alumno** (T13 ~01:49:33-01:50:13): ¿acceder a S3 desde VS Code cuenta como sacar datos de AWS? Loguearse no tiene coste. Descargar datos del bucket a tu ordenador sí es transferencia de salida, aunque la franja gratuita es amplia. Más adelante se verá cómo desarrollar dentro de AWS, en una máquina Linux.

---

## 6. Redes: Amazon VPC

### 6.1 Qué es una VPC y la notación CIDR

**Idea.** Una **VPC** (*Virtual Private Cloud*) es una red virtual privada dentro de una **región**. Se divide en **subredes**, cada una en una zona de disponibilidad, y cada región trae una **VPC por defecto** lista para usar (L04 «Qué es una VPC»; T13 ~02:18:40-02:19:25).

- El profesor lo plantea otra vez como cajas: región (París) → VPC → subredes (T13 ~02:18:48-02:19:07).
- **CIDR.** Una red se escribe como `dirección/prefijo`. El prefijo dice cuántos de los 32 bits de la IPv4 están fijados, y el número de direcciones es $2^{32-\text{prefijo}}$ (T13 ~02:19:25-02:20:33).

| Bloque | Direcciones | Ejemplo de clase |
|---|---|---|
| `/16` | $2^{16}$ = 65.536 | La VPC por defecto, `172.31.0.0/16` (L04; T13 ~02:20:33, ~02:30:23) |
| `/17` | 32.768 | Media clase: `172.31.0.0/17` y `172.31.128.0/17` (T13 ~02:20:57-02:22:32) |
| `/20` | 4.096 | Cada subred por defecto, una por AZ (T13 ~02:23:37, ~02:30:47) |
| `/31` | 2 | (T13 ~02:23:55-02:24:25) |
| `/32` | 1 | Una sola IP (T13 ~02:23:55) |

- Cuanto **mayor** es el prefijo, **menos** direcciones; un bloque con prefijo mayor cabe dentro de uno con prefijo menor. Las direcciones se recorren desde el último octeto (0-255) y después saltan al anterior (T13 ~02:23:37-02:24:44).
- **Para qué dividir** (T13 ~02:20:57-02:23:28): para aislar partes de la red. Ejemplo de clase: la mitad derecha del aula en una subred y la izquierda en otra, que solo se hablan si las reglas (cortafuegos) lo permiten. Así se puede impedir que una zona acceda a datos personales.
- El profesor advirtió que es algo avanzado ("si os parece chino, olvidaos") y que las redes son "lo que más dolores de cabeza nos puede traer", así que en el curso se tocará solo lo necesario (T13 ~02:22:36, ~02:33:17).

**Nota:** en la transcripción aparece una vez "2 elevado a 31 menos el número" (T13 ~02:23:37). Es un lapsus: la fórmula correcta es $2^{32-n}$, la que usó antes. Además, AWS **reserva 5 direcciones** de cada subred (red, router, DNS, una de reserva y *broadcast*), así que un `/20` deja 4.091 utilizables.

### 6.2 Subredes públicas y privadas, Internet Gateway y NAT

**Idea.** Una subred es **pública** si su tabla de rutas envía `0.0.0.0/0` a un **Internet Gateway** y sus recursos tienen IP pública. Es **privada** si no tiene ruta directa a Internet (L04 «Subred pública y privada»; T13 ~02:24:55-02:26:53).

| | Pública | Privada |
|---|---|---|
| Ruta a Internet | Por Internet Gateway | Sin ruta directa |
| IP pública | Sí | No |
| Uso típico (L04; T13 ~02:26:07-02:26:39) | Balanceadores, webs, APIs expuestas | Bases de datos, procesos internos, cómputo |

- **Internet Gateway (IGW).** Es la puerta de la VPC a Internet (L04 «Una VPC por dentro»; T13 ~02:25:25-02:25:36). El profesor lo llamó "un PaaS" *(dudoso)*: es un componente gestionado de la VPC.
- **NAT Gateway.** Deja que una subred privada **salga** a Internet (p. ej., para descargar paquetes) sin ser accesible desde fuera. **Cuesta por hora y por GB** (L04; T13 ~02:25:45-02:26:02). Todo lo que sale a Internet o cada servicio nuevo se paga (T13 ~02:26:56).
- **Tablas de rutas.** En la VPC por defecto la ruta `0.0.0.0/0` (todo destino) apunta al Internet Gateway (L04 «Demo»; T13 ~02:32:27-02:33:02).
- **DNS.** En las propiedades de la VPC se ve si resuelve nombres. El DNS traduce un dominio a una IP para no tener que usar números. Los dominios se compran a registradores. El curso no entra en ello (T13 ~02:30:56-02:32:15).

### 6.3 Servicios públicos y privados; Gateway Endpoint

**Idea.** Unos servicios viven **dentro** de tu VPC (EC2, RDS) y otros tienen un **endpoint público** fuera de ella (S3, DynamoDB, Route 53). Que el endpoint sea público **no** hace públicos tus datos: siguen protegidos por IAM (L04 «Servicios públicos y privados», «Dentro y fuera de la VPC»; T13 ~02:27:06-02:28:47).

- Lo bueno de un servicio público: si quieres publicar un dato, ya está accesible. Lo malo: si un dato privado acaba en algo expuesto, "la has liado", sobre todo con datos personales (T13 ~02:28:47-02:29:05).
- El profesor recordó que hoy S3 bloquea por defecto el acceso de terceros, y que antes había que bloquearlo uno mismo (T13 ~02:27:42-02:27:52).
- **Gateway Endpoint** (L04 «Acceso a S3 desde una VPC»): lleva el tráfico de la VPC a S3 o DynamoDB por la red de AWS, **sin coste**, sin pasar por Internet ni por un NAT Gateway.
- En clase: acceder a S3 desde EC2 o Lambda va por la red interna y no se cobra; acceder desde Internet tiene una franja gratuita y después se paga (T13 ~02:29:10-02:29:39).

**Nota (dos matices).** (1) El profesor dijo que el endpoint de S3 "no lo tenemos que configurar" y que casi todos los productos acceden directamente a S3 (T13 ~02:29:46). Desde una subred **privada** sin NAT, el Gateway Endpoint **sí hay que crearlo** y asociarlo a la tabla de rutas, aunque sea gratis (así lo plantea L04). Desde la VPC por defecto, con subredes públicas, se llega a S3 por el Internet Gateway, y los servicios gestionados como Lambda fuera de VPC llegan sin hacer nada. (2) Los buckets siempre han sido privados por defecto. Lo que cambió en 2023 es que **Block Public Access** viene activado por defecto en los buckets nuevos, lo que hace más difícil exponerlos por error.

### 6.4 Grupos de seguridad

**Idea.** Un **grupo de seguridad** es el cortafuegos de cada instancia: decide qué puertos y orígenes pueden entrar (L05 «Acceso seguro»; T13 ~02:35:59-02:36:20).

- Abrir SSH (22) solo desde **tu IP** (la consola tiene la opción *My IP*), no desde `0.0.0.0/0`. Para una web, HTTP (80) y HTTPS (443) desde cualquier lugar (L05 «Acceso seguro»; T13 ~02:35:59).
- Se pueden crear antes o durante el lanzamiento y reutilizarse (L05). Son las "reglas de firewall" de las que habló el profesor al dividir la clase en subredes (T13 ~02:21:48).

**Nota:** la lección de VPC (L04) no trata los grupos de seguridad; aparecen en la de EC2 (L05) y en clase ya dentro de EC2. Se incluyen aquí porque son la otra mitad del control de red: la tabla de rutas decide **por dónde** va el tráfico y el grupo de seguridad **qué** tráfico admite cada recurso.

### 6.5 Demo: explorar la VPC por defecto

```text
VPC → Your VPCs → la marcada como Default (172.31.0.0/16)
    → Subnets: una /20 por zona de disponibilidad (3 en París)
    → Route tables: 0.0.0.0/0 → Internet Gateway
```

(L04 «Demo»; T13 ~02:30:04-02:33:02.)

**Aviso: no borréis la VPC por defecto.** Muchos asistentes la usan, entre ellos ECS Express Mode (L04 «Demo»).

---

## 7. Repaso del día siguiente (T14)

**Idea.** Al empezar la clase del 14 el profesor resumió lo visto el 13 y fijó qué servicios se verán (T14 ~00:00:14-00:04:04):

- Servicios del curso: servidores (EC2), contenedores, funciones (Lambda), almacenamiento (S3), algo de IA y un par más. El resto, para descubrir por cuenta propia (T14 ~00:00:51-00:01:26).
- Regiones y zonas: interesan por **normativa** y por **latencia** con los usuarios. AWS no dice dónde está exactamente cada zona (T14 ~00:01:26-00:02:46).
- IaaS, PaaS y SaaS (T14 ~00:02:50-00:03:18); ver la nota de §2.3 sobre S3.
- Alerta de costes y usuario de trabajo para no usar todos los privilegios del raíz (T14 ~00:03:18-00:03:29). Lo demás que repasó (EC2, AMIs, SSH/SCP) es de otro documento.

---

## 8. Para la práctica

**Idea.** La práctica B7 monta un pipeline de KID en AWS: scraper → **S3** → extracción con **Bedrock** (salidas estructuradas) → **Aurora PostgreSQL Serverless v2 con RDS Data API** → API **FastAPI en Lambda con Function URL** → **Streamlit en ECS Express Mode**, con **Terraform + GitHub Actions (OIDC, estado en S3)** (ENUNCIADO §6). Casi todo lo de este documento aparece en alguna pieza.

| Tema de este documento | Dónde aparece en la práctica |
|---|---|
| Región (§2.2) | Todo se despliega en una sola región. **Nota:** Bedrock no tiene todos los modelos en todas las regiones; hay que comprobarlo antes de fijar `eu-west-3` o `eu-north-1`, como recoge `docs/DECISIONES.md` (D-0.2) |
| Modelos de servicio (§2.3) | La arquitectura es casi entera serverless o gestionada: S3, Bedrock, Aurora Serverless v2, Lambda y ECS Express (contenedores sin gestionar servidores). No hay EC2 |
| Costes y Budgets (§3) | Un **Zero spend budget** desde el primer día. **Nota:** Aurora Serverless v2 cobra mientras tenga capacidad activa, y ECS Express y sus IP públicas cobran por hora: hay que destruirlos (`terraform destroy`) cuando no se usen. Conviene evitar el NAT Gateway (§6.2) |
| Actividades de créditos (§3.6) | Dos coinciden con la práctica: **crear una base de datos Aurora** y **usar un modelo en Bedrock** |
| Raíz y MFA (§3.2) | Nada de la práctica se hace con el raíz |
| Mínimo privilegio (§4.3) | En la práctica sí importa. **Nota:** el rol de la Lambda debería poder solo leer la base de datos por Data API (`rds-data:*` sobre el clúster y lectura del secreto); el script de extracción, leer y escribir en el bucket e invocar Bedrock; el rol de GitHub Actions, lo necesario para Terraform |
| Roles y política de confianza (§4.2) | La Lambda y la tarea de ECS tienen **rol de ejecución**; GitHub Actions asume un rol por **OIDC**, cuya política de confianza lo limita al repositorio. Así se cumple la regla "sin credenciales en el repositorio" (ENUNCIADO §5; DECISIONES D-0.4) |
| `aws login`, CLI, boto3 (§5) | En local, scraper y extracción usan boto3 con las credenciales de `aws login`; en la nube, el mismo código usa el rol (orden de búsqueda de credenciales, §5.4). **Nota:** si alguna librería no lee `aws login`, se usa `aws configure export-credentials` |
| Entornos y reproducibilidad (§5.4) | `requirements.txt` con versiones fijadas e imágenes de Docker para la API y la aplicación |
| Servicios públicos y privados (§6.3) | **S3** tiene endpoint público pero los datos siguen privados: el enunciado exige no exponer documentos salvo a través de la API y la aplicación (ENUNCIADO §5). **Nota:** el bucket debe tener Block Public Access activado |
| VPC y Data API (§6) | **Nota:** Aurora vive en subredes de una VPC (la de por defecto vale), pero la **Data API** se consulta por HTTPS con IAM. La Lambda puede ir **fuera de la VPC**, sin NAT ni grupos de seguridad para conectar a PostgreSQL. Es la razón de elegirla frente a la "conexión directa por VPC" que el enunciado da como alternativa |
| Function URL (§6.3) | Es un endpoint HTTPS público de la Lambda. **Nota:** con `auth_type = NONE` cualquiera puede llamarla, así que solo debe devolver datos que se puedan publicar |
| VPC por defecto (§6.5) | **ECS Express Mode** la usa: no hay que borrarla (L04) |
| Grupos de seguridad (§6.4) | **Nota:** si la base de datos se usa solo por Data API, su grupo de seguridad no necesita abrir el puerto 5432 a Internet |

---

## 9. Preguntas de repaso

1. **¿Qué diferencia hay entre una región y una zona de disponibilidad, y para qué sirve desplegar en varias zonas?**
   Una región es un área geográfica aislada (p. ej. `eu-west-3`, París). Una zona es una ubicación aislada dentro de ella, con uno o más centros de datos. Desplegar en varias zonas permite seguir funcionando si una falla (§2.2).

2. **Pon un ejemplo de AWS de IaaS, de PaaS/serverless y de SaaS, y di qué gestionas tú en cada caso.**
   IaaS: EC2 (sistema, runtime, datos y aplicación). PaaS/serverless: Lambda (solo código y datos). SaaS: Textract o Athena desde la consola (solo el uso) (§2.3).

3. **¿Qué pasa al agotar los créditos en el plan gratuito y en el de pago?**
   En el gratuito la cuenta se cierra sin cargos (máximo 6 meses). En el de pago se factura a precio normal (créditos válidos 12 meses) (§3.3).

4. **¿Por qué no se usa el usuario raíz para trabajar y qué se hace en su lugar?**
   Porque tiene todos los permisos y no se pueden limitar. Se le activa MFA, no se le crean claves y se trabaja con un usuario IAM dentro de un grupo `administradores` (§3.2, §4.4).

5. **¿Qué es un rol de IAM y en qué se diferencia de un usuario?**
   Un rol es una identidad sin credenciales permanentes que un servicio o una persona asume y que da credenciales temporales. Una política de confianza dice quién puede asumirlo. Un usuario tiene credenciales propias y fijas (§4.1, §4.2).

6. **Si una política te da `AdministratorAccess` y otra te deniega `s3:DeleteObject`, ¿puedes borrar objetos?**
   No: los permisos se suman, pero un `Deny` explícito gana siempre (§4.2).

7. **¿Qué ventaja tiene `aws login` sobre las claves de acceso, y qué comando confirma con qué identidad estás trabajando?**
   Da credenciales temporales y no deja claves permanentes en disco ni en Git. Lo confirma `aws sts get-caller-identity` (§5.1, §5.2).

8. **¿Cuántas direcciones tiene un `/20` y qué hace pública a una subred?**
   $2^{12}$ = 4.096, de las que AWS reserva 5. Una subred es pública si su tabla de rutas envía `0.0.0.0/0` a un Internet Gateway y sus recursos tienen IP pública. Una privada puede salir a Internet con un NAT Gateway, que es de pago (§6.1, §6.2).
