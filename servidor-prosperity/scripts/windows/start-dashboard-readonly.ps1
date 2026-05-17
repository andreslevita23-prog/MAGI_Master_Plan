Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

# Credenciales de ejemplo. Reemplazar por usuarios/secretos reales fuera de Git.
$dashboardUsers = @(
  @{ user = "demo"; password = "change-me" }
) | ConvertTo-Json -Compress

$env:READ_ONLY_DASHBOARD = "true"
$env:PORT = "3001"
$env:DASHBOARD_USERS_JSON = $dashboardUsers
$env:MAGI_BOT_C_AUDIT_DIR = "<ruta-real-a-MQL5\Files\MAGI\audit>"

Write-Host "MAGI dashboard privado solo lectura" -ForegroundColor Cyan
Write-Host "Puerto: $env:PORT"
Write-Host "Bot C audit dir: $env:MAGI_BOT_C_AUDIT_DIR"
Write-Host "Usuarios habilitados: demo"
Write-Host "Rutas /analisis bloqueadas en READ_ONLY_DASHBOARD=true"
Write-Host ""

npm run start
