#!/usr/bin/env python3
"""
FLIP Gateway Reference OTA Client
Demonstrates manifest polling, SHA256 integrity, Cosign signature verification,
A/B partition swap staging, and health-check rollback.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ota_client")


class GatewayOTAClient:
    def __init__(self, manifest_path: Path, pubkey_path: Path, current_partition: str = "A"):
        self.manifest_path = Path(manifest_path)
        self.pubkey_path = Path(pubkey_path)
        self.current_partition = current_partition

    def load_public_key(self):
        with open(self.pubkey_path, "rb") as f:
            return serialization.load_pem_public_key(f.read())

    def check_for_updates(self, current_version: str):
        if not self.manifest_path.exists():
            logger.error(f"Manifest not found at {self.manifest_path}")
            return None

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        latest_version = manifest.get("latest_version")
        logger.info(f"Current version: {current_version}, Latest available: {latest_version}")

        if latest_version != current_version:
            return manifest["artifacts"].get("gateway")
        return None

    def verify_artifact(self, artifact_data: bytes, expected_sha256: str, signature_data: bytes) -> bool:
        # 1. Verify SHA-256 Checksum
        computed_hash = hashlib.sha256(artifact_data).hexdigest()
        if computed_hash != expected_sha256:
            logger.error(f"SHA-256 checksum mismatch! Expected: {expected_sha256}, Got: {computed_hash}")
            return False
        logger.info("✅ SHA-256 checksum verified.")

        # 2. Verify ECDSA Signature
        pubkey = self.load_public_key()
        try:
            pubkey.verify(signature_data, artifact_data, ec.ECDSA(hashes.SHA256()))
            logger.info("✅ Cryptographic ECDSA / Cosign signature verified successfully.")
            return True
        except InvalidSignature:
            logger.error("❌ Invalid cryptographic signature! Image rejected.")
            return False

    def stage_ab_swap(self) -> str:
        inactive_partition = "B" if self.current_partition == "A" else "A"
        logger.info(f"Staging A/B swap: Current={self.current_partition} -> Staging={inactive_partition}")
        return inactive_partition

    def post_reboot_health_check(self, simulate_healthy: bool = True) -> bool:
        logger.info("Performing post-boot automated health check...")
        if simulate_healthy:
            logger.info("✅ All health probes passed. Confirming partition upgrade as permanent.")
            return True
        else:
            logger.warning("🚨 Health check FAILED! Reverting boot partition (automatic rollback).")
            return False


def main():
    parser = argparse.ArgumentParser(description="FLIP Gateway OTA Reference Client")
    parser.add_argument("--manifest", default="infra/ota/server/ota_manifest.json")
    parser.add_argument("--pubkey", default="infra/ota/cosign.pub")
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()

    client = GatewayOTAClient(Path(args.manifest), Path(args.pubkey))
    artifact_meta = client.check_for_updates(args.version)
    if artifact_meta:
        logger.info(f"New update found: {artifact_meta['version']}")
        inactive = client.stage_ab_swap()
        logger.info(f"Target partition {inactive} ready for deployment.")


if __name__ == "__main__":
    main()
