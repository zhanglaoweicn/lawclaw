# LawClaw 开发启动脚本
# 启动方式: pwsh scripts/dev.ps1

$LawClawRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

Write-Host "=== LawClaw 律爪 开发环境 ===" -ForegroundColor Cyan

# 1. 启动 Python 后端（新窗口）
Write-Host "[1/2] 启动 Python 后端..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    python backend/main.py
} -ArgumentList $LawClawRoot

# 2. 启动 Tauri 开发模式（主进程）
Write-Host "[2/2] 启动 Tauri 桌面端..." -ForegroundColor Yellow
pnpm tauri dev

# 清理后端进程
Write-Host "停止 Python 后端..." -ForegroundColor Yellow
Stop-Job $backendJob
Remove-Job $backendJob
