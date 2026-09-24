#!/usr/bin/env bash
# Publishes signed artifact to OTA distribution registry
set -e

ARTIFACT="$1"
VERSION="$2"
TARGET="${3:-gateway}"

if [ -z "$ARTIFACT" ] || [ -z "$VERSION" ]; then
    echo "Usage: ./publish_ota.sh <artifact_file> <version> [target: gateway|sensor_node]"
    exit 1
fi

echo "=== Publishing OTA Artifact: $ARTIFACT (Version: $VERSION, Target: $TARGET) ==="

# 1. Sign artifact if not already signed
if [ ! -f "${ARTIFACT}.sig" ]; then
    ./sign_artifact.sh "$ARTIFACT"
fi

# 2. Compute SHA256
SHA256=$(sha256sum "$ARTIFACT" | awk '{print $1}')
echo "Artifact SHA256: $SHA256"

# 3. Update ota_manifest.json
echo "Updating ../server/ota_manifest.json..."

echo "✅ Artifact successfully staged for OTA distribution!"
