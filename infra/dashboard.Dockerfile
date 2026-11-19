# Imagen del cuadro de mando para ECS Express Mode. Health check: /_stcore/health en el puerto 8501. Desde la raíz:
#   docker build --platform linux/amd64 -f infra/dashboard.Dockerfile .
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[dashboard]"

EXPOSE 8501
CMD ["streamlit", "run", "src/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
