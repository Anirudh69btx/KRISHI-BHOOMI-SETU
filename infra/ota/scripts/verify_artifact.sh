#!/usr/bin/env bash
# Verifies artifact integrity and Cosign signature
set -e

ARTIFACT="$1"
SIGNATURE="${2:-${ARTIFACT}.sig}"
PUBKEY="${3:-../cosign.pub}"

if [ -z "$ARTIFACT" ] || [ ! -f "$ARTIFACT" ]; then
    echo "Usage: ./verify_artifact.sh <artifact_file> [signature_file] [public_key]"
    exit 1
fi

echo "=== Verifying Artifact: $ARTIFACT against $PUBKEY ==="
if command -v cosign &> /dev/null; then
    cosign verify-blob --key "$PUBKEY" --signature "$SIGNATURE" "$ARTIFACT"
else
    echo "Simulating signature check using OpenSSL..."
    openssl dgst -sha256 -verify "$PUBKEY" -signature "$SIGNATURE" "$ARTIFACT"
fi

echo "✅ Signature Verified! Artifact is authentic and untampered."
