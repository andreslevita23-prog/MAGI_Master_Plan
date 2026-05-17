Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$commonPaths = @(
  "C:\Program Files\cloudflared\cloudflared.exe",
  "C:\Program Files (x86)\cloudflared\cloudflared.exe",
  "$env:USERPROFILE\cloudflared.exe",
  "$env:USERPROFILE\Downloads\cloudflared.exe"
)

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
$cloudflaredPath = if ($cloudflared) { $cloudflared.Source } else { $null }

if (-not $cloudflaredPath) {
  foreach ($candidate in $commonPaths) {
    if (Test-Path -LiteralPath $candidate) {
      $cloudflaredPath = $candidate
      break
    }
  }
}

if (-not $cloudflaredPath) {
  Write-Host "No se encontro cloudflared. Ejecuta primero:" -ForegroundColor Yellow
  Write-Host ".\scripts\windows\check-cloudflared.ps1"
  exit 1
}

Write-Host "Iniciando Cloudflare Quick Tunnel temporal hacia MAGI dashboard privado..." -ForegroundColor Cyan
Write-Host "Origen local: http://localhost:3001"
Write-Host "Binario: $cloudflaredPath"
Write-Host ""
Write-Host "Nota: quick tunnel genera una URL trycloudflare.com temporal." -ForegroundColor Yellow
Write-Host "Para https://magi.prosperity.lat usa el tunel nombrado:" -ForegroundColor Yellow
Write-Host ".\scripts\windows\setup-cloudflare-magi.ps1"
Write-Host ".\scripts\windows\run-magi-named-tunnel.ps1"
Write-Host ""

& $cloudflaredPath tunnel --url http://localhost:3001
