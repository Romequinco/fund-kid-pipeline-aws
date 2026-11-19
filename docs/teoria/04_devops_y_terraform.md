# DevOps, GitHub Actions y Terraform: del `git push` a la infraestructura

> **Fuentes:**
> - **Fuente principal: la web del curso** (`docs/raw/miax-cloud-main/content/`). Estos temas **aún no se han dado en clase** (las clases del 13/11 y 14/11 llegaron hasta S3); Terraform no aparece en ninguna de las dos transcripciones.
> - **L19** = `19-devops.md` (filosofía DevOps). **L20** = `20-tests.md` (tests y calidad de código). **L21** = `21-actions.md` (GitHub Actions). **L22** = `22-cd-lambda.md` (despliegue continuo de Lambda). **L23** = `23-cd-ecs.md` (despliegue continuo en ECS). **L27** = `27-terraform.md`. Todas leídas completas.
> - **EJ** = `docs/raw/miax-cloud-main/ejemplos/`: `tests/` (`ejemplo_1`, `ejemplo_2`, `requirements.txt`), `github-actions/` (`ci.yml`, `deploy-lambda.yml`, `deploy-ecs.yml`) y `terraform/` (`.gitignore`, `1_bucket` a `5_lambda`, `main.tf` y `versions.tf`).
> - **CAMBIOS** = `docs/raw/miax-cloud-main/CAMBIOS.md` (claves → OIDC, flake8 → Ruff, versiones de las actions y del proveedor, `use_lockfile`).
> - **T13**, **T14** = `docs/raw/transcripciones/T13.txt` y `T14.txt`, transcripciones automáticas de las clases del 13/11 y 14/11/2026. Solo anticipos: T13 ~04:36-04:37; T14 ~01:02, ~01:11, ~02:51, ~04:11, ~04:46.
> - **ENUNCIADO** = `docs/raw/transcripciones/enunciado.txt` (práctica B7), §1, §4-§6.
>
> **Convenciones:** "(L22 «Configurar OIDC»)" = lección y título de la diapositiva (cada `---` es una diapositiva). "(EJ github-actions/ci.yml)" = fichero de ejemplo. "(T14 ~04:11)" = hora aproximada en la transcripción, siempre en **paráfrasis** de un texto muy ruidoso; lo que no se entiende bien va marcado *(dudoso)*. **Nota:** = contenido propio (conexiones con la práctica, detalles de GitHub, AWS o Terraform que no están en el curso). `<cuenta>`, `<región>`, `<alias>`, `<organización>` y `<repo>` sustituyen a los valores de cada uno. Los servicios que se despliegan (Lambda, ECR, ECS Express) están en [03_lambda_y_contenedores.md](03_lambda_y_contenedores.md).
>
> Escrito el 19/11/2026.

---

## 1. La filosofía DevOps

### 1.1 El problema

**Idea.** El software solo es un servicio cuando se ejecuta en un servidor, y entregarlo mal produce siempre los mismos síntomas: errores que llegan a producción, fallos difíciles de diagnosticar, problemas que solo aparecen en algunos entornos, esperas y culpas cruzadas entre equipos y errores manuales (L19 «El problema»).

- El "muro de la confusión": Desarrollo quiere cambiar rápido y Operaciones quiere estabilidad (L19 «El problema», «El muro entre Dev y Ops»).
- DevOps propone **automatizar y medir** cada paso: planificar → código → build → test → publicar → desplegar → operar → monitorizar, en bucle (L19 «Qué propone DevOps», «El ciclo DevOps»).
- Resultados: ciclos más cortos, despliegues más frecuentes y fiables, mejor alineación con el negocio (L19). Hay muchas definiciones distintas del término (L19 «Muchas definiciones»).

### 1.2 CI, entrega continua y despliegue continuo

| | Qué hace (L19 «CI/CD») |
|---|---|
| **Integración continua (CI)** | Une el código a menudo y ejecuta build y tests automáticos |
| **Entrega continua** | Deja siempre una versión lista para desplegar |
| **Despliegue continuo** | Lleva cada cambio válido a producción automáticamente |

Prácticas clave: un único repositorio, builds automatizadas, tests automáticos, entornos estables, iteraciones frecuentes, máxima visibilidad y despliegues automáticos (L19 «CI/CD», «Prácticas»).

**Nota:** la diferencia entre entrega y despliegue continuos es si el último paso a producción es manual (un botón o una aprobación) o automático. El curso hace **despliegue continuo**: cada `push` a `main` despliega (§5, §6).

### 1.3 Monolito y microservicios

| | Monolito | Microservicios |
|---|---|---|
| Despliegue | Todo junto | Por servicio |
| Escalado | Toda la aplicación | Solo lo necesario |
| Complejidad | En el código | En la red y la operación |
| Buen punto de partida | Equipos pequeños | Varios equipos independientes |

(L19 «Monolito y microservicios»). Los microservicios no son mejores por defecto: tienen un coste de operación real (L19).

**Nota:** la práctica queda en medio: un único repositorio y un único paquete de lógica (D-0.3 de `docs/DECISIONES.md`), desplegado en dos servicios (API y dashboard) y un proceso de extracción.

### 1.4 El flujo del curso

`git push` → GitHub Actions (tests y linter) → build de la imagen Docker → ECR → Lambda o ECS (L19 «Nuestro flujo de trabajo»; «Del código a producción»).

- El profesor lo anticipó: en lugar de plataformas tipo Vercel, montar "pipelines de trabajo" que lleven el código desde GitHub a una Lambda, algo "muy parecido" aunque Vercel añade seguridad y una experiencia de desarrollo cuidada (T13 ~04:36:29-04:37:13); antes hay que saber ciertas cosas (variables de entorno, secretos) para usar Docker y pipelines en GitHub (T14 ~01:02:13).
- Todo lo que sea código y despliegue de la práctica se verá en los dos talleres (T14 ~04:46:22).

---

## 2. Tests y calidad de código

### 2.1 pytest

**Idea.** Si un código va a estar en servicio mucho tiempo y va a cambiar, necesita tests que avisen cuando algo se rompe; son la red de seguridad que permite automatizar despliegues (L20, portada y «pytest»).

- `pytest` busca ficheros `test_*.py` o `*_test.py` y ejecuta las funciones que empiezan por `test`; una prueba pasa si no lanza excepciones (L20 «pytest»).

```python
import my_module

def test_resta():
    assert my_module.resta(4, 2) == 2
```
(EJ tests/ejemplo_1/test_my_module.py)

- VS Code detecta los tests en la pestaña **Testing**, permite ejecutar uno concreto y depurarlo con puntos de ruptura (L20 «VS Code», «Panel de tests»).

### 2.2 Probar un API

Con FastAPI, `TestClient` hace peticiones a la aplicación sin levantar un servidor; necesita `httpx` instalado (L20 «Probar un API»; EJ tests/requirements.txt):

```python
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_suma():
    r = client.get("/suma", params={"a": 1, "b": 2})
    assert r.status_code == 200 and r.json() == 3
```
(EJ tests/ejemplo_2/test_app.py)

CAMBIOS corrige que el ejemplo original definía dos funciones `suma`.

### 2.3 TDD

Ciclo **rojo → verde → refactor**: escribir un test que falla, el código mínimo que lo pasa y mejorar sin romper (L20 «Desarrollo guiado por tests», «El ciclo de TDD»).

### 2.4 Ruff

[Ruff](https://docs.astral.sh/ruff/) es linter y formateador a la vez, muy rápido; sustituye a flake8 del material original (L20 «Linter y formato: Ruff»; CAMBIOS).

| Comando | Qué hace (L20) |
|---|---|
| `ruff check .` | Busca problemas |
| `ruff check . --fix` | Corrige los automáticos |
| `ruff format .` | Formatea |

**Nota:** en CI conviene `ruff format --check .`, que falla si hay ficheros sin formatear en lugar de reescribirlos; la configuración (longitud de línea, reglas) va en `pyproject.toml`, sección `[tool.ruff]`.

---

## 3. GitHub Actions

### 3.1 Conceptos

**Idea.** Un workflow es un proceso automatizado, escrito en YAML en `.github/workflows/`, que un evento del repositorio lanza en una máquina (L21 «Conceptos»).

| Término | Significado (L21 «Conceptos») |
|---|---|
| **Workflow** | Proceso automatizado definido en YAML |
| **Evento** | Lo que lo inicia: push, pull request, cron o evento externo |
| **Job** | Conjunto de pasos en una misma máquina |
| **Step** | Una tarea: un comando (`run`) o una action (`uses`) |
| **Action** | Bloque reutilizable |
| **Runner** | Máquina de ejecución, de GitHub o propia |

Al terminar, GitHub marca en el commit o en el pull request si todo ha ido bien (L21).

### 3.2 El workflow de CI

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
permissions:
  contents: read
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with: { python-version: "3.14" }
      - run: python -m pip install -r requirements.txt
      - run: ruff check .
      - run: pytest
```
(EJ github-actions/ci.yml, en forma compacta; L21 «Ejemplo»)

- Usar versiones actuales de las actions: las antiguas pierden soporte. CAMBIOS sube `checkout@v2` y `setup-python@v1` a `@v7` y Python 3.6 a 3.14 (L21; CAMBIOS).
- **Permisos**: pedir solo los necesarios con `permissions` (L21). Aquí, leer el repositorio.
- **Pasar valores entre pasos**: escribir en `$GITHUB_OUTPUT` (L21); los workflows de despliegue usan `$GITHUB_ENV` para dejar la variable `IMAGE` disponible en los pasos siguientes (EJ github-actions/deploy-lambda.yml). CAMBIOS sustituye el antiguo `set-output`.

**Nota:** `$GITHUB_OUTPUT` crea una salida del paso (`steps.<id>.outputs.<nombre>`), visible también desde otros jobs si se declara en `outputs`; `$GITHUB_ENV` crea una variable de entorno para el resto del **mismo** job.

- Ejercicio del curso: repositorio con `pytest` y `ruff` en `requirements.txt`, una función con su test, el workflow, `push`, seguir la ejecución en **Actions** y romper un test a propósito (L21 «Ejercicio»).

---

## 4. Credenciales: de las claves a OIDC

### 4.1 Por qué no claves

**Idea.** Para desplegar, el runner de GitHub necesita credenciales de AWS. El material original las guardaba como claves en los secretos del repositorio; el curso actualizado usa **OIDC**: GitHub obtiene credenciales **temporales** de un rol, y no se guarda ninguna clave que pueda filtrarse (L22 «El flujo»; CAMBIOS).

- En clase, el profesor habló de guardar claves de API como **secretos** cifrados y de usar secretos en GitHub, por ejemplo "nuestras credenciales", para desplegar en AWS (T14 ~01:11:19-01:11:56). Es el enfoque del material original; la web del curso lo reemplaza por OIDC para AWS.
- También insistió en no escribir nunca credenciales en el código: hay bots que recorren GitHub buscándolas porque "es dinero gratis" (T14 ~04:11:08-04:11:37). El enunciado lo convierte en regla: "Sin credenciales en el repositorio" (ENUNCIADO §5).
- El `.gitignore` sirve para que no se suban a GitHub el entorno virtual ni los ficheros de configuración local (T14 ~02:51:10).

| | Claves en secretos de GitHub | OIDC |
|---|---|---|
| Qué se guarda en GitHub | Clave de acceso y secreto de un usuario de IAM | Nada secreto: solo el ARN del rol |
| Duración | Hasta que alguien las rote | Credenciales temporales por ejecución |
| Si se filtran | Acceso permanente a la cuenta | Caducan; y solo sirven desde el repositorio autorizado |
| Quién limita el acceso | La política del usuario | La **condición de confianza** del rol (L22 «Rol para GitHub») |
| En el curso | Material original (CAMBIOS) | Versión actual (L22, L23) |

### 4.2 Proveedor de identidad y rol

Pasos del curso (L22 «Configurar OIDC», «Rol para GitHub»):

1. **Proveedor de identidad** en IAM: tipo **OpenID Connect**, URL `https://token.actions.githubusercontent.com`, audiencia `sts.amazonaws.com`. Se crea una vez por cuenta.
2. **Rol** de tipo **Web identity** con ese proveedor y audiencia, rellenando organización, repositorio y, opcionalmente, rama de GitHub.
3. Políticas `AmazonEC2ContainerRegistryPowerUser` y `AWSLambda_FullAccess`; nombre `miax-github-deploy`.

La **condición de confianza** es la que limita el acceso a tu repositorio (L22). **Nota:** el asistente de la consola genera una política como esta:

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::<cuenta>:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
    "StringLike": { "token.actions.githubusercontent.com:sub": "repo:<organización>/<repo>:ref:refs/heads/main" }
  }
}
```

`sub` identifica quién pide el token: con `ref:refs/heads/main` solo los workflows de la rama `main` pueden asumir el rol; un pull request llega como `repo:<organización>/<repo>:pull_request` y quedaría fuera.

### 4.3 En el workflow

```yaml
permissions:
  id-token: write   # necesario para OIDC
  contents: read
...
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: arn:aws:iam::<cuenta>:role/miax-github-deploy
          aws-region: <región>
```
(L22 «El workflow»)

Sin `id-token: write` el runner no puede pedir el token OIDC.

---

## 5. Despliegue continuo de Lambda

**Idea.** Cada `push` a `main` se autentica con OIDC, construye la imagen, la sube a ECR y actualiza la función (L22 «El flujo»).

Pasos del job (EJ github-actions/deploy-lambda.yml; L22 «El workflow»):

| Paso | Qué hace |
|---|---|
| `actions/checkout@v7` | Descarga el repositorio |
| `aws-actions/configure-aws-credentials@v6` | Asume el rol por OIDC |
| `aws-actions/amazon-ecr-login@v2` (con `id: ecr`) | Inicia sesión en ECR; deja el registro en `steps.ecr.outputs.registry` |
| Build and push | `docker build --platform linux/amd64 --provenance=false`, etiqueta `${{ github.sha }}`, `docker push`, y `IMAGE` a `$GITHUB_ENV` |
| Update function | `aws lambda update-function-code --image-uri "$IMAGE"` y `aws lambda wait function-updated` |

- Etiquetar con el SHA del commit hace que cada despliegue sea una imagen distinta y trazable.
- Requisitos previos: repositorio ECR y función creados con una primera imagen manual (L22 «Ejercicio»).
- En un proyecto real: fijar las actions por el hash de un commit y limitar la política a la función y al repositorio concretos (L22, nota).

---

## 6. Despliegue continuo en ECS Express Mode

**Idea.** Mismo patrón que en Lambda, pero el último paso crea o actualiza un servicio de ECS Express con la action oficial (L23 «El paso de despliegue»).

- **Permisos**: al rol `miax-github-deploy` se le añade `AmazonECS_FullAccess` y una política en línea con **`iam:PassRole`** sobre `ecsTaskExecutionRole` y `ecsInfrastructureRoleForExpressServices`, porque el despliegue "entrega" esos roles al servicio (L23 «Permisos»).
- **Paso de despliegue**: `aws-actions/amazon-ecs-deploy-express-service@v1` con `service-name`, `image`, los dos ARN de roles, `container-port` y `health-check-path`; crea el servicio si no existe y lo actualiza si existe (L23).
- El workflow completo tiene dos jobs: `test` (instala dependencias, `pytest`) y `deploy` con `needs: test`, de modo que **no se despliega si fallan los tests** (EJ github-actions/deploy-ecs.yml; L23 «Ejercicio»).
- **Limpieza obligatoria**: borrar el servicio, comprobar los balanceadores y **desactivar el workflow**, o el siguiente `push` volverá a crear el servicio (L23 «Ejercicio», limpieza).

**Nota:** a diferencia de `deploy-lambda.yml`, la imagen de ECS se construye sin `--provenance=false`, porque esa opción solo la exige Lambda.

---

## 7. Terraform

### 7.1 Infraestructura como código

**Idea.** La infraestructura se describe en ficheros de texto versionables que se pueden revisar, repetir y destruir de forma fiable (L27 «Infraestructura como código»).

- Lenguaje **declarativo**: describes el resultado, no los pasos (L27).
- Multiproveedor (AWS, Azure, Google Cloud), con infraestructuras híbridas; un único binario en Go con los mismos comandos en Linux, Windows y macOS (L27).
- Licencia BSL, que no es de código abierto; **OpenTofu** es la alternativa abierta con comandos muy similares (L27).
- Terraform usa un **proveedor** para llamar al API del servicio de destino (L27 «Terraform y los proveedores»).

### 7.2 Ciclo de trabajo

Escribir `.tf` → `init` → `plan` → `apply` → `destroy` (L27 «Ciclo de trabajo», «Write, plan y apply»).

| Comando | Qué hace (L27 «Qué hace cada comando») |
|---|---|
| `init` | Descarga proveedores y módulos en `.terraform`; repetir si cambian |
| `fmt` / `validate` | Formatea / comprueba la sintaxis |
| `plan` | Muestra los cambios sin aplicarlos |
| `apply` | Calcula el plan y lo aplica si lo apruebas |
| `destroy` | Borra todo lo creado, si lo apruebas |

### 7.3 Estructura de un proyecto y forma de un recurso

| Fichero | Contenido (L27 «Estructura de un proyecto») |
|---|---|
| `main.tf` | Recursos principales |
| `variables.tf` | Variables de entrada |
| `outputs.tf` | Valores que se muestran al terminar |
| `*.tfvars` | Valores de las variables |

```hcl
resource "aws_s3_bucket" "datos" {
  bucket = "miax-<alias>-tf"
}
```

`aws_s3_bucket` es el **tipo** y `datos` el **nombre interno** (L27; EJ terraform/1_bucket/main.tf). Los ejemplos ponen el bloque `terraform` y el `provider` en un `versions.tf` aparte, y usan `variable`, `data` (la AMI de Amazon Linux 2023 leída de SSM) y `output` en `2_ec2` (EJ terraform/2_ec2/main.tf).

### 7.4 Proveedor

```hcl
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
provider "aws" { region = "<región>" }
```
(L27 «Proveedor»; EJ terraform/*/versions.tf)

- Sin versión, Terraform usa la más reciente. CAMBIOS sube el proveedor de `~> 4.16` (con `version` dentro de `provider`) a `~> 6.0` en `required_providers`.
- Con `aws login`, hace falta una versión reciente del proveedor o exportar credenciales con `aws configure export-credentials` (L27).

### 7.5 Estado y backend S3

**Idea.** Terraform recuerda qué ha creado en `terraform.tfstate`; sin estado no sabe qué recursos son suyos (L27 «El estado»).

- El estado puede contener secretos: **no se sube a Git** (L27). El `.gitignore` de los ejemplos excluye `.terraform/`, `*.tfstate*`, `*.tfvars` y `.terraform.lock.hcl` (EJ terraform/.gitignore).
- En equipo se guarda en un **backend remoto**:

```hcl
terraform {
  backend "s3" {
    bucket       = "miax-<alias>-tfstate"
    key          = "curso/terraform.tfstate"
    region       = "<región>"
    use_lockfile = true
  }
}
```

- `use_lockfile` bloquea el estado **en el propio S3** para que dos ejecuciones no lo modifiquen a la vez (L27). CAMBIOS: el bloqueo no se trataba en el material original.

**Nota:** antes se necesitaba una tabla de DynamoDB para el bloqueo; `use_lockfile` la hace innecesaria (de ahí `required_version >= 1.10`). El bloque `backend` no admite variables: los valores van literales o con `terraform init -backend-config=...`. Conviene activar el versionado del bucket de estado para poder recuperar un estado anterior.

### 7.6 `-target` y los ejemplos

- Una Lambda o un servicio de ECS de imagen no se pueden crear si la imagen aún no existe en ECR. Los ejemplos lo resuelven en tres pasos: `terraform apply -target=aws_ecr_repository.lambda` (solo el repositorio), subir la imagen con la etiqueta `latest` y después `terraform apply` completo (L27 «Ejercicio»; EJ terraform/5_lambda/main.tf y 4_ecs_express/main.tf, comentarios).
- `4_ecs_express` define el repositorio (`force_delete = true`), los dos roles con sus políticas gestionadas y el recurso `aws_ecs_express_gateway_service` con `depends_on` para que los roles no se borren antes que el servicio; tiene coste por hora (EJ terraform/4_ecs_express/main.tf).
- `5_lambda` define repositorio, rol con `AWSLambdaBasicExecutionRole` y `aws_lambda_function` con `package_type = "Image"` (EJ terraform/5_lambda/main.tf). CAMBIOS corrige que el original usaba un rol sin definir.
- `3_dynamodb` usa `PAY_PER_REQUEST` con clave `VALOR` + `TIME_ID` (EJ terraform/3_dynamodb/main.tf).
- Limpieza: `terraform destroy` en cada ejemplo (L27 «Ejercicio»).

**Nota:** Terraform advierte de que `-target` es para casos excepcionales; si se usa a menudo, suele indicar que hay que separar la configuración en raíces distintas (que es lo que se hace en §8.1).

---

## 8. Para la práctica

**Nota (propuesta).** El enunciado pide definir la infraestructura con Terraform y desplegarla desde GitHub Actions (ENUNCIADO §1, §4), y la referencia es "Terraform + GitHub Actions (OIDC, estado en S3)" (ENUNCIADO §6). La decisión D-5.1 de `docs/DECISIONES.md` fija dos raíces.

### 8.1 Dos raíces de Terraform

| | `infra/bootstrap/` | `infra/main/` |
|---|---|---|
| Qué crea | Bucket del estado (versionado), proveedor OIDC, rol de GitHub y sus permisos | S3 de documentos, Aurora, repositorios ECR, Lambda + Function URL, ECS Express, roles de ejecución |
| Quién lo aplica | Una persona, una vez, desde local con `aws login` | GitHub Actions al hacer `push` a `main` |
| Estado | Local (fuera de Git, §7.5) | Backend S3 con `use_lockfile` |
| Por qué separado | El rol con el que Actions se autentica no puede crearlo el propio Actions | Ciclo normal de cambios |

En `bootstrap`, el proveedor y el rol de §4.2 en HCL:

```hcl
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}
```

y un `aws_iam_role` cuyo `assume_role_policy` (con `jsonencode`, como en EJ terraform/5_lambda/main.tf) contiene el `Principal.Federated` y las condiciones `aud` y `sub` de §4.2.

### 8.2 Permisos del rol de GitHub

- El curso da a su rol ECR, Lambda, ECS y `iam:PassRole` (L22, L23). Para aplicar `main`, el rol además crea roles de IAM, buckets, la base de datos y secretos: necesita bastante más.
- Compensarlo con una condición de confianza estrecha (solo `main` de `<organización>/<repo>`), `iam:PassRole` limitado a los roles del proyecto y, si se quiere, un *environment* de GitHub con aprobación manual antes del `apply`.

### 8.3 Workflows

- **`ci.yml`** (en cada `push` y pull request, sin credenciales de AWS): `ruff check .`, `ruff format --check .`, `pytest`, `terraform fmt -check -recursive infra` y `terraform -chdir=infra/main init -backend=false` seguido de `terraform validate`. Base: EJ github-actions/ci.yml.
- **`deploy.yml`** (`push` a `main`, `needs` del job de tests como en EJ github-actions/deploy-ecs.yml): OIDC (§4.3) → `terraform apply -target` de los repositorios ECR si es la primera vez (§7.6) → build y push de las imágenes de API y dashboard con etiqueta `github.sha` (§5) → `terraform apply -var image_tag=<sha>` de `infra/main`.
- Para instalar Terraform en el runner existe la action `hashicorp/setup-terraform` (no aparece en el curso).

### 8.4 Un único dueño por recurso

Si Terraform declara `image_uri = ...:latest` y el workflow actualiza la función con `update-function-code` (§5), el siguiente `apply` deshace el cambio. Dos salidas coherentes:
- **Terraform manda**: la etiqueta de imagen es una variable y el workflow solo ejecuta `apply` (la opción de §8.3).
- **El workflow manda**: Terraform crea la función y la ignora después (`lifecycle { ignore_changes = [image_uri] }`); el código se despliega como en L22. Para ECS, lo mismo entre `aws_ecs_express_gateway_service` (EJ 4) y la action de L23: elegir uno de los dos.

### 8.5 Tests y coste

- Tests sin AWS: la lógica vive en `src/kid_pipeline/` (D-0.3), así que se prueba con funciones puras y clientes de boto3 sustituidos por dobles; la API con `TestClient` (§2.2); el esquema de extracción validando ejemplos contra el modelo Pydantic. "Añadir tests y validaciones al pipeline de GitHub" puntúa como ampliación (ENUNCIADO §4).
- ECS Express y Aurora tienen coste por hora (D-5.2): un workflow manual (`workflow_dispatch`) con `terraform destroy` evita dejarlos encendidos; recordar desactivar el despliegue automático si no se quiere que el siguiente `push` los recree (L23, limpieza).

---

## 9. Preguntas de repaso

1. **¿Qué diferencia hay entre entrega continua y despliegue continuo?** En la entrega siempre hay una versión lista para desplegar; en el despliegue cada cambio válido llega a producción automáticamente (L19).
2. **¿Qué condición debe cumplir una función para que pytest la ejecute como test?** Estar en un fichero `test_*.py` o `*_test.py` y llamarse `test...`; pasa si no lanza excepciones (L20).
3. **¿Qué es un job y qué es un step?** Un job es un conjunto de pasos en una misma máquina (runner); un step es una tarea concreta, un comando o una action (L21).
4. **¿Por qué OIDC es más seguro que guardar claves en los secretos de GitHub?** Porque no hay ninguna clave permanente que filtrar: GitHub obtiene credenciales temporales de un rol, y la condición de confianza solo lo permite desde el repositorio (y la rama) autorizados (L22; CAMBIOS).
5. **¿Qué permiso del workflow es imprescindible para OIDC?** `id-token: write` (L22).
6. **¿Para qué necesita el rol de despliegue `iam:PassRole` en ECS Express?** Para entregar al servicio los roles `ecsTaskExecutionRole` y `ecsInfrastructureRoleForExpressServices` (L23).
7. **¿Por qué no se sube `terraform.tfstate` a Git y qué hace `use_lockfile`?** Puede contener secretos; en equipo va a un backend S3, y `use_lockfile` bloquea el estado en el propio S3 para que dos ejecuciones no lo cambien a la vez (L27).
8. **¿Para qué se usa `-target` en los ejemplos de Lambda y ECS?** Para crear primero solo el repositorio ECR, subir la imagen y luego aplicar el resto, porque la función o el servicio necesitan que la imagen exista (L27; EJ terraform/5_lambda/main.tf).
