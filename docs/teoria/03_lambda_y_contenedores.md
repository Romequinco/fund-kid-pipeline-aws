# Lambda y contenedores: cómputo sin servidores que administrar

> **Fuentes:**
> - **Fuente principal: la web del curso** (`docs/raw/miax-cloud-main/content/`). Estos temas **aún no se han dado en clase**: las clases del 13/11 y 14/11 llegaron hasta S3, así que casi todo sale de las lecciones y los ejemplos, no de la explicación del profesor.
> - **L12** = `12-lambda.md` (primeros pasos con Lambda). **L13** = `13-lambda-paquetes.md` (empaquetado y buenas prácticas). **L14** = `14-lambda-triggers.md` (disparadores). **L15a** = `15a-docker-local.md` (Docker en tu ordenador). **L15** = `15-docker-ec2.md` (Docker en EC2). **L16** = `16-ecr.md`. **L17** = `17-ecs-express.md`. **L18** = `18-lambda-docker.md`. **L29** = `29-alb-apigw.md` (balanceadores y API Gateway). **L30** = `30-docker-basico.md` (cómo usar Docker). Todas leídas completas.
> - **EJ** = `docs/raw/miax-cloud-main/ejemplos/`: `api-suma/` (Dockerfile, `commands.sh`, `src/app.py`, `requirements.txt`), `lambda-docker/` (Dockerfile, `app.py`), `terraform/4_ecs_express/main.tf` y `terraform/5_lambda/main.tf`.
> - **CAMBIOS** = `docs/raw/miax-cloud-main/CAMBIOS.md` (qué se actualizó respecto a la presentación original).
> - **T13**, **T14** = `docs/raw/transcripciones/T13.txt` y `T14.txt`, transcripciones automáticas de las clases del 13/11 y 14/11/2026. Solo anticipos sueltos del profesor: T13 ~00:12, ~00:29-00:34, ~01:08, ~01:50, ~04:34-04:37, ~04:42; T14 ~00:48, ~01:01-01:02, ~01:07-01:11, ~01:41, ~04:47.
> - **ENUNCIADO** = `docs/raw/transcripciones/enunciado.txt` (práctica B7), §4-§6.
>
> **Convenciones:** "(L13 «Zip con dependencias»)" = lección y título de la diapositiva (cada `---` del fichero es una diapositiva). "(EJ api-suma/Dockerfile)" = fichero de ejemplo. "(T14 ~01:01)" = hora aproximada en la transcripción; lo que viene de ellas es **paráfrasis** de un texto muy ruidoso ("landa" = Lambda), y lo que no se entiende bien va marcado *(dudoso)*. **Nota:** = contenido propio (conexiones con la práctica, detalles de AWS que no están en el curso), no del material de clase. En los comandos, `<cuenta>`, `<región>` y `<alias>` sustituyen al ID de cuenta, la región y el alias de cada uno. Lo que viene después (CI/CD, OIDC y Terraform) está en [04_devops_y_terraform.md](04_devops_y_terraform.md).
>
> Escrito el 19/11/2026.

---

## 1. El mapa: dónde se ejecuta el código

**Idea.** El curso recorre tres formas de ejecutar código en AWS, de más a menos administración: una máquina (EC2), un contenedor gestionado (ECS Express Mode) y una función (Lambda). En la práctica conviven las dos últimas: la API en Lambda y el dashboard en ECS (ENUNCIADO §6).

- En clase se presentó el recorrido "de arriba abajo": primero EC2 (lo más duro, IaaS), después S3 y Lambda, para ir viendo "lo bonito" de los servicios gestionados (T13 ~00:34:59-00:35:06). En PaaS "subimos nuestra imagen de Docker" o "nuestro codiguito" y nos olvidamos del sistema operativo (T13 ~00:29:24, ~00:34:23).
- Al repasar el temario, el profesor resumió el foco del curso en servidores (EC2), contenedores y funciones "sin preocuparnos mucho del resto" (T14 ~00:00:51).

**Nota (comparativa propia, con datos del curso donde se indica):**

| | EC2 | ECS Express Mode | Lambda |
|---|---|---|---|
| Qué subes | Nada: entras por SSH e instalas | Una imagen en ECR (L17 «Qué crea») | Un zip o una imagen (L13 «Dos formatos») |
| Quién gestiona el SO | Tú | AWS (Fargate) | AWS (L12 «Qué es Lambda») |
| Coste | Por hora, aunque esté ociosa | Por hora: Fargate + balanceador + IP, ~2-3 $/día (L17 «Qué crea») | Por petición y tiempo × memoria; nivel gratuito mensual permanente (L12) |
| Duración máxima | Ilimitada | Ilimitada (servicio siempre encendido) | 15 min (L12) |
| Escalado | Manual | Autoescalado incluido (L17) | Automático por concurrencia (L12 «Cómo escala») |
| Encaja con | Desarrollo, cron, procesos largos | Aplicaciones web con estado o conexiones largas | Peticiones cortas, eventos, tareas programadas |

---

## 2. Lambda: el modelo sin servidor

### 2.1 Qué es

**Idea.** Subes una función y AWS se ocupa de servidores, sistema operativo, escalado y logs; solo te preocupas del código, y Lambda reparte memoria, CPU y red (L12 «Qué es Lambda»).

- Se paga por petición y por tiempo de ejecución en función de la memoria, con un nivel gratuito mensual permanente (L12 «Qué es Lambda»). En clase se mencionó al enseñar la capa gratuita: Lambda da un número de peticiones gratis al mes (T13 ~01:08:15).
- Se gestiona desde la consola (con editor), la CLI o el AWS Toolkit de VS Code (L12).
- Runtime del curso: **Python 3.14** (3.13 también vale; 3.10 y anteriores sin soporte) (L12). CAMBIOS lo actualiza desde 3.8/3.9.
- Casos de uso: procesar un CSV al llegar a S3, backend de una petición HTTP y procesos periódicos sin máquina encendida (L12 «Casos de uso»). El profesor lo anticipó así: ejecutar "pedacitos de Python" a una hora o cuando entra un fichero (T13 ~04:42:50), y comparó Lambda con plataformas tipo Vercel: se puede hacer "exactamente lo mismo", con más configuración pero más barato (T13 ~04:33:50-04:34:24).
- "Event Functions" es lo que usa el curso; las nuevas "Web Functions" son servidores HTTP y por ahora solo admiten Node.js (L12 «Casos de uso»).

### 2.2 Vocabulario y flujo

| Término | Significado (L12 «Vocabulario») |
|---|---|
| Función | Código + configuración |
| Trigger | Lo que la invoca (S3, cron, HTTP) |
| Evento | JSON con los datos de la invocación; cada servicio tiene su estructura |
| Controlador (*handler*) | Método que Lambda ejecuta |
| Rol de ejecución | Permisos de la función |

Flujo: trigger → evento JSON → función → logs en CloudWatch (L12 «Vocabulario»).

### 2.3 El controlador y el objeto `context`

**Idea.** Lambda llama a una función Python con dos argumentos; lo que devuelve vuelve a quien llamó (L12 «El controlador»).

```python
def lambda_handler(event, context):
    print("Recibido:", event)
    return {"mensaje": "Hola"}
```

- El handler se configura como `fichero.función` (`lambda_function.lambda_handler`).
- `event` suele ser un `dict`; `context` describe la ejecución.
- `print` y `logging` acaban en CloudWatch.
- El retorno debe ser serializable con `json.dumps`; sin `return` devuelve `null` en una invocación síncrona.
- Tras devolver, el entorno queda libre para el siguiente evento (L12 «El controlador»).

`context` expone nombre y versión, ARN invocado, memoria asignada, `aws_request_id`, grupo y stream de logs, y `get_remaining_time_in_millis()` (tiempo hasta el timeout) (L12 «El objeto context»).

**Nota:** `get_remaining_time_in_millis()` es útil en la extracción: antes de lanzar otra llamada a Bedrock se puede comprobar si queda tiempo y, si no, terminar limpiamente.

### 2.4 Escalado, arranque en frío y logs

- Cada invocación simultánea usa un **entorno de ejecución** propio; si llegan más peticiones se crean más, hasta el límite de concurrencia (con un límite de ráfaga previo) (L12 «Cómo escala», «Escalado y límite de concurrencia»).
- Un entorno nuevo tarda en arrancar: **arranque en frío**. Los entornos se reutilizan y lo definido **fuera** del controlador se conserva; los inactivos se eliminan. También se factura la inicialización (L12 «Cómo escala»).
- Cada función tiene un **grupo de logs** con un **stream por entorno**; Lambda escribe inicio, fin y la línea `REPORT` (duración y memoria usada) de cada invocación (L12 «Logs», «Probar la función»).
- El código corre con boto3 instalado y con las credenciales del rol de ejecución (L12 «Logs»).
- En la consola, los cambios no se ejecutan hasta pulsar **Deploy**; se pueden guardar hasta 10 eventos de prueba (L12 «Probar la función»).

### 2.5 Límites

| Límite | Valor (L12 «Qué es Lambda») |
|---|---|
| Duración máxima | 15 min |
| Memoria | 128 MB - 10.240 MB |
| `/tmp` | 512 MB - 10 GB |
| Paquete .zip | 50 MB directo, 250 MB descomprimido |
| Imagen de contenedor | 10 GB |

---

## 3. Empaquetado: zip o imagen

### 3.1 Los dos formatos

**Idea.** El código y sus librerías llegan a Lambda en un zip o en una imagen de contenedor; la frontera la marcan el tamaño y las dependencias de sistema (L13 «Dos formatos»; L18 «Ventajas»).

| | Archivo .zip | Imagen de contenedor |
|---|---|---|
| Límite | 50 MB directo, 250 MB descomprimido (L13) | 10 GB (L13, L18) |
| Cuándo | Código y dependencias ligeras (L13) | Dependencias pesadas o de sistema (L13, L18) |
| Cómo se construye | `pip install --platform ... --target` + `zip` (L13) | `Dockerfile` desde `public.ecr.aws/lambda/python` (L18) |
| Dónde vive | Subida directa o bucket S3 (L13) | Repositorio de ECR (L18) |
| Prueba local | Ejecutando el handler a mano | Idéntica al entorno real con el emulador de la imagen base (L18) |

boto3 ya viene en el runtime; AWS recomienda fijar e incluir la versión si dependes de una concreta (L13 «Dos formatos»).

### 3.2 Zip sin y con dependencias

- Sin dependencias (solo librería estándar y boto3): `zip paquete.zip lambda_function.py` y `aws lambda update-function-code --function-name <nombre> --zip-file fileb://paquete.zip`. En Windows, `Compress-Archive` (L13 «Zip sin dependencias»).
- Con dependencias compiladas (pandas): **Lambda corre en Linux**; si se instala en Windows o Mac, o con otro Python, fallan. No hay que empaquetar el entorno virtual sino decirle a pip la plataforma de destino (L13 «Zip con dependencias»; CAMBIOS, errores corregidos):

```bash
pip install --platform manylinux_2_28_x86_64 --target package \
  --implementation cp --python-version 3.14 --only-binary=:all: pandas
cd package && zip -r ../paquete.zip . && cd ..
zip paquete.zip lambda_function.py
```

- La arquitectura de la función debe ser x86_64; para arm64, `manylinux_2_28_aarch64` (L13). CAMBIOS explica que `manylinux2014_x86_64` ya no encuentra pandas ni numpy para 3.14.
- El curso propone construir el paquete en la instancia EC2 conectada a VS Code, para que se haga en Linux (L13 «Ejercicio: función con pandas»).

### 3.3 Paquetes grandes y capas

- Por encima de 50 MB, se sube el zip a S3 y se actualiza con `--s3-bucket` y `--s3-key` (L13 «Paquetes grandes: vía S3»). CAMBIOS corrige el error original de usar `--zip-file s3://...`.
- **Capas**: AWS publica la capa gestionada **AWS SDK for pandas**, que se añade desde **Layers**; así el paquete solo lleva tu código (L13 «Paquetes grandes: vía S3»).
- Por encima de 250 MB descomprimidos, imagen de contenedor (L13).

**Nota:** una capa es un zip aparte que Lambda monta junto a la función; cuenta para el límite de 250 MB descomprimidos y no existe en funciones de imagen (allí todo va dentro de la imagen).

### 3.4 Rol de ejecución, memoria, timeout y variables de entorno

**Idea.** La configuración de la función decide qué puede hacer (rol), cuánto puede tardar (timeout) y con qué recursos (memoria) (L13 «Permisos», «Configuración»).

- Toda función tiene un **rol de ejecución**; el de por defecto solo permite escribir logs. Para S3 u otros servicios se añaden políticas desde **Configuration → Permissions → (rol) → Add permissions** (L13 «Permisos: el rol de ejecución»).
- **Memory**: subirla también aumenta la CPU. **Timeout**: por defecto **3 segundos**; hay que subirlo para procesar ficheros (L13 «Configuración»).
- **Variables de entorno** en **Configuration → Environment variables**, leídas con `os.environ["BUCKET"]` (L13 «Configuración»). El profesor lo anticipó: en Lambda (y en ECS) se definen variables desde la propia interfaz de AWS y quedan disponibles en cada ejecución; para claves de API, mejor un **secreto** cifrado que una variable (T14 ~01:07:07, ~01:10:35-01:11:32).

### 3.5 Buenas prácticas

Según L13 «Buenas prácticas»:
1. Separar el controlador de la lógica de negocio (más fácil de probar).
2. Configuración por variables de entorno.
3. Crear los clientes de boto3 **fuera** del controlador, para reutilizarlos entre invocaciones (§2.4).
4. Paquete pequeño.
5. Permisos mínimos en el rol.

```python
import os
import boto3

s3 = boto3.client("s3")          # se reutiliza entre invocaciones
BUCKET = os.environ["BUCKET"]

def lambda_handler(event, context):
    s3.put_object(Bucket=BUCKET, Key="salida.txt", Body="hola")
    return {"ok": True}
```

---

## 4. Disparadores

**Idea.** Lo que hace útil a una función es qué la invoca. El curso usa tres: un horario (EventBridge Scheduler), un fichero nuevo en S3 y una petición HTTP (L14, portada).

### 4.1 EventBridge Scheduler (cron)

- Servicio para tareas programadas; admite zonas horarias y ejecuciones únicas. Expresiones `rate(1 minute)` o `cron(0 8 ? * MON-FRI *)` (L14 «Programar con EventBridge Scheduler»). CAMBIOS: sustituye a las reglas de EventBridge del material original.
- **El cron de AWS tiene seis campos** (`minuto hora día-mes mes día-semana año`) y uno de los dos campos de día debe ser `?`: no es el crontab de Linux (L14).
- Demo: programación recurrente por frecuencia, ventana flexible desactivada, destino **Lambda Invoke**, rol nuevo creado por el asistente; **borrar la programación** al terminar (L14 «Demo: ejecución periódica»).
- En clase, al ver cron en EC2, el profesor adelantó que Lambda tiene un trigger que es directamente un cron que llama al código subido (T14 ~01:01:40).

### 4.2 S3

- Flujo: fichero nuevo en el bucket de entrada → evento S3 → Lambda → fichero en el bucket de salida (L14 «Reaccionar a ficheros en S3»).
- Del evento interesan `Records[0].s3.bucket.name` y `Records[0].s3.object.key` (L14 «El evento de S3»).
- **Las claves llegan codificadas** (un espacio llega como `+`): hay que decodificarlas con `unquote_plus` (L14; CAMBIOS, errores corregidos).

```python
from urllib.parse import unquote_plus

def lambda_handler(event, context):
    registro = event["Records"][0]["s3"]
    bucket = registro["bucket"]["name"]
    key = unquote_plus(registro["object"]["key"])
```

- **Bucles recursivos**: si la función escribe en el mismo bucket que la dispara, se invoca sin fin (y se factura). Usar **otro bucket**, o un prefijo distinto y filtros (L14, aviso; CAMBIOS). La consola obliga a marcar el aviso de invocación recursiva al crear el disparador (L14 «Demo: disparador S3»).
- Además del disparador, el rol de la función necesita acceso a S3 (L14 «Demo: disparador S3»).

### 4.3 HTTP: Function URL, HTTP API y REST API

| Opción | Cuándo (L14 «Exponer una función por HTTP»; L29 «Amazon API Gateway») |
|---|---|
| **Function URL** | Lo más sencillo: una URL HTTPS para una función |
| **API Gateway HTTP API** | Varias rutas, autorización, dominios; caso general, más simple y barato |
| **API Gateway REST API** | Claves de API, transformaciones, caché |
| WebSocket API | Comunicación bidireccional (L29) |

- El evento de una HTTP API (formato 2.0) trae `rawPath`, `queryStringParameters`, `requestContext.http.method` y `body` (L14). CAMBIOS: el curso pasa de REST API a HTTP API (2.0) y Function URL.
- Para responder a API Gateway, la función devuelve `statusCode`, `headers` y un **`body` que debe ser una cadena** (`json.dumps(...)`); los parámetros llegan como texto (L14 «El API de suma, sin servidor»; CAMBIOS).
- La demo usa **Security: Open** solo para la prueba (L14). La actividad de créditos de AWS (20 $) crea una función con **Function URL**; al terminar hay que borrarla porque su URL puede ser accesible desde Internet (L14 «Ejercicio: web con Lambda»).
- El profesor dijo, al exponer el API de FastAPI en EC2 sin clave, que más adelante se crearían APIs con Lambda "de manera más sencilla" (T14 ~01:41:39-01:41:54).

**Nota (diferencias que no recoge el curso):** una Function URL acepta `AuthType NONE` (pública) o `AWS_IAM` (firmada), usa el mismo formato de evento 2.0 que la HTTP API y respeta el timeout de la función (hasta 15 min); una HTTP API corta la integración a unos 30 s, pero añade rutas, autorizadores, límites de peticiones y dominio propio.

---

## 5. Docker

### 5.1 Imagen, contenedor y registro

**Idea.** Un `Dockerfile` es la receta; `docker build` produce una **imagen** (plantilla de solo lectura) y `docker run` lanza un **contenedor** (un proceso en marcha) (L30 «Imagen y contenedor»).

| Concepto | Qué es (L30) | Analogía (L30) |
|---|---|---|
| Imagen | Sistema de ficheros con código, librerías y comando de arranque | Una clase |
| Contenedor | Una ejecución aislada de una imagen | Un objeto |
| Registro | Almacén de imágenes (Docker Hub, ECR) | Un repositorio de Git |

- Un contenedor lleva todo lo que necesita: funciona igual en el portátil, en EC2, en ECS o en Lambda. Lo que escribe se pierde al borrarlo salvo con volúmenes (L30).
- El profesor lo destacó como una de las cosas más útiles del curso (T13 ~00:29:51) y avisó de que en Windows "seguramente vais a sufrir", mientras que en Linux se instala con un comando (T13 ~01:50:25-01:50:31). Dentro de un contenedor no hace falta entorno virtual: se instalan las dependencias en el Python del propio contenedor (T14 ~00:48:55).

### 5.2 Instalación: local o EC2

- **Docker Desktop** (motor + CLI + interfaz). En Windows usa **WSL 2** (`wsl --install` como administrador, reiniciar, virtualización activada en BIOS/UEFI); en Mac, la versión según el chip; en Linux basta **Docker Engine** y añadir el usuario al grupo `docker` (L15a). El profesor pidió tenerlo instalado para la semana siguiente y señaló el tutorial de WSL (T13 ~00:12:15-00:12:25).
- Licencia: gratuito para uso personal, educativo y empresas pequeñas (L15a «Qué es Docker Desktop»).
- Comprobación: `docker run hello-world` y `docker run -it --rm python:3.14-slim python --version` (L15a «Comprobar la instalación»); la tabla de errores típicos (terminal abierta antes de instalar, motor parado, WSL antiguo, grupo `docker`) está en L15a «Si algo falla».
- **Alternativa en EC2** (Amazon Linux 2023): `dnf install -y docker`, `systemctl enable --now docker`, `usermod -aG docker ec2-user` y volver a entrar (L15 «Instalación en Amazon Linux 2023»). Para acceder al API del contenedor hay que publicar el puerto (`-p 8080:8080`) y abrirlo en el grupo de seguridad (L15 «Ejercicio»). Ya terminada la clase del 14/11, el profesor comentó que se verá cómo crear una imagen de Docker y desplegarla, y que también se puede poner en una EC2 abriendo los puertos adecuados (T14 ~04:47:42-04:47:56) *(dudoso: conversación informal, muy mal transcrita)*.
- **Mac con Apple silicon**: AWS usa x86_64 por defecto; construir con `docker build --platform linux/amd64` (L15a; L16; L30).

### 5.3 El Dockerfile y la caché de capas

```dockerfile
FROM python:3.14-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```
(EJ api-suma/Dockerfile; L30 «El Dockerfile»)

- `FROM`, `WORKDIR`, `COPY` y `RUN` se ejecutan al **construir**; `CMD`, al **arrancar** cada contenedor (L30).
- Cada instrucción es una **capa** que se reutiliza si no cambia: por eso se copia e instala `requirements.txt` **antes** que el código (L30 «Capas y caché»).
- `.dockerignore` evita meter `.venv/`, `.git/`, `.env` o `*.pem` en la imagen (tamaño y secretos) (L30).
- `--host 0.0.0.0` es obligatorio: con `127.0.0.1` el API solo escucharía dentro del contenedor (L30 «Construir y ejecutar tu imagen»).
- El fichero se llama `Dockerfile`, con mayúscula: en Linux importa (L16 «El proyecto»; CAMBIOS). Los comentarios van en su propia línea (L30).

### 5.4 Comandos del día a día

| Comando | Para qué (L30) |
|---|---|
| `docker build -t miax-suma .` | Construir con nombre |
| `docker run --rm -p 8080:8080 -e MODO=test miax-suma` | Ejecutar, publicar puerto, variable de entorno |
| `docker run -d --name api ...` / `--env-file .env` | Segundo plano / variables desde fichero |
| `docker ps`, `docker logs -f api`, `docker exec -it api bash` | Ver, seguir logs, entrar |
| `docker stop`, `docker rm`, `docker rmi`, `docker system prune` | Parar y limpiar |

El curso no usa volúmenes: en AWS los datos van a S3 o a una base de datos (L30 «Variables de entorno y volúmenes»).

---

## 6. Amazon ECR

**Idea.** ECR es el registro privado de imágenes de tu cuenta, integrado con IAM, del que leen Lambda y ECS (L16 «Qué es ECR»).

Ciclo (L16 «Construir y subir»; EJ api-suma/commands.sh):

```bash
aws ecr create-repository --repository-name miax-suma --region <región>
aws ecr get-login-password --region <región> | docker login --username AWS \
  --password-stdin <cuenta>.dkr.ecr.<región>.amazonaws.com
docker build --platform linux/amd64 -t <cuenta>.dkr.ecr.<región>.amazonaws.com/miax-suma:latest .
docker push <cuenta>.dkr.ecr.<región>.amazonaws.com/miax-suma:latest
```

- El nombre completo de la imagen indica a qué registro se sube; con una imagen ya construida se renombra con `docker tag` (L30 «Del ordenador a AWS»).
- El login debe responder `Login Succeeded` y caduca a las 12 horas (L16).
- ECR cobra por GB almacenado: borrar imágenes y repositorios sin uso o añadir una **lifecycle policy** (L16 «Ejercicio», limpieza).

---

## 7. ECS Express Mode

### 7.1 Qué es y por qué sustituye a App Runner

**Idea.** A partir de una imagen de ECR y dos roles, ECS Express Mode crea un servicio web con URL pública HTTPS (L17, portada).

- App Runner está cerrado a clientes nuevos desde el **30/04/2026** y AWS recomienda migrar a ECS Express Mode, que además deja todos los recursos visibles en la cuenta (L17 «Por qué no App Runner»; CAMBIOS).
- Crea un servicio ECS sobre **Fargate**, un **Application Load Balancer** con HTTPS y certificado, autoescalado, logs, alarmas y despliegues *canary*; la URL tiene la forma `servicio.ecs.región.on.aws` (L17 «Qué crea»).

### 7.2 Los dos roles

| Rol | Permite (L17 «Qué crea») |
|---|---|
| `ecsTaskExecutionRole` | Descargar la imagen y escribir logs |
| `ecsInfrastructureRoleForExpressServices` | Crear el balanceador y la red |

En Terraform son dos `aws_iam_role` que confían en `ecs-tasks.amazonaws.com` y `ecs.amazonaws.com`, con las políticas gestionadas `AmazonECSTaskExecutionRolePolicy` y `AmazonECSInfrastructureRoleforExpressGatewayServices` (EJ terraform/4_ecs_express/main.tf). Los roles recién creados tardan alrededor de un minuto en propagarse (L17 «Desde la CLI»).

**Nota:** el rol de ejecución no es el que usa **tu código**. Si el contenedor llama a otros servicios de AWS, necesita un *task role* aparte; el ejemplo del curso no lo define porque el API de suma no llama a nada.

### 7.3 Health check

- El balanceador comprueba una ruta periódicamente; por defecto `/`. El API de suma no la tenía: daría 404 y el despliegue fallaría, por lo que se añade `/health` (L17 «Salud del servicio»; EJ api-suma/src/app.py; CAMBIOS).
- En la consola: **Express mode** → imagen de ECR → roles (o **Create new role**) → *Additional configurations*: nombre, **Container port** 8080, **Health check path** `/health` (L17 «Demo: desde la consola»). Por CLI: `aws ecs create-express-gateway-service` con los ARN de los roles, `--primary-container` (imagen y puerto) y `--health-check-path` (L17 «Desde la CLI»).

### 7.4 Coste y limpieza

- **Sin nivel gratuito propio**: Fargate, balanceador e IP públicas, del orden de **2-3 $ al día** con la configuración por defecto (estimación del curso). Hay que borrarlo al terminar (L17 «Qué crea»).
- Limpieza obligatoria: borrar el servicio (`aws ecs delete-express-gateway-service --service-arn ...`), comprobar que no queda el balanceador y que no hay tareas (L17 «Ejercicio y limpieza»).

---

## 8. Lambda con imagen Docker

**Idea.** Si las dependencias no caben en un zip o necesitan paquetes de sistema, la función se empaqueta como imagen a partir de la imagen base oficial, que ya incluye el cliente del runtime (L18 «Ventajas»).

```dockerfile
FROM public.ecr.aws/lambda/python:3.14
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt --target "${LAMBDA_TASK_ROOT}"
COPY app.py ${LAMBDA_TASK_ROOT}
CMD ["app.handler"]
```
(EJ lambda-docker/Dockerfile; L18 «Los ficheros»)

- Aquí `CMD` no arranca un servidor: indica el handler (`fichero.función`).
- Prueba local: `docker build --platform linux/amd64 --provenance=false -t miax-lambda .`, `docker run --rm -p 9000:8080 miax-lambda` y un `POST` a `http://localhost:9000/2015-03-31/functions/function/invocations` (L18 «Probar en local»).
- `--provenance=false` evita un formato de imagen que Lambda rechaza (L18).
- Despliegue: repositorio ECR, login, `tag` y `push`; crear la función con **Container image** → **Browse images**; tras subir otra imagen, `aws lambda update-function-code --image-uri ...` (L18 «Desplegar»). En Terraform: `package_type = "Image"` e `image_uri` del repositorio, con un rol que confía en `lambda.amazonaws.com` y la política `AWSLambdaBasicExecutionRole` (EJ terraform/5_lambda/main.tf).

**Nota:** una función de imagen apunta a un *digest* concreto; volver a subir `:latest` no la actualiza por sí solo, por eso hace falta `update-function-code` (lo automatiza el workflow de [04_devops_y_terraform.md](04_devops_y_terraform.md) §5).

---

## 9. Anexo: balanceadores y API Gateway

### 9.1 Elastic Load Balancing

**Idea.** Un balanceador reparte el tráfico entre instancias EC2, contenedores, IP o funciones Lambda, en una o varias zonas de disponibilidad (L29 «Elastic Load Balancing»).

| Tipo | Capa | Uso (L29) |
|---|---|---|
| **Application (ALB)** | HTTP y HTTPS | Webs y API; es el que crea ECS Express Mode |
| **Network (NLB)** | TCP y UDP | Latencia muy baja |
| Gateway (GWLB) | Red | Dispositivos virtuales de seguridad |
| Classic | Anterior | No usar en proyectos nuevos (CAMBIOS: el material original usaba Classic) |

- Un ALB puede ser **público** (en subredes públicas, de cara a Internet) o **interno** (entre subredes privadas, delante de una base de datos o un servicio interno) (L29 «Público o interno»).
- En la consola, un balanceador se entiende por sus **Listeners** (qué puerto y protocolo escucha) y sus **Target groups** (a quién reenvía) (L29, demo).

**Nota:** en la práctica no se crea ningún balanceador a mano: el de ECS Express aparece en **Load Balancers** y es lo que hay que comprobar que desaparece al borrar el servicio (§7.4).

### 9.2 Amazon API Gateway

**Idea.** API Gateway crea, publica, supervisa y protege API HTTP sin estado; junto con Lambda forma la parte "de cara a la aplicación" de la arquitectura sin servidor de AWS (L29 «Amazon API Gateway»).

- Flujo: cliente → API Gateway (autorización, límites) → Lambda u otro backend (L29).
- Tipos: **HTTP API** para el caso general, **REST API** si se necesitan claves de API, transformaciones o caché, **WebSocket API** para comunicación bidireccional (L29; §4.3).
- Una HTTP API se organiza en **rutas**, **integraciones** (a qué backend va cada ruta) y **stages** (L29, demo «Explorar»).

---

## 10. Para la práctica

**Nota (propuesta; todo lo que no remite a una lección es contenido propio).** La arquitectura de referencia sitúa la API en "FastAPI en AWS Lambda con Function URL", la visualización en "Streamlit en Amazon ECS Express Mode" y la extracción en un "script por lotes", con la alternativa "Lambda disparada por S3" (ENUNCIADO §6).

### 10.1 API: FastAPI en Lambda con Function URL

- FastAPI es una aplicación ASGI, no un `lambda_handler`; hace falta un **adaptador** que traduzca el evento HTTP 2.0 de la Function URL (§4.3) a una petición ASGI. Dos opciones, ninguna en el curso:

| | Mangum | AWS Lambda Web Adapter |
|---|---|---|
| Qué es | Librería Python: `handler = Mangum(app)` | Extensión que se copia a `/opt/extensions/` en la imagen |
| Arranque | Lambda llama a `main.handler` | La imagen arranca `uvicorn` como en ECS y la extensión le reenvía las peticiones |
| Ventaja | Sencillo; vale con zip o imagen | El mismo `Dockerfile` sirve para local, ECS y Lambda |

- Empaquetado: imagen desde `public.ecr.aws/lambda/python:3.14` (§8) para que coincida con el patrón de CD del curso, o zip con `pip --platform` (§3.2) si las dependencias son ligeras.
- Configuración por variables de entorno (ARN del clúster de Aurora, ARN del secreto, nombre de la base), cliente `rds-data` creado fuera del handler (§3.5) y rol con permisos mínimos sobre la RDS Data API y el secreto.
- Function URL con `AuthType NONE`: es la "API HTTP" del enunciado y cumple la regla de exponer los datos **solo** por la API y la aplicación (ENUNCIADO §5), siempre que la API no sirva los PDF brutos ni permita escribir. Probarla con `TestClient` como el API de suma ([04_devops_y_terraform.md](04_devops_y_terraform.md) §2).
- Si se necesitan varias rutas con autorización o límites de peticiones, la alternativa es API Gateway HTTP API (ENUNCIADO §6; §4.3).

### 10.2 Dashboard: Streamlit en ECS Express Mode

- Imagen propia (como EJ api-suma/Dockerfile) con `CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]` y **Container port** 8501.
- **Health check**: Streamlit no responde en `/health`, pero expone **`/_stcore/health`**; es la ruta a poner en **Health check path** (si no, ocurre lo de L17 «Salud del servicio»).
- La aplicación solo lee de la API (decisión D-4.1 de `docs/DECISIONES.md`): basta una variable de entorno con la URL de la Function URL.
- Coste de 2-3 $/día (§7.4): desplegar para pruebas y la exposición, y destruir el resto del tiempo.
- Streamlit usa WebSocket; el ALB que crea ECS Express lo admite sin configuración adicional.

### 10.3 Extracción: lote o evento

| | Script por lotes (referencia) | Lambda disparada por S3 (ampliación) |
|---|---|---|
| Disparo | A mano o en Actions | Cada PDF nuevo en `kids/` (§4.2) |
| Límite de tiempo | Ninguno | 15 min por PDF; subir el timeout por defecto de 3 s (§2.5, §3.4) |
| Riesgo | Olvidar procesar | Bucle si escribe en el mismo prefijo: escribir en la base de datos, no en el bucket (§4.2) |
| Idempotencia | SHA-256 del PDF (D-1.2) | Igual; S3 puede entregar un evento más de una vez |

- La captura también puede ser una Lambda programada con EventBridge Scheduler (§4.1), lo que encaja con la ampliación "alertas cuando cambia un KID" (ENUNCIADO §4).
- Recordar `unquote_plus` al leer la clave (§4.2).

---

## 11. Preguntas de repaso

1. **¿Por qué hay que crear el cliente de boto3 fuera del handler?** Porque el entorno de ejecución se reutiliza entre invocaciones y lo definido fuera se conserva; se ahorra crearlo en cada petición (L12 «Cómo escala»; L13 «Buenas prácticas»).
2. **Un zip con pandas instalado en Windows falla en Lambda. ¿Por qué y cómo se arregla?** Lambda corre en Linux y las ruedas compiladas son de otra plataforma; se instala con `pip --platform manylinux_2_28_x86_64 --only-binary=:all: --python-version 3.14 --target` (L13).
3. **¿Cuándo pasar de zip a imagen?** Por encima de 250 MB descomprimidos o con dependencias de sistema; la imagen admite 10 GB (L13, L18).
4. **¿Qué dos cuidados exige un disparador S3?** Decodificar la clave con `unquote_plus` y no escribir en el bucket (o prefijo) que dispara la función, para evitar un bucle infinito (L14).
5. **¿Qué devuelve una función detrás de API Gateway?** Un diccionario con `statusCode`, `headers` y `body` como **cadena** (L14).
6. **¿Por qué falla un despliegue en ECS Express si el API no tiene `/health`?** Porque el balanceador comprueba `/` por defecto; si responde 404 lo marca como no sano. Se configura otra ruta (L17); para Streamlit, `/_stcore/health` (**Nota**).
7. **¿Qué diferencia hay entre `ecsTaskExecutionRole` y `ecsInfrastructureRoleForExpressServices`?** El primero descarga la imagen y escribe logs; el segundo crea el balanceador y la red (L17).
8. **¿Para qué sirve `--provenance=false` al construir una imagen de Lambda?** Evita un formato de imagen que Lambda rechaza (L18).
