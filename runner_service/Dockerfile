FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/skilltrial SKILLTRIAL_ENV=production SKILLTRIAL_DATA=/tmp/runner-state RUNNER_MODE=docker
WORKDIR /opt/skilltrial
RUN apt-get update && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*
COPY runner_service/requirements.txt runner_service/requirements.txt
RUN pip install --no-cache-dir -r runner_service/requirements.txt
COPY backend/app backend/app
COPY runner_service runner_service
EXPOSE 8080
CMD ["uvicorn", "runner_service.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log"]
