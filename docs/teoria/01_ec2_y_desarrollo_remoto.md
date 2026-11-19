# Amazon EC2 y desarrollo remoto: de la máquina virtual al primer API

> **Fuentes:**
> - **L05-L10** = lecciones de la web del curso, `docs/raw/miax-cloud-main/content/`: `05-ec2.md` (EC2), `06-ssh-scp.md` (SSH y SCP), `07-vscode.md` (desarrollo remoto con VS Code), `08-cron.md` (cron), `09-env.md` (variables de entorno) y `10-fastapi-ec2.md` (primer API en EC2). Leídas completas. Consultadas para enlazar: `03-iam-cli.md` (L03, autenticación y roles), `11-s3.md` (L11, credenciales en Python y rol de la instancia) y `14-lambda-triggers.md` (L14, EventBridge Scheduler y Function URL).
> - **CAMBIOS** = `docs/raw/miax-cloud-main/CAMBIOS.md` (cambios de la web respecto a la presentación original).
> - **T13** = `docs/raw/transcripciones/T13.txt`, transcripción automática de la clase del 13/11/2026. Tramo leído entero: **~02:30-04:50** (consola de la VPC, EC2, SSH/SCP, VS Code remoto, introducción a cron).
> - **T14** = `docs/raw/transcripciones/T14.txt`, transcripción de la clase del 14/11/2026. Tramo leído entero: **~00:00-03:08** (repaso, VS Code remoto, cron, variables de entorno, FastAPI en EC2, uv, ejercicio con GitHub). A partir de ~03:08 empieza S3, que no se trata aquí.
> - **EJ** = `docs/raw/miax-cloud-main/ejemplos/api-suma/` (`src/app.py`, versión del API con `/health`).
> - **ENUNCIADO** = `docs/raw/transcripciones/enunciado.txt` (Práctica B7, para la sección 8).
>
> **Convenciones:** "(T13 ~03:12)" = hora aproximada en la transcripción; todo lo que viene de ellas es **paráfrasis** de un texto automático muy ruidoso ("C 2", "F, Dos" = EC2; "ubicorn", "yubicon" = uvicorn; "Chrome", "Chronjob" = cron), y lo que no se entiende bien va marcado *(dudoso)*. "(L05 «Tipos de instancia»)" = diapositiva de la lección, citada por su título. **Nota:** = contenido propio (correcciones, conexiones, inferencias), no del material de clase. La red (VPC, subredes, tablas de rutas, CIDR) y la cuenta (IAM, presupuestos) están en [00_fundamentos_aws.md](00_fundamentos_aws.md).
>
> Escrito el 19/11/2026.

---

## 1. Qué es EC2 y de qué piezas se compone

**Idea.** EC2 (*Elastic Compute Cloud*) alquila máquinas virtuales en AWS por segundos: es IaaS puro, tú gestionas el sistema operativo y lo que corre encima (L05 «Qué nos da EC2»; T13 ~02:33:30). "La nube es el servidor de otra persona": detrás sigue habiendo una máquina física (T13 ~02:40:45).

| Pieza | Qué es | Dónde se trata |
|---|---|---|
| **Instancia** | La máquina virtual | §2.7 |
| **AMI** | Plantilla con sistema operativo y software | §2.1, §2.9 |
| **Tipo de instancia** | Combinación de CPU, memoria y red | §2.2 |
| **EBS** | Disco persistente (normalmente el disco raíz) | §2.3 |
| **Almacén de instancia** | Disco temporal, se pierde al detener | §2.3 |
| **Par de claves** | Acceso por SSH sin contraseña | §2.4 |
| **Grupo de seguridad** | Cortafuegos de la instancia | §2.4 |
| **IP pública / elástica** | Dirección accesible desde Internet; la elástica es fija | §2.5 |
| **Etiquetas** | Metadatos clave-valor | abajo |
| **VPC** | Red aislada en la que vive la instancia | 00_fundamentos |

(L05 «Qué nos da EC2»; T13 ~02:34:32-02:38:08.)

- **Escalado.** El profesor lo enlazó con el origen de AWS: picos de usuarios (rebajas, primeros días de mes) que se cubren levantando 2 o 3 instancias en vez de una solo durante esos días (T13 ~02:33:48-02:34:32).
- **Etiquetas.** Ejemplo de clase: etiquetar todas las máquinas con `grupo = MIAX14` o con el usuario responsable, para filtrarlas o analizar metadatos después (T13 ~02:37:05-02:37:52).

---

## 2. Lanzar y gestionar una instancia

### 2.1 AMI (Amazon Machine Image)

**Idea.** La AMI define lo que trae la máquina al arrancar; si la creas tú a partir de una instancia configurada, no hay que reinstalar nada en las siguientes (L05 «Amazon Linux 2023»).

- En el curso se usa siempre **Amazon Linux 2023** (AL2023), con `dnf` y `systemctl`; el material original usaba Amazon Linux 2 con `yum` (CAMBIOS, tabla de obsolescencia; T13 ~02:40:56).
- Elegir **Windows** como sistema operativo implica pagar la licencia de Windows Server, aunque la consola muestre la etiqueta de capa gratuita en el tipo (T13 ~02:51:09-02:51:26).
- Para IA existen las *Deep Learning AMI* (controladores CUDA, PyTorch); para entrenar sin gestionar máquinas, SageMaker (L05 «Amazon Linux 2023»).
- El profesor sugirió tener varias AMI según el trabajo: una para pruebas en una instancia pequeña y otra para trabajo exigente, y lanzarlas solo cuando hagan falta (T13 ~03:34:07-03:34:26).

**Nota:** el profesor dijo que la clave de acceso puede ir "preconfigurada" en la AMI (T13 ~02:35:10). Lo preciso es que el par de claves se elige **al lanzar**; una AMI creada desde una instancia conserva el `authorized_keys` de esa instancia, así que la clave original seguirá funcionando además de la que elijas.

### 2.2 Tipos de instancia y opciones de compra

**Idea.** El nombre `t3.micro` se lee familia `t`, generación `3`, tamaño `micro`; la familia indica para qué está optimizada (L05 «Tipos de instancia»).

| Familia | Enfocada a (L05) | Comentario en clase (T13 ~02:38:15-02:39:32) |
|---|---|---|
| **T** | Uso general con ráfagas de CPU | CPU y RAM suben de la mano |
| **M** | Uso general equilibrado | "un poco lo mismo" |
| **C** | Cómputo | mucha más CPU |
| **R** | Memoria | mucha más RAM |
| **P** | GPU para IA (P4 A100, P5 H100/H200, P6 Blackwell) | modelos grandes en la memoria de la gráfica |
| **G** | GPU para gráficos e inferencia | p. ej. videojuegos |

- Capa gratuita: `t3.micro`, `t3.small`, `t4g.micro`, `t4g.small`, `c7i-flex.large` y `m7i-flex.large`. La web usa `t3.micro` (L05 «Tipos de instancia»); el material antiguo, `t2.micro` (CAMBIOS).
- **Cuotas de GPU.** Las instancias con GPU requieren pedir aumento de cuota (L05). El profesor contó que, en su empresa, al desplegar mucho el proveedor les "capó" y tuvieron que abrir un ticket; en regiones pequeñas puede no haber GPU disponibles hasta que instalen más servidores (T13 ~02:39:38-02:40:45).
- **Opciones de compra:** bajo demanda (sin compromiso, por segundos), Savings Plans y reservadas (1 o 3 años, uso estable) y Spot (barata, pero AWS puede reclamarla; para procesos interrumpibles como entrenar modelos) (L05 «Opciones de compra»).

### 2.3 Almacenamiento: EBS, almacén de instancia, EFS y S3

**Idea.** Bloque (EBS) se comporta como un disco de una sola instancia; fichero (EFS) como una carpeta de red compartida; objeto (S3) como un almacén por HTTP (L05 «Tipos de almacenamiento»).

| | **EBS** (bloque) | **EFS** (fichero) | **S3** (objeto) |
|---|---|---|---|
| Quién accede | Una instancia | Muchas a la vez | Cualquier cliente con permiso |
| Alcance | Una zona de disponibilidad | Varias zonas | Regional, por Internet |
| Se modifica | Por bloques | Por ficheros | El objeto entero |

(L05 «Tipos de almacenamiento».)

- El disco raíz suele ser **EBS `gp3`**; admite **snapshots** (L05). Hay familias SSD y HDD; el profesor lo comparó con el arranque de un portátil con SSD frente a HDD (T13 ~02:44:09-02:44:46).
- **Almacén de instancia** (temporal): útil para un fichero intermedio enorme. Ejemplo de clase: procesas 10 GB en el temporal y guardas en EBS solo los 5 MB del resultado; también se puede usar S3 directamente (T13 ~02:36:20-02:36:57).
- **EFS**: varias personas o máquinas que comparten carpeta (una procesa, otra transforma, otra hace el *dashboard*) con menos latencia que S3 (T13 ~02:41:44-02:42:32).
- **Tamaño del EBS.** Si se asigna muy poco, la máquina "deja de funcionar" (p. ej. al instalar VS Code Server); si se asigna de más, pagas lo que no usas. Consejo: la primera vez mide cuánto consumes (con 32 GB asignados y 15 usados, 20 GB bastarían) (T13 ~02:42:32-02:43:06, ~03:34:26-03:34:50).
- **Durabilidad.** EBS tiene "tres nueves" (99,9 %); S3, muchos más (T13 ~02:45:17-02:45:39; T14 ~03:09:29).
- **Tiempo de arranque.** AWS cobra también el tiempo que tarda en levantarse la máquina; si una tarda mucho en arrancar y la vas a usar poco, compara alternativas (T13 ~02:44:46-02:45:12) *(el ejemplo numérico de la transcripción, "10 h de arranque para 2 min de uso", es exagerado a propósito)*.

**Nota:** en T13 ~02:35:41 el profesor dijo que el almacenamiento de la máquina "es volátil" y se pierde al apagarla, y a continuación se corrigió: el EBS es el disco **persistente** y lo volátil es el almacén de instancia (T13 ~02:36:20). La web lo dice sin ambigüedad (L05 «Tipos de almacenamiento»).

### 2.4 Par de claves, grupo de seguridad y puertos

**Idea.** Linux no usa contraseña: AWS guarda la **clave pública** y tú la **privada** (`.pem`); el **grupo de seguridad** decide qué puertos y orígenes pueden entrar. Para conectarte necesitas las dos cosas: la clave que casa con la pública y una regla que te deje pasar (L05 «Acceso seguro»; T13 ~02:45:51-02:46:15, ~02:49:54-02:50:13).

- El par se crea en *Key Pairs* o durante el lanzamiento; formato `.pem` para OpenSSH (también en Windows 10/11) y `.ppk` solo para PuTTY. Una clave puede servir para varias instancias (L05 «Acceso seguro»).
- **No compartas la `.pem`:** quien la tenga entra en todas las máquinas que usen esa clave (T13 ~02:47:10).
- **Una clave por máquina** es la buena práctica: si pierdes una, solo pierdes esa máquina. "Al final entra la pereza" y se reutiliza, pero no es buena práctica (T13 ~04:31:50-04:32:06).
- **Clave filtrada = clave muerta.** En T14 el profesor abrió sin querer la `.pem` de un alumno mientras compartía pantalla: terminó la instancia y borró el par de claves en la consola (hay que escribir *Delete* para confirmar), y el alumno tuvo que repetir el proceso con una clave nueva. "Cualquier clave que se haya compartido la tenemos que borrar" (T14 ~02:45:22-02:46:48).
- **Grupo de seguridad.** SSH (22) solo desde **tu IP** (botón *My IP*), no desde `0.0.0.0/0`; para una web, HTTP (80) y HTTPS (443) desde cualquier sitio (L05 «Acceso seguro»). El que crea el asistente se llama `launch-wizard-N` y abre el 22 (T13 ~02:55:33-02:55:59). En el aula todos salían a Internet por la misma IP pública, así que *My IP* era la misma para todos (T13 ~02:47:20-02:47:40, ~02:52:46).
- **Puertos.** Hay unos 65.500 (exactamente 65.535); algunos tienen uso convencional: HTTP 80, HTTPS 443, PostgreSQL 5432. Puedes desplegar un servicio en el puerto que quieras, siempre que lo indiques al conectarte y lo abras en el grupo de seguridad (T13 ~02:48:00-02:49:35).
- Los grupos de seguridad son de **permiso explícito**: lo que no se permite con una regla (una IP o un rango CIDR) no entra (T13 ~03:07:29-03:08:06).

**Nota:** el profesor mencionó que "cualquier rango hasta el 10.000 y pico" está reservado y que MySQL usa "el 4321" *(dudoso)*. Lo estándar: los puertos *well-known* son 0-1023; MySQL usa 3306 y PostgreSQL 5432.

### 2.5 Direcciones IP, DNS público y su coste

**Idea.** **Toda IPv4 pública cuesta**: 0,005 $/hora, también la que AWS asigna automáticamente a una instancia en marcha. La elástica es fija y se paga aunque no esté asociada (L05 «Direcciones IP», «IP elástica»; CAMBIOS: "IP pública: sin coste → 0,005 $/hora"). **Nota:** AWS empezó a cobrarlas en febrero de 2024; por eso el material antiguo decía que no tenían coste.

| Tipo | ¿Se conserva al detener? | Coste (L05) |
|---|---|---|
| **Privada** | Sí | Sin coste |
| **Pública** (automática) | No, cambia al arrancar | 0,005 $/hora |
| **Elástica** | Sí, hasta que la liberes | 0,005 $/hora, también sin asociar |

- Al pasar a *Running* la instancia recibe IP pública, IP privada y un **DNS público** que apunta a esa IP (T13 ~02:53:52-02:54:08; L05 «Demo: lanzar una instancia»).
- La IP elástica "te la quedas y hasta que no la sueltas te siguen cobrando"; poco dinero, pero se acumula si lo haces con todas las máquinas (T13 ~03:56:39-03:56:55). Libérala cuando no la uses (L05 «IP elástica»).
- Se puede lanzar la instancia **sin IP pública**; entonces solo pagas el almacenamiento (T13 ~03:00:51-03:01:10).

**Nota (contradicción importante).** En clase el profesor repitió que el **DNS público no cambia** al detener y arrancar, y que por eso conviene conectarse por DNS y no por IP (T13 ~03:01:40, ~03:41:42, ~03:56:24, ~04:31:00). Esto no es así en la VPC por defecto: el DNS público tiene la forma `ec2-<IP con guiones>.<región>.compute.amazonaws.com`, se deriva de la IP pública y **cambia con ella**. Lo correcto es lo que dice la web: si detienes la instancia, actualiza `HostName` en tu configuración o usa una IP elástica (L07 «Trucos»). También dijo que al detener se sigue pagando "el almacenamiento y la IP" (T13 ~02:59:57-03:00:03): con IP automática, al detener se libera y deja de cobrarse; con IP elástica sí se sigue pagando.

### 2.6 Salida a Internet: Internet Gateway y NAT gateway

**Idea.** Una instancia con IP pública en una subred pública entra y sale por el **Internet Gateway**; las de una subred privada solo pueden **salir** a través de un **NAT gateway** (que tiene IP elástica), y nadie puede iniciar desde fuera una conexión hacia ellas (L05 «NAT gateway»; T13 ~03:03:19-03:03:50).

- Para qué hace falta salir: instalar paquetes de Python, actualizar el sistema o llamar a API externas (un LLM de otro proveedor es "Internet"; uno gestionado por AWS se puede alcanzar por red interna con permisos) (T13 ~03:03:50-03:06:08).
- **Coste del NAT:** desde 0,045 $/hora más 0,045 $/GB; más de 30 $ al mes aunque no pase tráfico (L05 «NAT gateway»).
- El acceso a S3 desde EC2 o Lambda va por la red interna de AWS y no se cobra la transferencia (T13 ~02:29:16-02:29:39).
- El recorrido de la consola por la VPC por defecto (CIDR `/16`, tres subredes `/20`, tabla de rutas con `0.0.0.0/0` hacia el IGW) (T13 ~02:30:04-02:33:17) está en [00_fundamentos_aws.md](00_fundamentos_aws.md).

**Nota:** en la práctica no hace falta NAT: las piezas de referencia (Lambda, S3, Bedrock, RDS Data API) son servicios gestionados (ENUNCIADO §6). Un NAT olvidado es uno de los cargos fijos más caros que puede generar una cuenta de estudiante.

### 2.7 Lanzar una instancia (demo y recomendaciones de clase)

**Idea.** Nombre, AMI, tipo, par de claves, red (SSH desde tu IP) y almacenamiento; al lanzar, el estado pasa de *Pending* a *Running* (L05 «Demo: lanzar una instancia»).

```text
Name: miax-<alias>   AMI: Amazon Linux 2023   Arquitectura: 64 bits (x86)
Instance type: t3.micro (web)  |  c7i-flex.large (recomendado en clase para VS Code)
Key pair: crear nuevo, RSA o ED25519, formato .pem   Network: SSH desde My IP
Storage: 8 GB por defecto  ->  32 GB en clase
```

- **Lo que se hizo en clase** (T13 ~02:50:23-02:53:42; T14 ~02:38:44-02:40:24): como la instancia se iba a usar con VS Code Server, el profesor eligió `c7i-flex.large` (2 vCPU, 4 GB de RAM, T13 ~03:37:23-03:37:31) y subió el disco de 8 a **32 GB**. Avisó de que gasta algo más y de que hay que acordarse de borrarla. En la demo se le olvidó guardar el cambio de disco y la instancia salió con 8 GB (T13 ~02:55:04): conviene revisar el resumen antes de pulsar *Launch*.
- Pestañas útiles de la instancia: **Details** (AMI ID, IP, DNS), **Monitoring** (CPU, tráfico de red) y **Security** (grupo de seguridad) (T13 ~02:54:11-02:55:33).
- Varias instancias pueden llamarse igual; lo que las distingue es el **Instance ID**, aunque es mejor no repetir nombres (T13 ~03:24:36-03:24:51). Las de tipo `t` a veces tardan más en inicializarse por demanda (T13 ~03:25:15-03:25:28).
- Servidores en la **misma subred** pueden hablar entre sí si los grupos de seguridad lo permiten (T13 ~03:34:54-03:35:23).

**Nota (tamaño):** la web y la clase no coinciden. L05 usa `t3.micro` (1 GB de RAM) en todo el bloque y L07 avisa de que VS Code Server "puede quedarse justo" y propone `t3.small`. En clase el profesor fue más tajante: con una micro "no te va a funcionar"; hace falta al menos una vCPU y un par de GB de RAM y, sobre todo, disco, porque 8 GB se llenan en cuanto instalas una extensión (T14 ~03:01:18-03:01:54). Un alumno usó `t2.medium` con 16 GB sin problemas (T14 ~03:00:55). `c7i-flex.large` está en la capa gratuita de las cuentas nuevas (L05 «Tipos de instancia»), pero eso no la hace gratuita para siempre: consume créditos.

### 2.8 Detener o terminar

**Idea.** Mientras la instancia está en *Running* se paga el cómputo, estés conectado o no. Detenerla elimina el coste de cómputo pero no el del disco; terminarla borra todo (L05 «Detener o terminar»; T13 ~02:59:24-03:00:43).

| Acción | Cómputo | Disco EBS | Datos |
|---|---|---|---|
| **Stop** | No se paga | Se sigue pagando | Se conservan |
| **Terminate** | No se paga | Se borra por defecto | Se pierden |

- Desconectarse (cerrar la sesión SSH) **no** detiene la instancia (T13 ~02:59:24).
- Una instancia terminada sigue visible en la consola un rato (media hora o una hora); se deja de cobrar en el momento de terminarla (T13 ~03:28:58-03:29:35; L05).
- Tras terminar, revisa que no queden **volúmenes** ni **IP elásticas** (L05 «Detener o terminar»). Se puede desacoplar el EBS antes de terminar si quieres conservar solo el disco (T13 ~03:00:21-03:00:26).
- Al acabar una sesión de trabajo, el profesor recomendó ponerse una alarma para apagar la máquina (T14 ~03:08:26-03:08:40).

### 2.9 Crear una AMI propia y lanzar desde ella (actividad de créditos)

**Idea.** La actividad *Earn AWS credits → Lanzamiento de una instancia mediante EC2* da 20 $; después se crea una AMI desde la instancia y se lanza la instancia de trabajo a partir de ella (L05 «Ejercicio», «Ejercicio: instancia desde tu AMI»).

1. *Instances* → seleccionar → **Actions → Image and templates → Create image**. Esperar a que la AMI esté *Available* en *AMIs* (L05).
2. *AMIs* → **Launch instance from AMI**, elegir el par de claves existente y SSH desde *My IP* (L05; T13 ~03:30:05-03:33:46).

- En la demo con la pantalla de un alumno se vio la diferencia entre **Create template from instance** (plantilla de lanzamiento) y **Create image** (la AMI directamente); para el ejercicio es la segunda (T13 ~03:26:08-03:27:44). Hay que seleccionar antes la instancia con la casilla de la izquierda (T13 ~03:27:27).
- Problemas vistos: a algunos alumnos los créditos no les aparecían enseguida (tarda en actualizarse, o no se había verificado la tarjeta al crear la cuenta); el *widget* "Explore AWS" a veces hay que añadirlo desde *Widgets* (T13 ~03:14:28-03:19:39).
- **La AMI cuesta:** guarda un snapshot de EBS que se paga mientras exista. Si no la vas a usar, anula su registro y borra el snapshot (L05 «Ejercicio: instancia desde tu AMI»; T13 ~03:35:47-03:36:01).
- La instancia de la actividad es pequeña y el profesor recomendó borrarla y crear otra mayor para SSH y VS Code (T13 ~03:10:27, ~03:47:41).

### 2.10 Rol de IAM en la instancia

**Idea.** Un programa que corre en EC2 no debe llevar claves de acceso: se le asocia un **rol de IAM** y el SDK obtiene credenciales temporales solo (L03 «Autenticación»: "Rol de IAM | EC2, Lambda, ECS | Siempre para servicios"; CAMBIOS: "Credenciales en EC2: claves → rol de IAM").

```text
IAM → Roles → Create role → AWS service → EC2 → política (p. ej. AmazonS3FullAccess) → nombre miax-ec2-s3
EC2 → Instances → Actions → Security → Modify IAM role → elegir el rol
En la instancia: aws s3 ls
```

(L11 «Dar acceso a S3 a EC2».) boto3 y pandas buscan credenciales en este orden: parámetros explícitos, variables de entorno, `~/.aws/`, y por último el rol de la instancia o función (L11 «Credenciales en Python»).

**Nota:** en las clases de T13-T14 esto no se llegó a hacer; se ve con S3. Para la práctica, una política como `AmazonS3FullAccess` es demasiado amplia: lo correcto es limitarla al bucket del proyecto (mínimo privilegio).

### 2.11 User data (contenido propio)

**Nota:** ni la web ni las clases tratan el *user data*; se añade por completitud. En *Advanced details → User data* se puede pegar un script que la instancia ejecuta **una sola vez como root en el primer arranque** (mediante cloud-init). Sirve para no repetir a mano la preparación que en clase se hizo comando a comando:

```bash
#!/bin/bash
dnf install -y git cronie
systemctl enable --now crond
sudo -u ec2-user bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
```

La salida queda en `/var/log/cloud-init-output.log`. No pongas secretos en el *user data*: cualquiera con permiso de lectura sobre la instancia puede verlo. Una AMI propia (§2.9) y el *user data* son las dos formas de no reinstalar; en la práctica, Terraform cumple ese papel para toda la infraestructura.

---

## 3. Conectarse: EC2 Instance Connect, SSH y SCP

### 3.1 EC2 Instance Connect (navegador)

**Idea.** La forma fácil: *Instances → Connect → EC2 Instance Connect → Connect* abre una terminal en el navegador (L05 «Conexión desde el navegador»; T13 ~02:56:16-02:57:18).

- Entra por el puerto 22 **desde los rangos de IP de AWS**: si limitaste el grupo de seguridad a tu IP, no funciona; usa SSH o Session Manager (L05, nota «Si no conecta»). En la demo funcionó porque el 22 estaba abierto a `0.0.0.0/0` (T13 ~02:57:21-02:57:44).
- Es la alternativa si no consigues conectar VS Code: puedes hacer lo mismo, pero editando con `nano` (T14 ~00:29:21-00:30:44).
- En la sesión se crearon y leyeron ficheros (`ls`, `echo "hola" > hola.txt`, `cat hola.txt`) y luego se comprobó desde SSH que seguían ahí: es la misma máquina (T13 ~02:57:49-02:58:20, ~03:40:22-03:40:59).

### 3.2 SSH

**Idea.** `ssh` abre un túnel cifrado entre tu terminal y la instancia autenticándote con la clave privada (L06 «Conectar por SSH»; T13 ~03:36:09-03:43:26).

```bash
ssh -i "miax.pem" ec2-user@IP_PUBLICA     # o el DNS público
exit                                      # o Ctrl+D para salir
```

- `ec2-user` es el usuario por defecto de Amazon Linux; el comando exacto está en *Connect → SSH client* (L06 «Conectar por SSH», «Dónde está el comando»).
- La primera vez SSH pregunta si confías en la huella de la máquina: se responde `yes` (T13 ~03:38:37; T14 ~02:21:44).
- **Para salir, `exit`** (o Ctrl+D). `Ctrl+C` interrumpe un proceso pero no cierra la sesión (T13 ~03:42:31). La versión original del material decía Ctrl+X y está corregido (CAMBIOS, errores corregidos).
- Consejo práctico del profesor: renombrar la clave a algo corto (`miax.pem`), dejarla en la carpeta de trabajo y guardar en un `README.md` los comandos que se van usando (T13 ~03:36:51-03:38:08; ~04:01:09).

**Nota:** el usuario por defecto depende de la AMI: `ec2-user` en Amazon Linux, `ubuntu` en Ubuntu, `admin` en Debian. En T14 un alumno que usaba otra imagen tenía como usuario `admin` en vez de `ec2-user` y el profesor comentó que "es más o menos lo mismo" (T14 ~02:54:25, ~02:56:05).

### 3.3 Permisos de la clave y otros errores vistos en clase

**Idea.** OpenSSH rechaza una clave privada que otros usuarios puedan leer: aparece `WARNING: UNPROTECTED PRIVATE KEY FILE!` y la conexión falla. Hay que dejar la `.pem` solo legible por ti (L06 «Permisos de la clave»).

```bash
# macOS y Linux
chmod 400 miax.pem
```
```powershell
# Windows (PowerShell): quitar la herencia y dar solo lectura a tu usuario
icacls miax.pem /inheritance:r
icacls miax.pem /grant:r "$($env:USERNAME):(R)"
```

Errores reales de los alumnos y cómo se resolvieron:

| Síntoma | Causa | Solución en clase |
|---|---|---|
| `UNPROTECTED PRIVATE KEY FILE` en Windows | La `.pem` hereda permisos de la carpeta | Los dos `icacls` de arriba, cambiando `miax.pem` por el nombre real del fichero; la salida correcta es "se procesaron correctamente 1 archivos; error al procesar 0" (T13 ~04:03:10-04:04:50; T14 ~02:41:49-02:42:53) |
| `Identity file ... not accessible` | El nombre del fichero en el comando no coincidía con el real | Cambiar el nombre en el comando o renombrar el fichero (T13 ~04:05:12-04:05:37) |
| *Timeout* al conectar | El alumno había restringido el 22 a la IP de la zona compartida del móvil; al cambiar de red cambió su IP | Abrir el 22 a *Anywhere*: solo quien tiene la clave puede entrar (T14 ~02:37:16-02:37:58) |
| VS Code no conecta aunque el SSH en terminal sí | Ruta de `IdentityFile` mal escrita (mezcla de rutas Windows/Linux) o entradas duplicadas en el `config` | Pegar la ruta completa con *Copy Path* y borrar entradas repetidas (T14 ~00:40:11-00:41:03) |
| Varios alumnos sin conexión a la vez | Instancias mal configuradas o claves con permisos rotos | Crear una instancia nueva desde cero (c7i-flex, 32 GB, 22 abierto), aplicar `icacls` y probar primero en terminal y después en VS Code (T14 ~02:38:34-02:44:41) |

**Nota:** el profesor describió `chmod 400` como dar "permisos de ejecución de usuario" (T13 ~04:03:13) y dijo al principio que en Windows "no hace falta" porque eres el usuario principal (T13 ~03:41:13). Ambas cosas son imprecisas: `400` deja la clave **solo lectura para el propietario** y nada para los demás, y en Windows el error apareció a la mayoría de los alumnos. Abrir el 22 a todo Internet funciona, pero contradice la recomendación de la web (L05 «Acceso seguro»); es aceptable para una máquina de prácticas efímera, no como costumbre.

### 3.4 SCP: copiar ficheros

**Idea.** `scp` usa el mismo protocolo y la misma clave que SSH para copiar en un sentido u otro; el orden de los argumentos es siempre **origen → destino** (L06 «Copiar ficheros con SCP»; T13 ~03:43:20-03:46:52).

```bash
scp -i miax.pem ./datos.txt ec2-user@IP_PUBLICA:~/            # local → instancia
scp -i miax.pem ec2-user@IP_PUBLICA:~/datos.txt ./            # instancia → local
scp -i miax.pem ec2-user@DNS:~/market_data_proc.csv ./market_data_proc_2.csv   # renombrando
```

- Si no indicas carpeta de destino, el fichero va al *home* del usuario (`~/`) (T13 ~03:44:22).
- Ejercicio de clase: subir `market_data_proc.csv`, editarlo en la instancia con `nano` (cambiar la cabecera `time` por `tiempo`; se guarda con Ctrl+X, confirmar y Enter) y traerlo con otro nombre para comparar (L06 «Ejercicio: transferir ficheros»; T13 ~04:07:15-04:14:37).
- Para qué sirve: dejar corriendo un proceso de 20 horas sin tener el portátil encendido, o usar una máquina mayor unas horas y traerse el resultado. Aun así, el profesor prefiere **pasar los ficheros por un bucket de S3** antes que por SCP (T13 ~03:46:52-03:47:28).
- Con VS Code conectado hay un atajo: clic derecho → *Download* para bajar y arrastrar un fichero al explorador para subirlo (T14 ~00:08:27-00:09:16).

### 3.5 Comandos de Linux que aparecieron

| Comando | Para qué |
|---|---|
| `ls`, `cat`, `clear`, `pwd`, `cd ..` | Listar, leer, limpiar la terminal, ver dónde estás, subir de carpeta |
| `echo "texto" > f.txt` / `>> f.txt` | Sobrescribir / añadir al final (T13 ~03:39:15; T14 ~00:27:06) |
| `nano f.txt` | Editor sencillo de terminal |
| `sudo dnf install -y htop` / `top` | Instalar con permisos de administrador; ver procesos (L06 «Ejercicio: conectar por SSH») |
| `date` | Hora del servidor (UTC) (T14 ~00:11:35) |
| `chmod +x script.sh` | Dar permiso de ejecución (T14 ~00:56:44) |

- `sudo` ejecuta como administrador: **lee bien lo que va detrás** antes de lanzarlo (T13 ~04:29:30-04:29:46).
- El profesor no memoriza comandos y los busca cuando le hacen falta, "sin ningún tipo de vergüenza" (T13 ~04:12:50).

---

## 4. Desarrollo remoto con VS Code (Remote - SSH)

### 4.1 Cómo funciona

**Idea.** La interfaz de VS Code corre en tu ordenador; la extensión **Remote - SSH** instala **VS Code Server** dentro de la instancia, y ficheros, terminales, extensiones y depuración viven allí (L07 «Cómo funciona», «Arquitectura de Remote - SSH»; T13 ~04:14:58-04:16:03, ~04:18:10-04:18:35).

- Con Mac apenas se nota diferencia (también es Unix); desde Windows se pasa a una terminal Linux (T13 ~04:15:00-04:15:28).
- Una máquina de AWS de este tamaño suele ser **más pequeña** que un portátil de 16 GB y 8 núcleos; la ventaja es que no depende de tu equipo y puede quedarse encendida (T13 ~04:16:16-04:16:41). A un alumno con un portátil muy lento el profesor le recomendó programar directamente en la máquina remota (y poner el modo de energía en máximo rendimiento) (T14 ~01:56:30-01:56:41, ~02:27:42-02:27:55).
- La extensión correcta es **Remote - SSH**, verificada por Microsoft; hay otra de nombre casi igual (T13 ~04:16:59). Cursor funciona igual (T14 ~00:04:42, ~02:52:19).

### 4.2 El fichero de configuración SSH

**Idea.** En lugar de recordar el comando `ssh`, se declara cada máquina en un bloque `Host` y VS Code la muestra en *Remote Explorer* (L07 «Configurar VS Code»).

```text
Host aws-ec2
    HostName IP_O_DNS_PUBLICO
    User ec2-user
    IdentityFile C:\ruta\a\miax.pem
```

| Campo | Significado (L07) |
|---|---|
| `Host` | Nombre que tú eliges (en clase, "mi máquina bonita", T13 ~04:21:48) |
| `HostName` | IP o DNS público de la instancia |
| `User` | Usuario de la máquina |
| `IdentityFile` | Ruta a la clave privada |

Pasos: instalar la extensión → F1 → *Remote-SSH: Open SSH Configuration File...* → añadir el bloque → *Remote-SSH: Connect to Host...* → elegir el host y la plataforma **Linux** → *File → Open Folder* `/home/ec2-user` y confiar en la carpeta (L07 «Configurar VS Code»; T13 ~04:19:17-04:23:13).

- En clase se creó un fichero `ssh_config` en la carpeta del curso y se apuntó a él desde la rueda de configuración de Remote Explorer; el profesor aclaró que lo habitual es **un único fichero de configuración** del usuario (`~/.ssh/config`) con todas las máquinas (T13 ~04:20:48-04:21:23; T14 ~00:37:36-00:38:11).
- Alternativa: en Remote Explorer, botón **+**, pegar el comando `ssh -i ... ec2-user@...` y dejar que lo escriba en el `config`. Usa la ruta **completa** de la clave, o la entrada quedará mal (T14 ~00:38:12-00:40:24).
- Para la ruta, clic derecho sobre la `.pem` → *Copy Path* (T13 ~04:20:27).
- Si cambia la instancia y usas la misma clave, solo hay que cambiar `HostName` (T14 ~00:07:22).

### 4.3 Trabajar dentro de la instancia

- La barra de estado muestra `SSH: <host>` cuando estás conectado (T13 ~04:22:41). Un fichero creado desde VS Code aparece al hacer `ls` desde una sesión SSH normal (T13 ~04:23:31-04:24:27).
- **Las extensiones se instalan en el servidor** (en el panel aparecen separadas *Local* y *SSH: host*). Instala allí las que uses a diario, sabiendo que ocupan disco (L07 «Trucos»; T13 ~04:26:15-04:26:19, ~04:31:05-04:31:19).
- **Python de AL2023.** Viene `python3` (3.9), sin el alias `python` y sin `pip`. Para abrir un notebook hubo que instalar `pip` (`sudo dnf install -y python3-pip`; el profesor usó `yum`, que en AL2023 es un alias de `dnf`) y luego `ipykernel` (T13 ~04:25:08-04:29:21). En T14 el selector de *kernel* no mostraba el entorno virtual y se recurrió a la terminal (T14 ~00:50:14-00:50:41).
- Si la extensión no se deja instalar, a veces basta con reintentar; el profesor comentó que en días de partido de fútbol algunos bloqueos de Cloudflare impiden descargas (T13 ~04:37:42-04:38:33) *(anécdota, dudoso que fuera la causa)*.

**Nota:** con IP automática, cada vez que detengas y arranques la instancia tendrás que actualizar `HostName` (ver §2.5). Si la máquina va a durar varios días, una IP elástica ahorra el paso a cambio de 0,005 $/hora.

---

## 5. Tareas programadas con cron

### 5.1 La expresión de cron

**Idea.** Cinco campos indican cuándo se ejecuta un comando: minuto, hora, día del mes, mes y día de la semana; un asterisco significa "todos" (L08 «Crontab»; T13 ~04:39:56-04:41:26).

```text
┌ minuto (0-59)
│ ┌ hora (0-23)
│ │ ┌ día del mes (1-31)
│ │ │ ┌ mes (1-12)
│ │ │ │ ┌ día de la semana (0-6, 0 = domingo)
* * * * *  comando
```

| Expresión | Significado |
|---|---|
| `* * * * *` | Cada minuto, siempre ("hasta que alguien prenda fuego al servidor o te quedes sin crédito", T14 ~00:57:47-00:57:59) |
| `0 8 * * 1-5` | A las 8:00, de lunes a viernes (L08) |
| `5 4 * * *` | Todos los días a las 4:05 (T14 ~00:10:26) |
| `5-10 10 * * 6` | Cada minuto de 10:05 a 10:10, solo los sábados (T14 ~00:15:32-00:16:14) |
| `*/2 * * * 1` | Cada 2 minutos, los lunes (T13 ~04:43:10-04:43:20) |

- Comprueba las expresiones en **crontab.guru**: dice cuándo será la próxima ejecución (L08; T13 ~04:41:26).
- Usos que se citaron: descargar datos cada noche, preparar datos de premercado una o dos horas antes de la apertura y lanzar el algoritmo al abrir, rastrear el consumo eléctrico cada minuto, rotar un fichero de registro cada día, o excluir meses (Navidad, agosto) (T13 ~04:40:44-04:41:14; T14 ~00:10:45-00:11:17, ~00:23:17-00:24:02). Los asistentes que "programan tareas" funcionan con un cron por detrás (T13 ~04:39:02-04:39:31).
- Cron puede retrasarse unos segundos dentro del minuto si hay otros procesos (T14 ~00:25:04-00:25:21).

**Nota:** el profesor dijo que si defines el día del mes "no podrías definir" el de la semana (T13 ~04:41:19). Sí se pueden definir los dos, pero cron los combina con **O**: `0 9 1 * 1` se ejecuta el día 1 de cada mes **y** todos los lunes.

### 5.2 Instalar cron en Amazon Linux 2023

**Idea.** AL2023 **no trae cron**; sin instalarlo, `crontab` da *command not found* (L08 «Instalar cron en AL2023»; CAMBIOS, errores corregidos).

```bash
sudo dnf install -y cronie
sudo systemctl enable --now crond
crontab -e    # editar
crontab -l    # listar
```

- En la demo, tras instalar, `crontab -l` seguía quejándose; no era un fallo de instalación sino que **aún no había ninguna tarea** definida para el usuario. Al abrir `crontab -e` por primera vez se resolvió (T14 ~00:17:07-00:18:46).
- El editor por defecto es **vim**: `i` para editar, `Esc` y `:wq` para guardar y salir (L08 «Editar y listar»; T14 ~00:19:25-00:19:55). Para usar nano: `EDITOR=nano crontab -e` (L08).
- Demo: `29-32 8 * * 6 echo "Hola el sábado por la mañana" >> saludos.txt` escribió una línea por minuto en el intervalo y dejó de escribir al pasar el minuto 32 (T14 ~00:19:55-00:25:34).

**Nota:** en la demo el profesor escribió algo como `nano crontab -e` *(dudoso)* y le apareció un fichero vacío sin la tarea anterior; de ahí su consejo de usar "siempre el mismo editor" (T14 ~00:25:39-00:26:53). Lo que pasa realmente es que `nano crontab` edita un fichero normal llamado `crontab`, no la tabla de cron. La forma correcta de cambiar de editor es la variable `EDITOR` de L08.

### 5.3 Rutas absolutas, entornos virtuales y logs

**Idea.** Cron ejecuta con un `PATH` mínimo, desde el *home* y **sin activar tu entorno virtual**: usa rutas absolutas al intérprete del entorno y al script, y redirige la salida a un fichero de log (L08 «Editar y listar», «Guardar logs»).

```bash
* * * * * /home/ec2-user/proyecto/.venv/bin/python /home/ec2-user/proyecto/mi_algo.py
1 9 * * 1-5 /home/ec2-user/proyecto/.venv/bin/python /home/ec2-user/proyecto/mi_algo.py > /home/ec2-user/proyecto/logs/cron_$(date +\%F_\%H-\%M-\%S).log 2>&1
```

En crontab `%` tiene significado especial y se escribe `\%` (L08 «Guardar logs»).

**El ejercicio de clase** (L08 «Ejercicio»; T14 ~00:41:32-01:02:10):

1. Instalar cron, crear un entorno (`python3 -m venv venv`) y activarlo con `source venv/bin/activate` (en Windows es `Scripts\activate`; con Git Bash en Windows se usa el mismo `source`) (T14 ~00:44:12-00:48:21, ~01:14:29-01:15:30).
2. `pip install pandas` y un `app.py` que imprima `pd.Timestamp.now()`: devolvió una hora menos que la de Madrid porque el servidor está en UTC (T14 ~00:49:27-00:53:04).
3. Un `my_script.sh` que llame a `venv/bin/python app.py`, que es equivalente a activar el entorno y ejecutar. Falló dos veces: primero por una ruta con una carpeta `proyecto` que no existía, después por falta de permisos; se arregló con `chmod +x my_script.sh` (T14 ~00:53:09-00:57:20).
4. `* * * * * /home/ec2-user/my_script.sh > log.txt` en `crontab -e`; al minuto apareció el log. La ruta absoluta se puede sacar con `pwd` o *Copy Path* (T14 ~00:57:29-01:01:25). Media hora después seguía ejecutándose "de manera consistente" (T14 ~01:32:29-01:32:47); para pararlo, borrar la línea con `crontab -e` (T14 ~01:16:49-01:17:10).

**Nota:** con `>` el log se **sobrescribe** en cada ejecución (solo verás la última); con `>>` se acumula. Sin `2>&1`, los errores de Python no llegan al log y el fallo pasa desapercibido. Son los dos olvidos más habituales con cron.

### 5.4 La hora del servidor es UTC

**Idea.** Las instancias están en **UTC**; España está en UTC+1 en invierno y UTC+2 en verano. Programa sabiendo esa diferencia (L08 «Instalar cron en AL2023»; T13 ~04:43:55-04:44:44; T14 ~00:11:17-00:11:56).

- Se puede cambiar la zona horaria del servidor, pero lo importante es que el código sea **consistente**: si todo está en UTC, todo en UTC (T14 ~00:11:56-00:14:05).
- Experiencia del profesor: procesos nocturnos con Brasil (3 h de diferencia), Estados Unidos y Reino Unido; si no lo tienes en cuenta, pierdes o duplicas datos, sobre todo en los **cambios de hora**, cuando un proceso "de apertura" llega tarde (T13 ~04:44:52-04:45:23; T14 ~00:13:18-00:15:15). Hay zonas con desfases de media hora (India) y países que no cambian de hora (T13 ~04:45:25-04:45:53).
- Truco: un recordatorio en el calendario para revisar los procesos el día del cambio de hora (T14 ~00:14:40-00:15:15).
- Cron en EC2 obliga a tener la máquina encendida; "más adelante haremos lo mismo sin servidor, con Lambda y EventBridge Scheduler" (L08 «Ejercicio»; T14 ~01:01:40-01:02:01), que además admite zonas horarias (L14 «Programar con EventBridge Scheduler»).

---

## 6. Variables de entorno

### 6.1 Qué son y cómo se usan en bash

**Idea.** Son variables con nombre que el sistema pasa a cada programa y que cambian su comportamiento sin tocar el código; el uso típico es la configuración y los secretos (L09 «Qué son»; T14 ~01:02:38-01:03:10).

```bash
echo $PATH               # ver una
env                      # ver todas
MI_CASA=76               # solo en esta shell; los programas no la heredan
export MASTER_MIAX=14    # la heredan los programas que lances desde esta shell
```

- Demostración de clase: `export` en una terminal y `echo` en **otra** terminal nueva no devuelve nada, porque la variable vive en la shell donde se creó. Para que esté siempre, se añade la línea `export` a `~/.bashrc`; al abrir otra terminal ya aparece (L09 «En bash»; T14 ~01:05:06-01:09:37).
- También se puede hacer que `~/.bashrc` cargue un fichero `.env` con todas las variables cada vez que se abre una terminal (T14 ~01:10:07-01:10:23).

### 6.2 En Python

```python
import os
api_key = os.environ["API_KEY"]             # obligatoria: falla pronto y con mensaje claro
timeout = os.environ.get("TIMEOUT", "30")   # opcional, con valor por defecto
os.environ["MODO"] = "test"                 # solo para este proceso y sus hijos
```

(L09 «En Python».) En local se suele cargar un `.env` al principio del programa (T14 ~01:09:47-01:10:07).

### 6.3 Secretos: dónde va cada cosa

**Idea.** **Nunca** escribas claves en el código: además de acabar en Git, los asistentes de programación leen el código constantemente; un secreto debe estar donde haga falta permiso para leerlo (T14 ~01:03:17-01:03:51; L09 «Secretos»).

| Dónde | Para qué (L09) |
|---|---|
| Fichero `.env` local (en `.gitignore`) | Desarrollo |
| Variables de Lambda o ECS | Configuración no sensible |
| Secrets Manager o Parameter Store | Secretos en producción (cifrados, acceso con permisos) |
| Secretos de GitHub | Valores del pipeline |

- Una clave publicada debe considerarse comprometida **aunque borres el commit** (L09 «Secretos»).
- En Lambda y ECS las variables se definen desde la consola y están disponibles en cada ejecución; una clave de API de un proveedor de modelos, en cambio, va a un gestor de secretos (T14 ~01:10:35-01:11:56).

---

## 7. Primer API: FastAPI en EC2

### 7.1 La aplicación

**Idea.** FastAPI crea un API REST con un decorador por ruta; los parámetros tipados se leen de la URL y se **validan** solos (L10 «La aplicación»; T14 ~01:17:38-01:19:47).

```python
# app.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/suma")
def suma(a: int, b: int) -> int:
    return a + b
```

- `@app.get` define un *endpoint* de tipo GET (cada vez que abres una página web haces un GET); otros métodos son POST y DELETE (T14 ~01:18:09-01:18:36).
- El ejemplo del repositorio añade `/health`, porque ECS Express comprueba esa ruta (EJ `src/app.py`; CAMBIOS).
- Si pasas `b=abc`, FastAPI responde con un error que indica que `b` debe ser entero, sin escribir código de validación (T14 ~03:04:33-03:05:03).

### 7.2 Arrancarlo con uvicorn

```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

`app:app` = fichero `app.py`, objeto `app`; `--host 0.0.0.0` acepta conexiones desde fuera de la máquina (L10 «Ejercicio»; T14 ~01:20:50-01:21:29). Si el fichero se llama `main.py`, el comando es `uvicorn main:app ...` (T14 ~01:36:32-01:37:04).

- `/docs` abre la documentación interactiva (Swagger) generada sola, donde se puede probar cada *endpoint* con *Try it out → Execute* (T14 ~01:22:16-01:22:56).
- **Error típico en local:** `uvicorn` "no se encuentra". Solución: activar el entorno virtual y `pip install uvicorn`; algunos alumnos lo arrancaron con `fastapi dev` *(dudoso)* (T14 ~01:24:02-01:28:08). El profesor anotó corregirlo en la documentación (T14 ~01:26:20), y la web actual instala `fastapi uvicorn` juntos (L10 «Python actual en la instancia»).
- Para parar el servidor, Ctrl+C (L10, limpieza).

**Nota:** `pip install fastapi` instala solo la librería; el servidor (`uvicorn`) y el comando `fastapi dev` vienen con `pip install "fastapi[standard]"`. Por eso unos alumnos tenían `uvicorn` y otros no.

### 7.3 Anatomía de la URL

```text
http://IP_O_DNS:8080/suma?a=12&b=3
└─┬─┘ └───┬────┘└┬─┘└┬─┘└───┬────┘
protocolo máquina puerto endpoint parámetros (? el primero, & los siguientes)
```

(T14 ~01:29:29-01:31:19.) En local la máquina es `localhost` (127.0.0.1) (T14 ~01:23:29; ~02:59:27).

- Escribe **`http://`** delante: algunos navegadores prueban HTTPS por defecto y el servidor no lo tiene (T14 ~03:02:50-03:03:01).
- También se puede llamar desde terminal: `curl "http://IP:8080/resta?a=10&b=100"` → `-90` (T14 ~01:39:44-01:40:35).

### 7.4 Llevarlo a EC2: el puerto del grupo de seguridad

**Idea.** El API arranca en la instancia pero el navegador "se queda cargando": falta abrir el **puerto 8080** en el grupo de seguridad (L10 «Abrir el puerto»; T14 ~01:37:24-01:38:49).

```text
Security Groups → (el de la instancia) → Edit inbound rules → Add rule
Type: Custom TCP   Port: 8080   Source: My IP (para probar) | Anywhere (para que entre otra persona)
```

- En clase se abrió a *Anywhere* y el profesor pasó el enlace por el chat para que los alumnos usaran su API; además del `/suma` se añadió un `/resta` (T14 ~01:34:32-01:39:44).
- El navegador avisa de "no seguro": no hay HTTPS (T14 ~01:38:51).
- **Al terminar, borra la regla.** Al 22 solo entra quien tiene la clave; al 8080 entra cualquiera, porque el API no tiene autenticación (T14 ~01:41:01-01:41:54).
- En la instancia, el flujo fue: activar el entorno, `pip install fastapi uvicorn`, `pip freeze > requirements.txt`, arrancar con `uvicorn` (T14 ~01:33:27-01:37:04).

### 7.5 Un Python moderno con uv

**Idea.** AL2023 trae Python 3.9, demasiado antiguo para las últimas versiones de muchas librerías; **uv** instala la versión que pidas y crea entornos e instala paquetes mucho más rápido que `pip` (L10 «Python actual en la instancia»; T14 ~01:41:58-01:46:29).

```bash
sudo dnf install -y git
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc                 # o abrir una terminal nueva
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install fastapi uvicorn   # o: uv pip install -r requirements.txt
```

- El profesor lo usa a diario en el trabajo: es "estándar de la industria", mucho más rápido y permite fijar versiones exactas con ficheros de bloqueo para evitar incompatibilidades. Es a Python lo que `npm`/`npx` (`uv`/`uvx`) al desarrollo web (T14 ~01:42:11-01:43:50, ~01:45:56).
- Tras instalarlo, `uv --version` comprueba la instalación; con el entorno nuevo, `python --version` pasa de 3.9 a 3.13 (T14 ~01:44:09-01:45:44).

### 7.6 Ejercicio: de GitHub a EC2

**Idea.** El despliegue "manual" completo: repositorio en GitHub, clonarlo en la instancia, entorno, `requirements.txt`, `.gitignore`, push y arrancar el API en el 8080 (L10 «Ejercicio»; T14 ~02:16:38-02:18:19).

1. Crear un repositorio **público** en GitHub y clonarlo en la instancia (antes, `sudo dnf install -y git`, o `git clone` fallará).
2. Entorno virtual y `requirements.txt` (con `pip freeze > requirements.txt` o con uv).
3. `app.py` con `/suma`; `.venv/` en `.gitignore`; commit y push.
4. `uvicorn app:app --host 0.0.0.0 --port 8080`, regla del 8080 y probar `/docs` y `/suma?a=1&b=2`, también el API de otra persona.

Lo que se vio al corregirlo con la pantalla de un alumno (T14 ~02:47:00-03:07:13):

- Clonar un repositorio público no pide credenciales; **hacer push desde la instancia sí** (GitHub pregunta quién eres) (T14 ~02:49:51-02:50:19).
- `.gitignore`: todo lo que no deba quedar público (entorno virtual, configuración local) (T14 ~02:51:04-02:51:34).
- Moverse a la carpeta del repo con `cd` (comprobar con `pwd`) antes de `pip install -r requirements.txt` y de arrancar el servidor (T14 ~02:56:33-02:57:35).
- Comprobar que de verdad estás en la máquina remota y no en una ventana local del editor (T14 ~02:52:34-02:54:08).
- Probar entradas "raras" (negativos, números enormes, texto): el profesor insistió en romper tus propias API antes de que lo hagan los usuarios, con el ejemplo del cliente que entra en el bar a usar el baño en vez de pedir en la barra (T14 ~03:05:33-03:06:22).

### 7.7 EC2 frente a una plataforma gestionada

Un alumno preguntó por qué no usar un PaaS como Vercel, que se conecta al repositorio y es más cómodo (T13 ~04:33:07-04:37:24). Respuesta del profesor, resumida:

- Para un desarrollador solo o para prototipar, está muy bien, con mejor experiencia de desarrollo.
- Pero si algo se hace viral o sufres un ataque de **"denegación de cartera"** (*denial of wallet*: te hacen gastar hasta arruinarte), un servicio que escala sin límite te puede mandar una factura enorme; una sola máquina simplemente se satura.
- Muchos de esos servicios corren sobre AWS y añaden su margen: si AWS sube un 5 %, a ti te puede llegar bastante más *(la cifra de la transcripción es dudosa)*.
- En el curso se hará algo parecido con GitHub → Lambda, controlando cada pieza.

---

## 8. Para la práctica

**Idea.** En el pipeline KID de la práctica casi nada vive en una EC2, pero casi todo lo aprendido aquí reaparece con otra forma (ENUNCIADO §6, arquitectura de referencia).

| Visto en este bloque | En la práctica B7 |
|---|---|
| FastAPI con `uvicorn` en EC2 y puerto 8080 abierto (§7) | **FastAPI en AWS Lambda con Function URL** (ENUNCIADO §6, capa API). El código de los *endpoints* es el mismo; cambia quién lo sirve. La Function URL da HTTPS sin gestionar puertos ni grupos de seguridad (L14 «Exponer una función por HTTP») |
| `/docs`, validación por tipos, probar entradas raras (§7.1, §7.6) | La API "expone los datos" del KID: los parámetros (p. ej. un ISIN de 12 caracteres) se validan con tipos; un ISIN malformado debe devolver error, no romper la consulta |
| Variables de entorno y `.env` en `.gitignore` (§6) | Configuración sin secretos (nombre del bucket, ARN de la base de datos, región, modelo de Bedrock) en variables de Lambda/ECS; **"sin credenciales en el repositorio"** (ENUNCIADO §5) |
| Rol de IAM en la instancia en vez de claves (§2.10) | Cada pieza con su rol: Lambda del API (leer de la base de datos), script de extracción (S3 y Bedrock), GitHub Actions por **OIDC** (ENUNCIADO §6; L03 «Autenticación») |
| cron en EC2, UTC, rutas absolutas, logs (§5) | La extracción es un **script por lotes** (ENUNCIADO §6); si se automatiza, el equivalente sin servidor es EventBridge Scheduler (L08, L14). Fechar en UTC el momento de descarga de cada KID (ENUNCIADO §4: "cuándo se descargó") |
| `requirements.txt`, uv, versiones fijas (§7.5) | Dependencias reproducibles para empaquetar el API y la app, y para el pipeline de GitHub Actions |
| Coste de IP pública, NAT, AMI, EBS; terminar al acabar (§2.5-§2.9) | Disciplina de limpieza: con Terraform, `destroy` al terminar las pruebas |

**Nota:** algunas inferencias que no están en el material:

- Servir FastAPI en Lambda requiere un adaptador entre el evento de Lambda y la aplicación ASGI (por ejemplo Mangum o AWS Lambda Web Adapter); no se usa `uvicorn` en producción.
- Una EC2 sigue siendo útil en la práctica como **máquina de desarrollo** (scraping lento, pruebas de Bedrock con el rol de la instancia), siempre con el rol limitado al bucket del proyecto y detenida cuando no se use.
- Si se programa el lote (por ejemplo, revisar a diario si una gestora ha publicado un KID nuevo, una de las ampliaciones del ENUNCIADO §4), conviene que sea **idempotente**: el enunciado exige evitar duplicados si un documento se procesa dos veces (ENUNCIADO §4), y un cron mal configurado en UTC puede lanzarlo dos veces el día del cambio de hora (§5.4).
- La regla "los datos y documentos no se exponen públicamente salvo a través de la API y la aplicación" (ENUNCIADO §5) es la versión de la práctica del aviso de §7.4: no dejar puertos ni buckets abiertos "para probar".

---

## 9. Preguntas de repaso

1. **¿Qué diferencia hay entre detener y terminar una instancia, y qué se sigue pagando en cada caso?**
   Detener (*stop*) conserva el EBS y los datos; no se paga cómputo, pero sí el disco (y la IP elástica si la hay). Terminar borra el EBS por defecto y se pierden los datos. Después de terminar, revisa volúmenes e IP elásticas (§2.8).

2. **Has detenido y vuelto a arrancar la instancia y VS Code ya no conecta. ¿Qué ha pasado?**
   La IP pública automática cambia al arrancar, y con ella el DNS público derivado. Hay que actualizar `HostName` en el `config` o usar una IP elástica (§2.5, §4.3).

3. **En Windows, `ssh -i miax.pem ...` devuelve `UNPROTECTED PRIVATE KEY FILE`. ¿Cómo se arregla?**
   Restringiendo los permisos de la clave: `icacls miax.pem /inheritance:r` y `icacls miax.pem /grant:r "$($env:USERNAME):(R)"`. En macOS/Linux, `chmod 400` (§3.3).

4. **El API arranca en la instancia con `uvicorn app:app --host 0.0.0.0 --port 8080`, pero el navegador no responde. ¿Qué falta?**
   Una regla de entrada *Custom TCP 8080* en el grupo de seguridad (desde tu IP o desde cualquier sitio), y escribir `http://` en la URL. Al terminar, borrar la regla, porque el API no tiene autenticación (§7.4).

5. **¿Por qué una tarea de cron que funciona a mano falla al programarla?**
   Cron usa un `PATH` mínimo y no activa el entorno virtual: hay que poner rutas absolutas al Python del entorno y al script, darle `chmod +x` si es un `.sh` y redirigir la salida (con `2>&1`) a un log para ver los errores (§5.3).

6. **Quieres que un proceso se ejecute a las 9:00 de Madrid de lunes a viernes en una EC2. ¿Qué escribes?**
   El servidor está en UTC: en invierno `0 8 * * 1-5` y en verano `0 7 * * 1-5`, o bien cambiar la zona horaria del servidor, o usar EventBridge Scheduler, que admite zonas horarias (§5.4).

7. **¿Dónde guardarías la clave de API de un proveedor de modelos para una Lambda en producción?**
   En Secrets Manager o Parameter Store, no en el código ni en una variable de entorno en claro. Las variables de entorno sirven para configuración no sensible y el `.env`, en `.gitignore`, solo para desarrollo (§6.3).

8. **¿Cómo da acceso a S3 un programa que corre en EC2 sin poner claves en ningún sitio?**
   Se asocia a la instancia un rol de IAM con la política necesaria. boto3 y pandas obtienen solos credenciales temporales del rol (§2.10).
