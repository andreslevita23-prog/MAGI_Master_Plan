Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$commonPaths = @(
  "C:\Program Files\cloudflared\cloudflared.exe",
  "C:\Program Files (x86)\cloudflared\cloudflared.exe",
  "$env:USERPROFILE\cloudflared.exe",
  "$env:USERPROFILE\Downloads\cloudflared.exe"
)

foreach ($candidate in $commonPaths) {
  try {
    $version = & $candidate --version 2>$null
    Write-Host "cloudflared encontrado:" -ForegroundColor Green
    Write-Host $candidate
    Write-Host $version
    exit 0
  } catch {
  }
}

$fromPath = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($fromPath) {
  Write-Host "cloudflared encontrado en PATH:" -ForegroundColor Green
  Write-Host $fromPath.Source
  & $fromPath.Source --version
  exit 0
}

foreach ($candidate in $commonPaths) {
  if (Test-Path -LiteralPath $candidate) {
    Write-Host "cloudflared encontrado:" -ForegroundColor Green
    Write-Host $candidate
    & $candidate --version
    exit 0
  }
}

Write-Host "cloudflared no esta instalado o no esta en PATH." -ForegroundColor Yellow
Write-Host ""
Write-Host "Descarga oficial para Windows:"
Write-Host "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
Write-Host ""
Write-Host "Instalacion simple:"
Write-Host "1. Descarga cloudflared-windows-amd64.exe"
Write-Host "2. Renombralo a cloudflared.exe"
Write-Host "3. Guardalo en una carpeta incluida en PATH, por ejemplo C:\Windows\System32 o C:\Program Files\cloudflared"
Write-Host "4. Abre una nueva terminal y valida con:"
Write-Host "   cloudflared --version"
Write-Host ""
Write-Host "Tambien puedes dejarlo en Downloads y ejecutar start-cloudflare-tunnel.ps1; este script revisa esa ruta comun."
exit 1
