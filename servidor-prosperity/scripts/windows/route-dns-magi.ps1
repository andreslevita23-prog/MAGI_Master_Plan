Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$cloudflaredPath = "C:\Program Files\cloudflared\cloudflared.exe"
$tunnelName = "magi-dashboard"
$tunnelId = "6eb582eb-0de5-43ce-9a26-d5dfe388d827"
$hostname = "magi.prosperity.lat"

try {
  & $cloudflaredPath --version | Out-Null
} catch {
  Write-Host "No se encontro cloudflared en: $cloudflaredPath" -ForegroundColor Yellow
  Write-Host "Ejecuta primero: .\scripts\windows\check-cloudflared.ps1"
  exit 1
}

Write-Host "Creando/actualizando ruta DNS: $hostname -> $tunnelName ($tunnelId)" -ForegroundColor Cyan
Write-Host "Se usa --overwrite-dns para corregir CNAMEs previos apuntando a otro tunel." -ForegroundColor Yellow
Write-Host ""

& $cloudflaredPath tunnel route dns --overwrite-dns $tunnelId $hostname
