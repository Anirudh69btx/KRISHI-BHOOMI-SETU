#!/usr/bin/env bash
# FLIP Gateway Provisioning & Setup Script for Raspberry Pi Zero 2W
set -e

echo "=== Installing FLIP Gateway System Dependencies ==="
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    mosquitto \
    mosquitto-clients \
    sqlite3 \
    alsa-utils \
    libasound2-dev \
    git

# Configure directories
sudo mkdir -p /data /models /etc/flip /var/log/flip
sudo chown -R $USER:$USER /data /models /etc/flip /var/log/flip

# Copy configuration
cp ../config/gateway.yaml /etc/flip/gateway.yaml

# Create virtualenv and install python dependencies
python3 -m venv /opt/flip-venv
/opt/flip-venv/bin/pip install --upgrade pip
/opt/flip-venv/bin/pip install -r ../requirements.txt

# Install Systemd Service
sudo bash -c 'cat <<EOF > /etc/systemd/system/flip-gateway.service
[Unit]
Description=FLIP Edge Gateway Daemon
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/flip/edge/gateway
ExecStart=/opt/flip-venv/bin/python gateway.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable flip-gateway.service

echo "✅ Gateway system installation completed successfully!"
