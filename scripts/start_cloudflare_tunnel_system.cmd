@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if "%CF_TUNNEL_PORT%"=="" set "CF_TUNNEL_PORT=7860"

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo [ERROR] cloudflared not on PATH.
  echo Install:  winget install Cloudflare.cloudflared
  echo Then open a NEW terminal and run this script again.
  exit /b 1
)

for /f "delims=" %%I in ('where cloudflared 2^>nul') do (
  set "CF_EXE=%%I"
  goto :found
)
:found

echo Using: %CF_EXE%
echo Local backend: http://127.0.0.1:%CF_TUNNEL_PORT%/ ^(start app.py first^)
echo.

set "CF_LOG=--loglevel info"
if /I "%CF_TUNNEL_DEBUG%"=="1" set "CF_LOG=--loglevel debug --transport-loglevel debug"

"%CF_EXE%" tunnel %CF_LOG% --url "http://127.0.0.1:%CF_TUNNEL_PORT%/"

echo.
echo cloudflared exited. ERRORLEVEL=%ERRORLEVEL%
