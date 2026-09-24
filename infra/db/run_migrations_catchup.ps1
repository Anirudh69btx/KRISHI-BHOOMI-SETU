param(
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"
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

    docker cp $File "${Container}:${containerPath}"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to copy $File to container" -ForegroundColor Red
        exit 1
    }

    $output = docker exec -u $User $Container psql -v ON_ERROR_STOP=1 -d $DB -f $containerPath 2>&1
    $exitCode = $LASTEXITCODE

    if ($output) { $output | ForEach-Object { Write-Host $_ } }

    if ($exitCode -ne 0) {
        Write-Host "`n[FAIL] $Label (exit code $exitCode)" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK]   $Label" -ForegroundColor Green
}

Write-Host "Checking container..." -ForegroundColor Cyan
$status = (docker inspect --format "{{.State.Status}}" $Container 2>&1).Trim()
if ($status -ne "running") {
    Write-Host "[ERROR] Container not running" -ForegroundColor Red; exit 1
}
docker exec $Container pg_isready -U $User -d $DB | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] PG not ready" -ForegroundColor Red; exit 1 }
Write-Host "[OK] PostgreSQL is ready" -ForegroundColor Green

$MigrDir = Join-Path $PSScriptRoot "migrations"

Exec-SQL -Label "0006 - Row Level Security Policies" -File (Join-Path $MigrDir "0006_rls_policies.sql")
Exec-SQL -Label "0007 - Functions and Triggers"      -File (Join-Path $MigrDir "0007_functions_triggers.sql")
Exec-SQL -Label "0008 - Auth Enhancements"           -File (Join-Path $MigrDir "0008_auth_enhancements.sql")
Exec-SQL -Label "0009 - Farmer-Farm Binding"         -File (Join-Path $MigrDir "0009_farmer_farms.sql")
Exec-SQL -Label "0010 - Trusted Devices"             -File (Join-Path $MigrDir "0010_trusted_devices.sql")

if (-not $SkipSeed) {
    Exec-SQL -Label "SEED  - Dev Seed Data" -File (Join-Path $MigrDir "seed_dev.sql")
}

Write-Host "`n===========================================" -ForegroundColor Cyan
Write-Host "  FLIP DB VERIFICATION" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

Write-Host "`nHypertables + Compression:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT hypertable_name, compression_enabled FROM timescaledb_information.hypertables ORDER BY hypertable_name;"

Write-Host "`nBackground Jobs:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT job_id, proc_name, hypertable_name, schedule_interval FROM timescaledb_information.jobs ORDER BY job_id;"

Write-Host "`nRLS Policies:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT tablename, policyname FROM pg_policies WHERE schemaname='public' ORDER BY tablename;"

Write-Host "`nSeed Row Counts:" -ForegroundColor Yellow
docker exec -u $User $Container psql -d $DB -c "SELECT 'orgs' AS tbl, COUNT(*) FROM orgs UNION ALL SELECT 'profiles', COUNT(*) FROM profiles UNION ALL SELECT 'farms', COUNT(*) FROM farms UNION ALL SELECT 'fields', COUNT(*) FROM fields UNION ALL SELECT 'devices', COUNT(*) FROM devices ORDER BY tbl;"

Write-Host "`n[SUCCESS] Migrations 0006-0010 + seed done!" -ForegroundColor Green
