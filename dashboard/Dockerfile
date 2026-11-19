# Imagen del cuadro de mando para ECS Express Mode. Health check: /_stcore/health en el puerto 8501.
#   docker build --platform linux/amd64 -t fund-kid-dashboard dashboard/
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
