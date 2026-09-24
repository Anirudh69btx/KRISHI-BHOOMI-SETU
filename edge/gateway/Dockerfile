# FLIP Edge Gateway Container for Raspberry Pi Zero 2W (ARM64)
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies: Mosquitto, ALSA, libgpiod, SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    mosquitto \
    mosquitto-clients \
    alsa-utils \
    libasound2-dev \
    sqlite3 \
    iputils-ping \
    wireless-tools \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy gateway source code, models, audio, and configuration
COPY . .

# Environment configuration
ENV GATEWAY_CONFIG=/app/config/gateway.yaml
ENV PYTHONUNBUFFERED=1

EXPOSE 1883

ENTRYPOINT ["python", "gateway.py"]
