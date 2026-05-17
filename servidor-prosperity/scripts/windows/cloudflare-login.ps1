Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$cloudflaredPath = "C:\Program Files\cloudflared\cloudflared.exe"

try {
  & $cloudflaredPath --version | Out-Null
} catch {
  Write-Host "No se encontro cloudflared en: $cloudflaredPath" -ForegroundColor Yellow
  Write-Host "Ejecuta primero: .\scripts\windows\check-cloudflared.ps1"
  exit 1
}

Write-Host "Abriendo login de Cloudflare..." -ForegroundColor Cyan
Write-Host "Paso manual: inicia sesion, selecciona prosperity.lat y autoriza cloudflared."
Write-Host ""

& $cloudflaredPath tunnel login
