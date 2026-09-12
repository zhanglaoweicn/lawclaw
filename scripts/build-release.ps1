# LawClaw 发布打包脚本
# 生成 U 盘便携版 exe
# 前置条件: 安装 Python 3.11+, Node.js, Rust

$LawClawRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$DistDir = Join-Path $LawClawRoot "dist-lawclaw"

Write-Host "=== LawClaw 律爪 发布打包 ===" -ForegroundColor Cyan

# Step 1: 前端构建
Write-Host "[1/4] 构建前端..." -ForegroundColor Yellow
Set-Location $LawClawRoot
pnpm build
if (-not $?) { Write-Host "前端构建失败" -ForegroundColor Red; exit 1 }

# Step 2: Tauri 构建桌面端
Write-Host "[2/4] 构建 Tauri 桌面端..." -ForegroundColor Yellow
pnpm tauri build
if (-not $?) { Write-Host "Tauri 构建失败" -ForegroundColor Red; exit 1 }

# Step 3: PyInstaller 打包 Python 后端
Write-Host "[3/4] 打包 Python 引擎 (PyInstaller)..." -ForegroundColor Yellow
python -m PyInstaller `
    --name hermes-engine `
    --onefile `
    --distpath (Join-Path $LawClawRoot "src-tauri\binaries") `
    --add-data "agent:agent" `
    --add-data "tools:tools" `
    --add-data "hermes_cli:hermes_cli" `
    --add-data "gateway:gateway" `
    --hidden-import=openai `
    --hidden-import=rich `
    --hidden-import=pyyaml `
    backend/main.py
if (-not $?) { Write-Host "PyInstaller 打包失败" -ForegroundColor Red; exit 1 }

# Step 4: 整合发布包
Write-Host "[4/4] 整合发布包..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $DistDir -Force
Copy-Item (Join-Path $LawClawRoot "src-tauri\target\release\LawClaw.exe") $DistDir
Copy-Item (Join-Path $LawClawRoot "src-tauri\binaries\hermes-engine.exe") $DistDir
Copy-Item (Join-Path $LawClawRoot "backend\.env.example") (Join-Path $DistDir ".env")
Copy-Item (Join-Path $LawClawRoot "backend\config.yaml") $DistDir

Write-Host "=== 打包完成 ===" -ForegroundColor Green
Write-Host "发布目录: $DistDir" -ForegroundColor Green
Write-Host "将整个目录复制到 U 盘即可使用" -ForegroundColor Green
