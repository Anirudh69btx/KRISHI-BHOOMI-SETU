param(
    [switch]$SeedOnly,
    [switch]$SkipSeed
)

$ErrorActionPreference = "Continue"
$Container = "flip-postgres"
$DB        = "flip"
$User      = "postgres"

function Exec-SQL {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][string]$File
    )

    Write-Host "`n-----------------------------------------" -ForegroundColor DarkGray
    Write-Host "[RUN] $Label" -ForegroundColor Cyan
    Write-Host "      File: $File" -ForegroundColor DarkGray

    $leafName = Split-Path $File -Leaf
    $containerPath = "/tmp/migration_$leafName"

    # Copy file into container
    docker cp $File "${Container}:${containerPath}"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to copy $File to container" -ForegroundColor Red
        exit 1
    }

    # Run with ON_ERROR_STOP=1
    $output = docker exec -u $User $Container psql -v ON_ERROR_STOP=1 -d $DB -f $containerPath 2>&1
    $exitCode = $LASTEXITCODE

    if ($output) {
        $output | ForEach-Object { Write-Host $_ }
    }

    if ($exitCode -ne 0) {
        Write-Host "`n[FAIL] $Label (exit code $exitCode)" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK]   $Label" -ForegroundColor Green
}

Write-Host "Checking container status..." -ForegroundColor Cyan
$status = (docker inspect --format "{{.State.Status}}" $Container 2>&1).Trim()
if ($status -ne "running") {
    Write-Host "[ERROR] Container '$Container' is not running (status: $status)" -ForegroundColor Red
    exit 1
}

$ready = docker exec $Container pg_isready -U $User -d $DB 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PostgreSQL not ready: $ready" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] PostgreSQL is ready" -ForegroundColor Green

$MigrDir = Join-Path $PSScriptRoot "migrations"

if (-not $SeedOnly) {
    Exec-SQL -Label "0001 - Initial Schema (extensions, tables, PostGIS)" -File (Join-Path $MigrDir "0001_initial_schema.sql")
    Exec-SQL -Label "0002 - TimescaleDB Hypertables and Compression"     -File (Join-Path $MigrDir "0002_timescale_hypertables.sql")
    Exec-SQL -Label "0003 - Advisory Templates and Action Verification" -File (Join-Path $MigrDir "0003_advisory_action.sql")
    Exec-SQL -Label "0004 - Disaster Dispatches Table"                  -File (Join-Path $MigrDir "0004_disaster_alerts.sql")
    Exec-SQL -Label "0005 - Materialized Views and Advanced Indexes"    -File (Join-Path $MigrDir "0005_indexes_views.sql")
    Exec-SQL -Label "0006 - Row Level Security Policies"                -File (Join-Path $MigrDir "0006_rls_policies.sql")
    Exec-SQL -Label "0007 - Functions and Triggers (NATS Bridge)"       -File (Join-Path $MigrDir "0007_functions_triggers.sql")
    Exec-SQL -Label "0008 - Auth Enhancements (Keycloak UUID Linkage)" -File (Join-Path $MigrDir "0008_auth_enhancements.sql")
    Exec-SQL -Label "0009 - Farmer Farms Binding & RLS"                -File (Join-Path $MigrDir "0009_farmer_farms.sql")
    Exec-SQL -Label "0010 - Trusted Devices (HMAC & Fingerprint)"      -File (Join-Path $MigrDir "0010_trusted_devices.sql")
    Exec-SQL -Label "0011 - Cleanup Hypertables + Missing Tables"      -File (Join-Path $MigrDir "0011_cleanup_and_missing.sql")
}

if (-not $SkipSeed) {
    Exec-SQL -Label "SEED - Dev Seed Data" -File (Join-Path $MigrDir "seed_dev.sql")
}

Write-Host "`n===========================================" -ForegroundColor Cyan
Write-Host "  FLIP DATABASE VERIFICATION REPORT" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

Write-Host "`nExtensions:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "\dx"

Write-Host "`nTables:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "\dt public.*"

Write-Host "`nHypertables:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT hypertable_name, num_dimensions, num_chunks FROM timescaledb_information.hypertables ORDER BY hypertable_name;"

Write-Host "`nCompression & Retention Policies:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT job_id, proc_name, hypertable_name, schedule_interval, config FROM timescaledb_information.jobs WHERE proc_name LIKE 'policy_%' ORDER BY job_id;"

Write-Host "`nMaterialized Views:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT matviewname FROM pg_matviews WHERE schemaname='public';"

Write-Host "`nRLS Policies:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT tablename, policyname FROM pg_policies WHERE schemaname='public' ORDER BY tablename;"

Write-Host "`nFunctions:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT routine_name, routine_type FROM information_schema.routines WHERE routine_schema='public' ORDER BY routine_name;"

Write-Host "`nTriggers:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT trigger_name, event_object_table FROM information_schema.triggers WHERE trigger_schema='public' ORDER BY event_object_table;"

Write-Host "`nIndexes (vector/spatial):" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT indexname, tablename, indexdef FROM pg_indexes WHERE schemaname='public' AND (indexdef LIKE '%hnsw%' OR indexdef LIKE '%gist%') ORDER BY tablename;"

Write-Host "`n[SUCCESS] All migrations and verification completed successfully!" -ForegroundColor Green
