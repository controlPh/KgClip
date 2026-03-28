@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if "%CF_TUNNEL_PORT%"=="" set "CF_TUNNEL_PORT=7860"

if not exist "tools\cloudflared.exe" (
  echo [ERROR] Missing tools\cloudflared.exe
  echo Download: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
  echo Rename to cloudflared.exe and place in project tools\ folder.
  exit /b 1
)

echo Local backend: http://127.0.0.1:%CF_TUNNEL_PORT%/ ^(start app.py first^)
echo.
echo Connecting to Cloudflare quick tunnel... Usually 15-90 seconds.
echo Success line contains: trycloudflare.com
echo.
echo NOTE: In PowerShell, debug mode is NOT  "set CF_TUNNEL_DEBUG=1"
echo       Use:  $env:CF_TUNNEL_DEBUG = "1"
echo       ^(CMD.exe uses: set CF_TUNNEL_DEBUG=1^)
echo.

if exist "%USERPROFILE%\.cloudflared\config.yml" (
  echo [WARN] Found %USERPROFILE%\.cloudflared\config.yml — rename if quick tunnel fails.
  echo.
)
if exist "%USERPROFILE%\.cloudflared\config.yaml" (
  echo [WARN] Found %USERPROFILE%\.cloudflared\config.yaml — rename if quick tunnel fails.
  echo.
)

set "CF_LOG=--loglevel info"
if /I "%CF_TUNNEL_DEBUG%"=="1" set "CF_LOG=--loglevel debug --transport-loglevel debug"

set "CF_RUN=%TEMP%\kgclip_cloudflared.exe"
copy /Y "tools\cloudflared.exe" "%CF_RUN%" >nul
if errorlevel 1 (
  echo [ERROR] Could not copy cloudflared to %TEMP% — run CMD as normal user with temp dir writable.
  exit /b 1
)
echo Running cloudflared from %TEMP% ^(avoids sync-folder locks on BaiduSyncdisk, etc.^)
echo.

"%CF_RUN%" tunnel %CF_LOG% --url "http://127.0.0.1:%CF_TUNNEL_PORT%/"

set "EC=%ERRORLEVEL%"
echo.
echo cloudflared exited. ERRORLEVEL=%EC%

if %EC% NEQ 0 (
  echo.
  echo ========== Troubleshooting ==========
  echo ERRORLEVEL %EC% often means cloudflared CRASHED ^(access violation 0xC0000005^), not a network timeout.
  echo.
  echo 1^) Project on Baidu Netdisk sync: move cloudflared.exe to C:\bin\ or use winget build ^(see below^).
  echo 2^) winget install Cloudflare.cloudflared
  echo    then run:  scripts\start_cloudflare_tunnel_system.cmd
  echo 3^) Re-download cloudflared-windows-amd64.exe ^(must match Windows x64^).
  echo 4^) Antivirus: temporarily allow tools\cloudflared.exe and %TEMP%\kgclip_cloudflared.exe
  echo =====================================
)
