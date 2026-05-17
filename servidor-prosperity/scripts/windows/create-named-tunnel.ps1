Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$cloudflaredPath = "C:\Program Files\cloudflared\cloudflared.exe"
$tunnelName = "magi-dashboard"

try {
  & $cloudflaredPath --version | Out-Null
} catch {
  Write-Host "No se encontro cloudflared en: $cloudflaredPath" -ForegroundColor Yellow
  Write-Host "Ejecuta primero: .\scripts\windows\check-cloudflared.ps1"
  exit 1
}

Write-Host "Creando tunel nombrado: $tunnelName" -ForegroundColor Cyan
Write-Host "Si ya existe, este comando puede fallar sin afectar un tunel previamente creado."
Write-Host ""

& $cloudflaredPath tunnel create $tunnelName
