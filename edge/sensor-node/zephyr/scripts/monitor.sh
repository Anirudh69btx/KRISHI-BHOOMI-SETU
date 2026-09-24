#!/usr/bin/env bash
# FLIP Sensor Node Serial Monitor
set -e

PORT="${1:-/dev/ttyUSB0}"
BAUD="${2:-115200}"

echo "=== Connecting to FLIP Sensor Node on ${PORT} @ ${BAUD} baud ==="
if command -v west &> /dev/null; then
    west monitor --esp-device "${PORT}" --esp-baud-rate "${BAUD}"
elif command -v picocom &> /dev/null; then
    picocom -b "${BAUD}" "${PORT}"
elif command -v minicom &> /dev/null; then
    minicom -b "${BAUD}" -D "${PORT}"
else
    python3 -m serial.tools.miniterm "${PORT}" "${BAUD}"
fi
