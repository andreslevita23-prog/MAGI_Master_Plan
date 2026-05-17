Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptsRoot = $PSScriptRoot

Write-Host "Setup Cloudflare Tunnel nombrado para MAGI" -ForegroundColor Cyan
Write-Host "Dominio: https://magi.prosperity.lat"
Write-Host "Tunel: magi-dashboard (6eb582eb-0de5-43ce-9a26-d5dfe388d827)"
Write-Host "Servicio local: http://localhost:3001"
Write-Host ""
Write-Host "Paso manual inevitable: el login abrira navegador. Andres debe iniciar sesion, seleccionar prosperity.lat y autorizar."
Write-Host ""

& (Join-Path $scriptsRoot "cloudflare-login.ps1")
& (Join-Path $scriptsRoot "create-named-tunnel.ps1")
& (Join-Path $scriptsRoot "route-dns-magi.ps1")

Write-Host ""
Write-Host "Setup completado. Para iniciar el tunel cuando el dashboard ya este corriendo en 3001:" -ForegroundColor Green
Write-Host ".\scripts\windows\run-magi-named-tunnel.ps1"
Write-Host ""
Write-Host "Si quieres arrancarlo ahora, ejecutando run-magi-named-tunnel.ps1 se quedara conectado en esta terminal."
