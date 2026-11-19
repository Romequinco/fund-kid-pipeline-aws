# Glosario

> **Fuentes:** los documentos de esta carpeta, que citan el material de clase original en cada concepto. Aquí solo se remite al documento y la sección (§) donde se explica cada término.
>
> **Convenciones:** términos en orden alfabético dentro de cada bloque. Entre paréntesis, la sigla desarrollada o la traducción. "→" = ver también.
>
> Escrito el 19/11/2026.

---

## 1. Nube y cuenta de AWS

| Término | Definición breve | Dónde |
|---|---|---|
| **AMI** (*Amazon Machine Image*) | Plantilla de disco y configuración desde la que se lanza una instancia EC2 | [01](01_ec2_y_desarrollo_remoto.md) §2.1 |
| **Budgets** (AWS Budgets) | Alertas de gasto por correo al superar un umbral; sustituye a la alarma de CloudWatch del material antiguo | [00](00_fundamentos_aws.md) §3.5 |
| **CloudShell** | Terminal en el navegador, ya autenticada con tu usuario de la consola | [00](00_fundamentos_aws.md) §5.3 |
| **Créditos** | Saldo promocional de las cuentas nuevas (100 $ al alta y hasta otros 100 $ por actividades) | [00](00_fundamentos_aws.md) §3.6 |
| **IaaS / PaaS / SaaS** | Infraestructura, plataforma o software como servicio: cuánto gestiona el proveedor y cuánto tú | [00](00_fundamentos_aws.md) §2.3 |
| **MFA** (*multi-factor authentication*) | Segundo factor (app autenticadora) para el usuario raíz y los usuarios IAM | [00](00_fundamentos_aws.md) §3.2 |
| **Región / zona de disponibilidad** | Región: zona geográfica con su propio precio y servicios. Zona: centro o grupo de centros de datos aislado dentro de ella | [00](00_fundamentos_aws.md) §2.2 |
| **Serverless** | Ejecutar código sin gestionar servidores, pagando por uso (Lambda, Fargate) | [00](00_fundamentos_aws.md) §2.3, [03](03_lambda_y_contenedores.md) §1 |
| **Usuario raíz** | Identidad con la que se crea la cuenta; todos los permisos. Solo para tareas de cuenta | [00](00_fundamentos_aws.md) §3.2 |

## 2. Identidad y seguridad

| Término | Definición breve | Dónde |
|---|---|---|
| **`aws login`** | Inicio de sesión de la CLI con credenciales temporales desde el navegador; sustituye a las claves de `aws configure` | [00](00_fundamentos_aws.md) §5.2 |
| **Condición de confianza** | Parte de la política de un rol que dice **quién** puede asumirlo (p. ej., solo este repositorio de GitHub) | [04](04_devops_y_terraform.md) §4 |
| **Grupo de seguridad** (*security group*) | Cortafuegos con estado de una instancia: qué puertos entran y desde dónde | [01](01_ec2_y_desarrollo_remoto.md) §2.4 |
| **IAM** (*Identity and Access Management*) | Servicio de usuarios, grupos, roles y políticas | [00](00_fundamentos_aws.md) §4 |
| **Mínimo privilegio** | Dar solo los permisos imprescindibles, sobre los recursos concretos | [00](00_fundamentos_aws.md) §4.3 |
| **OIDC** (*OpenID Connect*) | GitHub Actions obtiene credenciales temporales asumiendo un rol, sin guardar claves | [04](04_devops_y_terraform.md) §4 |
| **Par de claves** (*key pair*) | Clave pública en la instancia y privada (`.pem`) en tu equipo, para SSH | [01](01_ec2_y_desarrollo_remoto.md) §2.4, §3 |
| **Política** | Documento JSON que permite o deniega acciones sobre recursos. Un `Deny` explícito gana | [00](00_fundamentos_aws.md) §4.2 |
| **Rol** | Identidad sin contraseña que asume un servicio (EC2, Lambda, ECS) o un tercero (GitHub) y da credenciales temporales | [00](00_fundamentos_aws.md) §4.2 |
| **Rol de ejecución** | Rol que usa una función Lambda o una tarea de ECS para llamar a otros servicios | [03](03_lambda_y_contenedores.md) §3 |
| **Secrets Manager** | Almacén de secretos; RDS guarda ahí la contraseña de la base de datos si se le pide (`manage_master_user_password`) | [06](06_piezas_de_la_practica.md) |

## 3. Red

| Término | Definición breve | Dónde |
|---|---|---|
| **CIDR** | Notación de rangos de IP (`10.0.0.0/16`): el número indica los bits fijos | [00](00_fundamentos_aws.md) §6.1 |
| **Endpoint de puerta de enlace** (*gateway endpoint*) | Acceso privado y gratuito de una VPC a S3 sin salir a internet | [00](00_fundamentos_aws.md) §6.3 |
| **Internet Gateway** | Puerta de la VPC a internet, en ambos sentidos, para las subredes públicas | [00](00_fundamentos_aws.md) §6.2 |
| **IP elástica** | IP pública fija que se conserva al parar la instancia (y se paga mientras exista) | [01](01_ec2_y_desarrollo_remoto.md) §2.5 |
| **NAT Gateway** | Salida a internet para subredes privadas sin permitir conexiones entrantes; tiene coste por hora | [00](00_fundamentos_aws.md) §6.2 |
| **Subred pública / privada** | Pública: con ruta al Internet Gateway. Privada: sin ella | [00](00_fundamentos_aws.md) §6.2 |
| **VPC** (*Virtual Private Cloud*) | Red privada propia dentro de una región | [00](00_fundamentos_aws.md) §6 |

## 4. Cómputo y contenedores

| Término | Definición breve | Dónde |
|---|---|---|
| **cron** | Planificador de tareas de Linux (`minuto hora día mes día_semana`), en UTC en EC2 | [01](01_ec2_y_desarrollo_remoto.md) §5 |
| **Docker / imagen / contenedor** | Imagen: plantilla inmutable construida con un `Dockerfile`. Contenedor: una imagen en ejecución | [03](03_lambda_y_contenedores.md) §5 |
| **EBS** (*Elastic Block Store*) | Disco de bloque de una instancia EC2; se paga aunque esté parada | [01](01_ec2_y_desarrollo_remoto.md) §2.3 |
| **EC2** (*Elastic Compute Cloud*) | Máquinas virtuales | [01](01_ec2_y_desarrollo_remoto.md) |
| **ECR** (*Elastic Container Registry*) | Registro privado de imágenes Docker | [03](03_lambda_y_contenedores.md) §6 |
| **ECS Express Mode** | Despliegue de un contenedor web con URL HTTPS (Fargate + balanceador) a partir de una imagen y dos roles; sustituye a App Runner | [03](03_lambda_y_contenedores.md) §7 |
| **EventBridge Scheduler** | Planificador gestionado que lanza Lambdas u otros destinos con una expresión cron o de ritmo | [03](03_lambda_y_contenedores.md) §4.1 |
| **Fargate** | Ejecución de contenedores sin gestionar servidores | [03](03_lambda_y_contenedores.md) §7 |
| **Function URL** | URL HTTPS propia de una función Lambda, sin API Gateway | [03](03_lambda_y_contenedores.md) §4.3 |
| **Handler** | Función de entrada de una Lambda: `lambda_handler(event, context)` | [03](03_lambda_y_contenedores.md) §2 |
| **Health check** | Ruta que el balanceador consulta para saber si el contenedor está sano (`/health`; en Streamlit, `/_stcore/health`) | [03](03_lambda_y_contenedores.md) §7.3 |
| **Lambda** | Funciones que se ejecutan bajo demanda, con un límite de 15 minutos | [03](03_lambda_y_contenedores.md) §2 |
| **Mangum** | Adaptador que traduce el evento de Lambda a ASGI para servir FastAPI | [03](03_lambda_y_contenedores.md) §10, [D-4.2](../DECISIONES.md) |
| **systemd** | Gestor de servicios de Linux; mantiene viva una app (Streamlit en EC2) y la arranca con la máquina | [02](02_s3_y_streamlit.md) §7 |
| **user data** | Script que una instancia ejecuta en su primer arranque | [01](01_ec2_y_desarrollo_remoto.md) §2.11 |

## 5. Almacenamiento y datos

| Término | Definición breve | Dónde |
|---|---|---|
| **Athena** | SQL sobre ficheros de S3, pagando por datos leídos | [05](05_datos_y_documentos.md) |
| **Aurora Serverless v2** | PostgreSQL o MySQL gestionado que escala en ACU y puede pausarse a 0 | [06](06_piezas_de_la_practica.md) |
| **Bucket / objeto / clave** | Bucket: contenedor con nombre único en todo AWS. Objeto: el fichero y sus metadatos. Clave: su nombre completo (las "carpetas" son prefijos) | [02](02_s3_y_streamlit.md) §2 |
| **Clase de almacenamiento** | Standard, Intelligent-Tiering, Glacier…: precio por GB frente a coste y tiempo de recuperación | [02](02_s3_y_streamlit.md) §4 |
| **DynamoDB** | Base de datos NoSQL clave-valor; clave de partición y de ordenación | [05](05_datos_y_documentos.md) |
| **Idempotencia** | Ejecutar dos veces da el mismo resultado; aquí, `ON CONFLICT` sobre el SHA-256 del PDF | [06](06_piezas_de_la_practica.md), [D-1.2](../DECISIONES.md) |
| **RDS Data API** | API HTTP para lanzar SQL contra Aurora sin driver ni conexión de red a la VPC | [06](06_piezas_de_la_practica.md) |
| **S3** (*Simple Storage Service*) | Almacenamiento de objetos | [02](02_s3_y_streamlit.md) |
| **Textract** | Servicio de AWS que extrae texto, formularios y tablas de PDF e imágenes (OCR) | [05](05_datos_y_documentos.md) |
| **Upsert** | Insertar o, si la clave ya existe, actualizar (`INSERT ... ON CONFLICT DO UPDATE`) | [06](06_piezas_de_la_practica.md) |
| **Versionado** (S3) | Conservar las versiones anteriores de cada objeto | [02](02_s3_y_streamlit.md) §3.4 |

## 6. IA generativa

| Término | Definición breve | Dónde |
|---|---|---|
| **Bedrock** | Servicio de AWS para usar modelos fundacionales (Anthropic, Amazon, Meta, Mistral…) por API | [06](06_piezas_de_la_practica.md) |
| **Converse API** | API unificada de Bedrock para conversar con cualquier modelo, con documentos y herramientas | [06](06_piezas_de_la_practica.md) |
| **Perfil de inferencia** | Identificador (`eu.`, `us.`) que reparte las llamadas entre varias regiones de una zona geográfica | [06](06_piezas_de_la_practica.md) |
| **Salida estructurada** | Respuesta obligada a cumplir un esquema JSON, por formato de respuesta o por uso forzado de una herramienta | [06](06_piezas_de_la_practica.md), [D-2.1](../DECISIONES.md) |
| **Tool use** (uso de herramientas) | El modelo devuelve una llamada a una función con argumentos que cumplen su `inputSchema`; con `toolChoice` se le obliga a usarla | [06](06_piezas_de_la_practica.md) |

## 7. DevOps e infraestructura como código

| Término | Definición breve | Dónde |
|---|---|---|
| **Backend** (Terraform) | Dónde se guarda el estado; aquí, S3 con `use_lockfile` | [04](04_devops_y_terraform.md) §7 |
| **CI / CD** | Integración continua (tests y lint en cada cambio) y despliegue continuo (publicar automáticamente) | [04](04_devops_y_terraform.md) §1 |
| **Estado** (Terraform) | `terraform.tfstate`: lo que Terraform cree que existe. Puede contener secretos y no va a Git | [04](04_devops_y_terraform.md) §7 |
| **GitHub Actions** | CI/CD de GitHub: *workflows* en YAML con *jobs*, *steps* y *runners* | [04](04_devops_y_terraform.md) §3 |
| **IaC** (*infrastructure as code*) | La infraestructura descrita en ficheros versionables y reproducibles | [04](04_devops_y_terraform.md) §7 |
| **`plan` / `apply` / `destroy`** | Previsualizar, aplicar y borrar los cambios de Terraform | [04](04_devops_y_terraform.md) §7 |
| **Proveedor** (Terraform) | Plugin que traduce los recursos a llamadas a la API de una nube (`hashicorp/aws ~> 6.0`) | [04](04_devops_y_terraform.md) §7 |
| **Ruff** | Linter y formateador de Python; sustituye a flake8 | [04](04_devops_y_terraform.md) §2 |
| **`-target`** | Aplicar solo algunos recursos; se usa para crear ECR antes de subir la imagen | [04](04_devops_y_terraform.md) §8 |
| **TDD** | Escribir primero el test y después el código que lo hace pasar | [04](04_devops_y_terraform.md) §2 |

## 8. Fondos y KID

| Término | Definición breve | Dónde |
|---|---|---|
| **Costes de entrada / salida** | Comisión, en %, al suscribir o reembolsar participaciones | [practica_partida](practica_partida.md) §4 |
| **DFI / KIID** | Antiguo documento de datos fundamentales de los UCITS, sustituido por el KID desde 2023 | [practica_partida](practica_partida.md) §4, [06](06_piezas_de_la_practica.md) |
| **Gastos corrientes** | Comisiones de gestión y otros costes de funcionamiento, en % anual | [practica_partida](practica_partida.md) §4 |
| **Gestora / productor** | Sociedad que crea y gestiona el fondo y publica el KID | [practica_partida](practica_partida.md) §4 |
| **ISIN** | Código de 12 caracteres que identifica una clase de un fondo; el último es un dígito de control | [practica_partida](practica_partida.md) §4 |
| **KID** (*Key Information Document*) | Documento de datos fundamentales del Reglamento PRIIPs: unas tres páginas con estructura común | [practica_partida](practica_partida.md) §4, [06](06_piezas_de_la_practica.md) |
| **Periodo de mantenimiento recomendado** | Plazo mínimo sugerido para mantener la inversión, en años | [practica_partida](practica_partida.md) §4 |
| **PRIIPs** | Productos de inversión minorista empaquetados; su reglamento europeo obliga a publicar el KID | [06](06_piezas_de_la_practica.md) |
| **SRI** (*summary risk indicator*) | Indicador resumido de riesgo, de 1 (más bajo) a 7 (más alto) | [practica_partida](practica_partida.md) §4 |
| **UCITS** | Fondos armonizados de la UE (en España, OICVM) | [06](06_piezas_de_la_practica.md) |
| **Web scraping** | Extraer datos de páginas web de forma automatizada; "responsable" = respetar `robots.txt`, identificarse y no saturar | [06](06_piezas_de_la_practica.md), [D-1.1](../DECISIONES.md) |
