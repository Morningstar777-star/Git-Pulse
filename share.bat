@echo off
setlocal
title GitPulse - Public Sharing Tunnel
cd /d "%~dp0"

echo ==========================================================
echo        GitPulse Explorer - Public Sharing Tunnel
echo ==========================================================
echo.
echo Launching high-speed Cloudflare tunnel for http://127.0.0.1:8000 ...
echo.

if exist "%~dp0cloudflared.exe" (
    "%~dp0cloudflared.exe" tunnel --url http://127.0.0.1:8000
) else (
    echo cloudflared.exe not found, falling back to ngrok...
    ngrok http 8000
)

pause
