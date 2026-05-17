Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$cloudflaredPath = "C:\Program Files\cloudflared\cloudflared.exe"
$tunnelName = "magi-dashboard"
$tunnelId = "6eb582eb-0de5-43ce-9a26-d5dfe388d827"
$hostname = "magi.prosperity.lat"
$service = "http://localhost:3001"
$cloudflaredHome = Join-Path $env:USERPROFILE ".cloudflared"
$configPath = Join-Path $cloudflaredHome "magi-dashboard-config.yml"
$credentialsPath = Join-Path $cloudflaredHome "$tunnelId.json"

try {
  & $cloudflaredPath --version | Out-Null
} catch {
  Write-Host "No se encontro cloudflared en: $cloudflaredPath" -ForegroundColor Yellow
  Write-Host "Ejecuta primero: .\scripts\windows\check-cloudflared.ps1"
  exit 1
}

if (-not (Test-Path -LiteralPath $cloudflaredHome)) {
  Write-Host "No existe la carpeta $cloudflaredHome. Ejecuta primero cloudflare-login.ps1 y create-named-tunnel.ps1." -ForegroundColor Yellow
  exit 1
}

if (-not (Test-Path -LiteralPath $credentialsPath)) {
  Write-Host "No se encontro el archivo de credenciales esperado para $tunnelName." -ForegroundColor Yellow
  Write-Host "Esperado: $credentialsPath"
  Write-Host "No se usaran credenciales de otros tuneles para evitar enrutar a un ID incorrecto."
  Write-Host "Ejecuta primero: .\scripts\windows\create-named-tunnel.ps1"
  exit 1
}

$credentials = Get-Content -LiteralPath $credentialsPath -Raw | ConvertFrom-Json
if ($credentials.TunnelID -ne $tunnelId) {
  Write-Host "El archivo de credenciales no corresponde al tunel esperado." -ForegroundColor Yellow
  Write-Host "Esperado: $tunnelId"
  Write-Host "Encontrado: $($credentials.TunnelID)"
  exit 1
}

$config = @"
tunnel: $tunnelId
credentials-file: $credentialsPath

ingress:
  - hostname: $hostname
    service: $service
  - service: http_status:404
"@

Set-Content -LiteralPath $configPath -Value $config -Encoding ASCII

Write-Host "Ejecutando tunel nombrado MAGI..." -ForegroundColor Cyan
Write-Host "URL publica: https://$hostname"
Write-Host "Tunel: $tunnelName ($tunnelId)"
Write-Host "Servicio local: $service"
Write-Host "Config: $configPath"
Write-Host ""

& $cloudflaredPath tunnel --config $configPath run $tunnelId
