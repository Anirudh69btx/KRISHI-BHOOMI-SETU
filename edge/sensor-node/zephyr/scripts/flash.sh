#!/usr/bin/env bash
# FLIP Sensor Node Flashing Script
set -e

PORT="${1:-/dev/ttyUSB0}"
BAUD="${2:-921600}"

echo "=== Flashing FLIP Sensor Node Firmware to ${PORT} ==="
if command -v west &> /dev/null; then
    west flash --esp-device "${PORT}" --esp-baud-rate "${BAUD}"
elif command -v esptool.py &> /dev/null; then
    esptool.py --port "${PORT}" --baud "${BAUD}" --chip esp32c3 write_flash \
        0x0000 build/zephyr/zephyr.bin
else
    echo "Error: Neither 'west' nor 'esptool.py' found in PATH."
    exit 1
fi

echo "✅ Firmware flashed successfully!"
