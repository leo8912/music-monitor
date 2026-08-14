# ============================================================================
# music-monitor 一键启动脚本 (Windows / PowerShell)
#
# 用法:
#   .\run_dev.ps1            # 开发模式: 后端 :8000 + 前端 Vite :5173, 自动开浏览器
#   .\run_dev.ps1 -Prod      # 单进程模式: 构建前端后仅由后端 :8000 托管, 自动开浏览器
#   .\run_dev.ps1 -NoInstall # 跳过依赖检查/安装, 直接启动
#
# 停止方式: 关闭弹出的两个命令行窗口, 或 Ctrl+C。
# ============================================================================

param(
    [switch]$Prod,       # 单进程模式: 后端直接托管构建好的 web/dist
    [switch]$NoInstall   # 跳过依赖安装检查
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$venvPy   = Join-Path $root '.venv\Scripts\python.exe'
$webDir   = Join-Path $root 'web'
$nodeMods = Join-Path $webDir 'node_modules'

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  music-monitor 一键启动" -ForegroundColor Cyan
Write-Host "  模式: $(if ($Prod) { '单进程 (Prod, :8000)' } else { '开发 (后端 :8000 + 前端 :5173)' })" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# ---------- 1. 检查 Python ----------
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "未找到 python, 请先安装 Python 3.11+ 并加入 PATH"
    exit 1
}

# ---------- 2. 检查/创建 .venv 并安装依赖 ----------
if (-not (Test-Path $venvPy)) {
    Write-Host ">> 未找到 .venv, 正在创建虚拟环境..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Error "创建 .venv 失败"; exit 1 }
    & $venvPy -m pip install --upgrade pip
}

if (-not $NoInstall) {
    Write-Host ">> 检查 Python 依赖..." -ForegroundColor Yellow
    & $venvPy -c "import fastapi, sqlalchemy, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ">> 安装 Python 依赖 (requirements.txt)..." -ForegroundColor Yellow
        & $venvPy -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { Write-Error "依赖安装失败"; exit 1 }
    } else {
        Write-Host "   Python 依赖已就绪。" -ForegroundColor Green
    }
}

# ---------- 3. 检查 Node/npm 与前端依赖 ----------
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "未找到 npm, 请先安装 Node.js 18+"
    exit 1
}

if (-not $NoInstall -and -not (Test-Path $nodeMods)) {
    Write-Host ">> 安装前端依赖 (npm install)..." -ForegroundColor Yellow
    Push-Location $webDir
    npm install
    $npmExit = $LASTEXITCODE
    Pop-Location
    if ($npmExit -ne 0) { Write-Error "npm install 失败"; exit 1 }
}

# ---------- 4. 端口占用检查 ----------
function Test-PortInUse([int]$port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn)
}

if (Test-PortInUse 8000) {
    Write-Warning "端口 8000 已被占用 (可能已有后端在运行)。脚本将直接打开该端口, 请确认是本项目实例。"
}
if (-not $Prod -and (Test-PortInUse 5173)) {
    Write-Warning "端口 5173 已被占用 (可能已有前端在运行)。脚本将直接打开该端口, 请确认是本项目实例。"
}

# ---------- 5. 构建前端 (Prod 模式) ----------
if ($Prod) {
    $dist = Join-Path $webDir 'dist'
    if (-not $NoInstall -or -not (Test-Path $dist)) {
        Write-Host ">> 构建前端 (npm run build)..." -ForegroundColor Yellow
        Push-Location $webDir
        npm run build
        $buildExit = $LASTEXITCODE
        Pop-Location
        if ($buildExit -ne 0) { Write-Error "前端构建失败"; exit 1 }
    }
}

# ---------- 6. 启动后端 ----------
Write-Host ">> 启动后端 (python main.py, :8000)..." -ForegroundColor Yellow
$backendArgs = @('-NoExit', '-NoProfile', '-Command', "Set-Location '$root'; & '$venvPy' main.py")
Start-Process powershell -ArgumentList $backendArgs -WindowStyle Normal

# 等待后端就绪 (用 .venv python 探测, 规避 PS 5.1 Invoke-WebRequest 的挂起/IPv6 解析问题)
Write-Host ">> 等待后端就绪..." -ForegroundColor Yellow
$probeCode = @'
import urllib.request, sys
try:
    ok = urllib.request.urlopen('http://127.0.0.1:8000/api/check_auth', timeout=2).status < 400
except Exception:
    ok = False
sys.exit(0 if ok else 1)
'@
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    # 2>&1 合并输出并丢弃: PS 5.1 的 2>$null 会误显示 NativeCommandError
    $null = & $venvPy -c $probeCode 2>&1
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    Write-Warning "后端 30 秒内未就绪, 请检查上方后端窗口日志。仍将尝试打开网页..."
} else {
    Write-Host "  后端已就绪。" -ForegroundColor Green
}

# ---------- 7. 启动前端 (开发模式) / 打开浏览器 ----------
if ($Prod) {
    $url = "http://localhost:8000"
    Write-Host ">> 单进程模式: 前端已由后端托管。" -ForegroundColor Green
} else {
    Write-Host ">> 启动前端 (npm run dev, :5173)..." -ForegroundColor Yellow
    $frontArgs = @('-NoExit', '-NoProfile', '-Command', "Set-Location '$webDir'; npm run dev")
    Start-Process powershell -ArgumentList $frontArgs -WindowStyle Normal
    $url = "http://localhost:5173"
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  启动完成! 正在打开浏览器: $url" -ForegroundColor Green
Write-Host "  默认账号: music / password (见 config/config.yaml)" -ForegroundColor Green
Write-Host "  关闭弹出的命令行窗口即可停止服务。" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Start-Process $url
