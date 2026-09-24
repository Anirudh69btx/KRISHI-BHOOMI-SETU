package flip.ota

# Default: do not permit OTA update
default allow = false

# Allow update if all safety conditions are met
allow {
    valid_signature
    sufficient_battery
    not emergency_mode
    within_rollout_phase
}

# Rule 1: Signature must be present and verified
valid_signature {
    input.signature_verified == true
    input.signer == "ci@flip.farm"
}

# Rule 2: Device battery must be at least 30% to prevent bricking during flash
sufficient_battery {
    input.device_battery_percent >= 30
}

# Rule 3: No pending or active disaster/emergency alerts on the farm
emergency_mode {
    input.active_emergency == true
}

# Rule 4: Canary / Staged rollout constraints
within_rollout_phase {
    # Beta channel allows 100% rollout
    input.channel == "beta"
}

within_rollout_phase {
    input.channel == "stable"
    # Modulo hash of device ID within current rollout percentage
    input.rollout_percentage >= 100
}
