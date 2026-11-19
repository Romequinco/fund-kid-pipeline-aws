# Imagen de Lambda para la API (D-4.2). Desde la raíz del repo:
#   docker build --platform linux/amd64 --provenance=false -f infra/api.Dockerfile .
FROM public.ecr.aws/lambda/python:3.13

COPY pyproject.toml /tmp/build/
COPY src /tmp/build/src
RUN pip install --no-cache-dir --target "${LAMBDA_TASK_ROOT}" "/tmp/build[api]" \
    && cp /tmp/build/src/api.py "${LAMBDA_TASK_ROOT}/" && rm -rf /tmp/build

CMD ["api.handler"]
