# Imagen de Lambda para la API. Se construye desde la raíz del repo:
#   docker build --platform linux/amd64 --provenance=false -f api/Dockerfile -t fund-kid-api .
FROM public.ecr.aws/lambda/python:3.13

COPY api/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY src/kid_pipeline ${LAMBDA_TASK_ROOT}/kid_pipeline
COPY api/app.py ${LAMBDA_TASK_ROOT}/

CMD ["app.handler"]
