FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn

COPY . /app

EXPOSE 8015

CMD ["python", "-m", "uvicorn", "app:app", "--app-dir", "geospatial-2026/process-type-register/service", "--host", "0.0.0.0", "--port", "8015"]
