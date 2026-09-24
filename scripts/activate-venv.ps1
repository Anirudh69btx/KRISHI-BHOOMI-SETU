<#
.SYNOPSIS
    Activates a FLIP service virtual environment.
.EXAMPLE
    .\scripts\activate-venv.ps1 core-api
    .\scripts\activate-venv.ps1 ml
    .\scripts\activate-venv.ps1 dev
#>

param(
    [ValidateSet('dev','core-api','copilot-rag','dialogue-manager/actions','tile-server','api-gateway','ml','edge/gateway','scripts')]
    [string]$Service = 'dev'
)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition | Split-Path -Parent

$VenvMap = @{
    'dev' = '.venv-dev'
    'ml' = 'ml\.venv'
    'edge/gateway' = 'edge\gateway\.venv'
    'scripts' = 'scripts\.venv'
}

$VenvDir = if ($VenvMap.ContainsKey($Service)) { $VenvMap[$Service] } else { "services\$Service\.venv" }
$ActivateScript = "$RootDir\$VenvDir\Scripts\Activate.ps1"

if (-not (Test-Path $ActivateScript)) {
    Write-Host "❌ Venv not found: $VenvDir. Run setup-venv.ps1 first." -ForegroundColor Red
    return
}

. $ActivateScript
Write-Host "✅ Activated $Service venv ($VenvDir)" -ForegroundColor Green
