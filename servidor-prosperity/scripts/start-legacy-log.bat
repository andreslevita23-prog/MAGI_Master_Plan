@echo off
cd /d C:\Users\Asus\servidor-prosperity

echo [%date% %time%] Iniciando Prosperity... >> log.txt

start "Tunnel" cmd /k "cloudflared tunnel run prosperity-tunnel ^& echo Tunnel terminado. >> log.txt"
timeout /t 10
start "Servidor Node" cmd /k "node index.js ^& echo Servidor detenido. >> log.txt"

echo [%date% %time%] Scripts lanzados. >> log.txt
