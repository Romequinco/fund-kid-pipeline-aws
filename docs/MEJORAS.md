# Mejoras pendientes

Lista de extras propuestos el 26/11/2026, por orden de valor para la nota y la demo. Cuando se haga uno, se anota su
decisión en [DECISIONES.md](DECISIONES.md) y se marca aquí.

## Coste (urgente: presupuesto de 14 $ al mes)

- [x] **Apagar el cuadro de mando cuando no se use.** Hecho con D-4.3. ECS Express cobra las 24 horas, entre o no alguien: unos
  2,7 $ al día (unos 80 $ al mes). Se apaga con `desplegar_dashboard=false` y se enciende el día antes de la
  exposición y mientras el profesor corrija. Ver el desglose en [Costes](#costes-estimados-con-precios-de-parís).
- [x] **Alternativa barata para tenerlo siempre encendido:** elegido stlite en S3 + CloudFront (~0 $), D-4.3. Opción descartada: Streamlit en una EC2 `t4g.micro` con systemd, como en la
  lección 11b del curso, por unos 11 $ al mes en lugar de 80. El enunciado lo permite («otra forma de despliegue»).
- [x] **Política de ciclo de vida en ECR:** conservar solo las últimas 3 imágenes. Cada push añade unos 650 MB
  (0,10 $/GB al mes).

## Extras para la nota (ampliaciones del enunciado)

1. [ ] **Interfaz de Streamlit cuidada**, en varias páginas:
   - **Explorador:** filtros por gestora, SRI, gastos y periodo; tabla ordenable y gráfico de gastos frente a riesgo.
   - **Ficha de cada fondo:** los 10 campos del KID, cada uno con su evidencia literal y su marca de verificado, y el
     enlace al PDF original de la gestora.
   - **Comparador:** de 2 a 4 clases lado a lado.
   - **Calidad de la extracción:** Kimi frente a Nova frente a las reglas, y las evidencias verificadas.
   - **Además:** tema visual propio y portada con las cifras clave.
2. [ ] **Buscador en lenguaje natural** (ampliación del enunciado). Por ejemplo, «renta variable con SRI ≤ 4 y gastos
   < 1 %»: Kimi lo convierte en filtros con salida estructurada y la API los aplica. Cuesta céntimos por pregunta.
3. [ ] **Alertas por correo cuando cambia un KID** (ampliación del enunciado). Ya detectamos KID nuevos, cambiados y
   desaparecidos (D-1.6); falta publicarlo en SNS al final del lote semanal.
4. [ ] **Mejoras de la API**, lo que necesiten 1 y 2:
   - Filtros por gastos y periodo, ordenación y paginación.
   - `/comparar?isin=…`, `/fondos/{isin}/evidencias` y `/buscar`.
   - Ejemplos en `/docs`.
5. [ ] **Permisos mínimos del rol de GitHub** (D-5.3): el curso lo pide «para nota». Hay que probarlo bien para no
   romper el despliegue.
6. [ ] Extracción por eventos (S3 → Lambda): ampliación del enunciado, pero el lote semanal ya cubre el caso. Prioridad
   baja.
7. [x] ~~Playwright~~: descartado. Las tres webs sirven el enlace al KID en el HTML, sin JavaScript (06 §3.5).

## Compartir con el grupo

- [ ] **GitHub:** añadir a los dos compañeros como colaboradores del repositorio. Así pueden hacer push, y el despliegue
  funciona igual para ellos: entra en AWS por OIDC y no necesitan credenciales.
- [ ] **AWS:** un usuario IAM por compañero, con consola y MFA, en un grupo `equipo`. Pueden ver S3, la base de datos y
  Bedrock y ejecutar `aws login` en su ordenador.
- [ ] **Datos locales que no están en Git** (`data/`: referencia revisada, extracciones, Markdown):
  - Subirlos al bucket con un prefijo `compartido/`.
  - Cada compañero los baja con `aws s3 sync s3://fund-kid-orq-documentos/compartido data/` tras `aws login`.
  - Los PDF y los manifiestos ya están en el bucket.

## Costes estimados (con precios de París)

Precios oficiales de la API de precios de AWS, consultados el 26/11/2026. Cost Explorer tarda unas 24 horas en
mostrarlos.

| Recurso | Cálculo | Al día | Al mes |
|---|---|---:|---:|
| Contenedor del cuadro de mando (Fargate, 1 vCPU y 2 GB) | ~0,048 $/vCPU-h + 0,0053 $/GB-h, las 24 h | ~1,40 $ | ~42 $ |
| Balanceador HTTPS (ALB) | 0,0265 $/h + LCU | ~0,80 $ | ~24 $ |
| IP públicas (4: 3 del balanceador y 1 de la tarea) | 0,005 $/h cada una | 0,48 $ | ~14 $ |
| **Subtotal: cuadro de mando encendido** | | **~2,7 $** | **~80 $** |
| Aurora Serverless v2 | Se pausa sola sin uso; solo cobra minutos de ACU al consultar, más el almacenamiento | céntimos | < 1 $ |
| Secreto de la base de datos (Secrets Manager) | 0,40 $/mes | 0,01 $ | 0,40 $ |
| ECR (imágenes) | ~1,9 GB hoy, creciendo con cada push | 0,01 $ | ~0,20 $ y subiendo |
| Lambda (API), S3 y lote semanal | Por uso; minutos de Actions gratis en un repositorio público | ~0 $ | < 0,50 $ |
| Bedrock (Kimi) | Solo al extraer KID nuevos (~0,05 $ por KID) | 0 $ | según novedades |
| **Total con el cuadro de mando apagado** | | **~0,03 $** | **~1-2 $** |

Gasto puntual ya hecho: unos 3,5 $ de Kimi al extraer los 68 KID el 26/11/2026.
