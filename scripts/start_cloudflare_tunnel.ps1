# 将本机 Gradio（默认 7860）通过 Cloudflare 临时隧道暴露到公网。
#
# 若提示「禁止运行脚本」，任选其一：
#   1) 用 CMD 无策略限制：  scripts\start_cloudflare_tunnel.cmd
#   2) 仅本次绕过策略：    powershell -ExecutionPolicy Bypass -File .\scripts\start_cloudflare_tunnel.ps1
#
# 正常用法：先在一个终端运行 app.py，再开新终端执行本脚本。
# 可选：$env:CF_TUNNEL_PORT = "8080" 再运行以改用其它端口。

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $ProjectRoot "tools\cloudflared.exe"
$Port = if ($env:CF_TUNNEL_PORT -match '^\d+$') { $env:CF_TUNNEL_PORT } else { "7860" }

if (-not (Test-Path $Exe)) {
    Write-Error @"
未找到 tools\cloudflared.exe。
请从官方发布页下载 Windows 版并重命名为 cloudflared.exe 放到项目 tools\ 目录：
https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
"@
}

Write-Host "Local backend: http://127.0.0.1:$Port/ (start app.py first)" -ForegroundColor Cyan
Write-Host "Quick tunnel: wait 15-90s for a line with trycloudflare.com" -ForegroundColor Cyan
Write-Host 'If stuck: check firewall/proxy; rename $env:USERPROFILE\.cloudflared\config.yml if it exists. Debug: $env:CF_TUNNEL_DEBUG = "1"' -ForegroundColor DarkGray
Write-Host ""

$cfLog = @("--loglevel", "info")
if ($env:CF_TUNNEL_DEBUG -eq "1") { $cfLog = @("--loglevel", "debug", "--transport-loglevel", "debug") }

& $Exe tunnel @cfLog --url "http://127.0.0.1:$Port/"
