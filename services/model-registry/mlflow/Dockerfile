# FLIP v3.0 — MLflow Tracking Server Dockerfile
# Multi-stage: installs MLflow + boto3 for MinIO artifact storage

FROM python:3.12-slim AS base

WORKDIR /mlflow

RUN pip install --no-cache-dir \
    mlflow==2.14.1 \
    boto3==1.34.144 \
    psycopg2-binary==2.9.9 \
    gunicorn==22.0.0

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM base AS runtime

ENV MLFLOW_TRACKING_URI=http://0.0.0.0:5000
ENV MLFLOW_BACKEND_STORE_URI=postgresql://mlflow:mlflow@postgres:5432/mlflow
ENV MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow-artifacts/
ENV AWS_ACCESS_KEY_ID=minioadmin
ENV AWS_SECRET_ACCESS_KEY=minioadmin
ENV MLFLOW_S3_ENDPOINT_URL=http://minio:9000

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["mlflow", "server", \
     "--host", "0.0.0.0", \
     "--port", "5000", \
     "--backend-store-uri", "${MLFLOW_BACKEND_STORE_URI}", \
     "--default-artifact-root", "${MLFLOW_DEFAULT_ARTIFACT_ROOT}", \
     "--serve-artifacts", \
     "--workers", "2"]
