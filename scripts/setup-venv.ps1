<#
.SYNOPSIS
    Sets up Python 3.11 virtual environments for all FLIP services.
.DESCRIPTION
    Creates .venv directories and installs requirements per service.
    Run from repository root in PowerShell 5.1+ or PowerShell 7+.
#>

param(
    [string]$PythonCmd = ""
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition | Split-Path -Parent

Write-Host "🐍 Setting up Python 3.11 virtual environments..." -ForegroundColor Cyan

# Resolve Python executable
if (-not $PythonCmd) {
    if (Get-Command "python3.11" -ErrorAction SilentlyContinue) {
        $PythonCmd = "python3.11"
    } elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
        $ver = & python --version 2>&1
        if ($ver -match "3\.11") {
            $PythonCmd = "python"
        } else {
            Write-Host "⚠️ python is not 3.11 ($ver), checking python3..." -ForegroundColor Yellow
            if (Get-Command "python3" -ErrorAction SilentlyContinue) {
                $PythonCmd = "python3"
            } else {
                $PythonCmd = "python"
            }
        }
    } else {
        Write-Host "❌ Python not found. Install Python 3.11.9 from python.org" -ForegroundColor Red
        exit 1
    }
}

$pyVer = & $PythonCmd --version 2>&1
Write-Host "Using Python: $PythonCmd ($pyVer)" -ForegroundColor Green

function Setup-Venv {
    param(
        [string]$ServiceDir,
        [string]$ReqFile,
        [string]$VenvName
    )
    
    Write-Host "`n📦 Setting up $VenvName ($ServiceDir)..." -ForegroundColor Yellow
    $TargetDir = Join-Path $RootDir $ServiceDir
    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }
    Set-Location $TargetDir
    
    if (-not (Test-Path ".venv")) {
        Write-Host "  Creating venv in $TargetDir\.venv..."
        & $PythonCmd -m venv .venv
    }
    
    $ActivateScript = Join-Path $TargetDir ".venv\Scripts\Activate.ps1"
    if (Test-Path $ActivateScript) {
        & $ActivateScript
        python -m pip install --upgrade pip setuptools wheel
        pip install -r $ReqFile
        deactivate
        Write-Host "✅ $VenvName ready" -ForegroundColor Green
    } else {
        Write-Host "❌ Could not find $ActivateScript" -ForegroundColor Red
    }
}

# Core services
Setup-Venv "services\core-api" "requirements.txt" "Core API"
Setup-Venv "services\copilot-rag" "requirements.txt" "Copilot RAG"
Setup-Venv "services\dialogue-manager\actions" "requirements.txt" "Rasa Actions"
Setup-Venv "services\tile-server" "requirements.txt" "Tile Server"
Setup-Venv "services\api-gateway" "requirements.txt" "API Gateway"

# ML
Setup-Venv "ml" "requirements-train.txt" "ML Training"

# Edge
Setup-Venv "edge\gateway" "requirements.txt" "Gateway Edge"

# Scripts
Setup-Venv "scripts" "requirements.txt" "Utility Scripts"

# Root dev
Write-Host "`n📦 Setting up root dev environment..." -ForegroundColor Yellow
Set-Location $RootDir
if (-not (Test-Path ".venv-dev")) {
    & $PythonCmd -m venv .venv-dev
}
$DevActivate = Join-Path $RootDir ".venv-dev\Scripts\Activate.ps1"
if (Test-Path $DevActivate) {
    & $DevActivate
    python -m pip install --upgrade pip setuptools wheel
    pip install -r requirements-dev.txt
    deactivate
    Write-Host "✅ Root dev environment ready" -ForegroundColor Green
}

Write-Host "`n🎉 All virtual environments ready!" -ForegroundColor Green
Write-Host "Activate via: .\scripts\activate-venv.ps1 [service]" -ForegroundColor Cyan
