#!/usr/bin/env bash
# Signs build artifact using cosign and root private key
set -e

ARTIFACT="$1"
KEY="${2:-../cosign.key}"

if [ -z "$ARTIFACT" ] || [ ! -f "$ARTIFACT" ]; then
    echo "Usage: ./sign_artifact.sh <artifact_file> [cosign.key]"
    exit 1
fi

echo "=== Signing Artifact: $ARTIFACT with Cosign ==="
if command -v cosign &> /dev/null; then
    cosign sign-blob --key "$KEY" --tlog-upload=false --output-signature "${ARTIFACT}.sig" "$ARTIFACT"
else
    echo "Simulating signature generation..."
    openssl dgst -sha256 -sign "$KEY" -out "${ARTIFACT}.sig" "$ARTIFACT"
fi

echo "✅ Signature written to ${ARTIFACT}.sig"
