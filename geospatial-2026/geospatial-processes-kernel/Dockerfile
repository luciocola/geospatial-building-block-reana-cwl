FROM python:3.11.13-slim-bookworm

WORKDIR /app

COPY geospatial-2026/geospatial-processes-kernel/requirements.lock.txt /tmp/requirements.lock.txt
RUN pip install --no-cache-dir --requirement /tmp/requirements.lock.txt

COPY . /app

EXPOSE 8016

CMD ["python", "-m", "uvicorn", "app:app", "--app-dir", "geospatial-2026/geospatial-processes-kernel/service", "--host", "0.0.0.0", "--port", "8016"]
