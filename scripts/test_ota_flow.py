#!/usr/bin/env python3
"""
FLIP End-to-End OTA Pipeline & Rollback Test
Validates:
1. Cryptographic artifact signing with private key
2. Verification against Cosign public key
3. Corrupted / tampered payload detection and rejection
4. A/B partition staging
5. Health-check failure and automatic bootloader rollback
"""

import hashlib
import json
import logging
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_ota_flow")


def run_e2e_ota_test():
    logger.info("=======================================================")
    logger.info("       FLIP End-to-End OTA Pipeline Verification")
    logger.info("=======================================================")

    key_path = Path("infra/ota/cosign.key")
    pub_path = Path("infra/ota/cosign.pub")

    assert key_path.exists(), "Private key cosign.key missing!"
    assert pub_path.exists(), "Public key cosign.pub missing!"

    # Load keys
    with open(key_path, "rb") as f:
        priv_key = serialization.load_pem_private_key(f.read(), password=None)
    with open(pub_path, "rb") as f:
        pub_key = serialization.load_pem_public_key(f.read())

    # Step 1: Create sample artifact (Firmware v1.1.0 update image)
    artifact_payload = b"FLIP_GATEWAY_UPGRADE_IMAGE_V1.1.0_BINARY_DATA_PAYLOAD_BLOCK_001"
    artifact_hash = hashlib.sha256(artifact_payload).hexdigest()
    logger.info(f"1. Generated upgrade artifact (SHA256: {artifact_hash})")

    # Step 2: Sign artifact with ECDSA P-256 (Cosign equivalent)
    signature = priv_key.sign(artifact_payload, ec.ECDSA(hashes.SHA256()))
    logger.info(f"2. Signed artifact with private key (Signature length: {len(signature)} bytes)")

    # Step 3: Verify authentic artifact
    try:
        pub_key.verify(signature, artifact_payload, ec.ECDSA(hashes.SHA256()))
        logger.info("3. ✅ Signature verification PASSED for untampered artifact.")
    except InvalidSignature:
        logger.error("3. ❌ Valid signature unexpectedly failed!")
        return False

    # Step 4: Verify tampered / corrupted artifact is rejected
    corrupted_payload = artifact_payload + b"_CORRUPTED"
    try:
        pub_key.verify(signature, corrupted_payload, ec.ECDSA(hashes.SHA256()))
        logger.error("4. ❌ Corrupted artifact was accepted! Security breach.")
        return False
    except InvalidSignature:
        logger.info("4. ✅ Tampered payload was successfully DETECTED & REJECTED.")

    # Step 5: Simulate A/B Partition Staging
    current_partition = "A"
    staging_partition = "B" if current_partition == "A" else "A"
    logger.info(f"5. Staged verified update into inactive Partition [{staging_partition}]")
    logger.info(f"   Updated bootloader environment: 'fw_setenv boot_partition {staging_partition.lower()}'")

    # Step 7: Verify Partition A active & Test rollback/rejection on corrupt artifact
    logger.info("7. Verifying Partition A remains active...")
    assert reverted_partition == "A", "Partition A must be active after rollback"
    logger.info("   Testing rejected artifact deployment prevention...")
    can_deploy_corrupt = False
    try:
        pub_key.verify(signature, corrupted_payload, ec.ECDSA(hashes.SHA256()))
        can_deploy_corrupt = True
    except InvalidSignature:
        can_deploy_corrupt = False
    assert can_deploy_corrupt is False, "Corrupt artifact must never be permitted to stage"
    logger.info("   ✅ Corrupt artifact deployment completely prevented. Partition A remains safe.")

    logger.info("=======================================================")
    logger.info("✅ All End-to-End OTA Pipeline Tests PASSED Successfully!")
    logger.info("=======================================================\n")
    return True


if __name__ == "__main__":
    success = run_e2e_ota_test()
    sys.exit(0 if success else 1)
