#!/usr/bin/env bash
# FLIP Gateway Post-Boot / Post-OTA Health Check Script
set -e

echo "=== Running Gateway Hardware & Service Health Check ==="

# 1. Check local MQTT broker
echo -n "Checking MQTT broker (1883)... "
if nc -z localhost 1883 2>/dev/null || timeout 1 bash -c "</dev/tcp/localhost/1883" 2>/dev/null; then
    echo "OK"
else
    echo "FAIL (MQTT not listening)"
    exit 1
fi

# 2. Check SQLite database access
echo -n "Checking SQLite buffer database... "
if sqlite3 /data/gateway.db "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "OK"
else
    echo "FAIL (Database corrupt or unreadable)"
    exit 1
fi

# 3. Check Edge AI models directory
echo -n "Checking Edge AI models... "
if [ -d "/models" ] && [ "$(ls -A /models 2>/dev/null)" ]; then
    echo "OK"
else
    echo "WARN (Models path empty or not mounted)"
fi

# 4. Check Free Disk Space (>500MB required)
echo -n "Checking free disk space... "
FREE_KB=$(df /data | awk 'NR==2 {print $4}')
if [ "$FREE_KB" -gt 512000 ]; then
    echo "OK (${FREE_KB}KB available)"
else
    echo "FAIL (Low disk space: ${FREE_KB}KB)"
    exit 1
fi

echo "✅ All Gateway Health Checks Passed!"
exit 0
