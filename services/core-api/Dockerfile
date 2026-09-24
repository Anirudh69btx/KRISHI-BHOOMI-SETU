FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build stage
FROM base AS builder

RUN pip install --upgrade pip hatchling

COPY pyproject.toml ./
RUN pip install --prefix=/install .[dev] 2>/dev/null || pip install --prefix=/install .

COPY src/ src/

# Runtime stage
FROM base AS runtime

COPY --from=builder /install /usr/local
COPY --from=builder /app/src /app/src

# OTEL / Prometheus
ENV OTEL_SERVICE_NAME=flip-core-api \
    OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "flip_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# Dev stage (with reload)
FROM runtime AS dev
CMD ["uvicorn", "flip_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]
