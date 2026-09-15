FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pydantic cwltool

COPY . /app

EXPOSE 8016

CMD ["python", "-m", "uvicorn", "app:app", "--app-dir", "geospatial-2026/geospatial-processes-kernel/service", "--host", "0.0.0.0", "--port", "8016"]
