param(
    [ValidateSet("compose", "local")]
    [string]$Mode = "local",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackendStartScript = Join-Path $BackendDir "start-backend.ps1"

function Write-Step {
    param(
        [string]$Title,
        [string]$Detail
    )

    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
    Write-Host $Detail -ForegroundColor DarkGray
}

function Start-InNewWindow {
    param(
        [string]$WorkingDirectory,
        [string]$Command,
        [string]$Title
    )

    Write-Step $Title $Command

    if ($DryRun) {
        return
    }

    $escapedDir = $WorkingDirectory.Replace("'", "''")
    $scriptBlock = "Set-Location '$escapedDir'; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; $Command"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $scriptBlock | Out-Null
}

function Invoke-InCurrentWindow {
    param(
        [string]$WorkingDirectory,
        [string]$Command,
        [string]$Title
    )

    Write-Step $Title $Command

    if ($DryRun) {
        return
    }

    Push-Location $WorkingDirectory
    try {
        Invoke-Expression $Command
    }
    finally {
        Pop-Location
    }
}

Write-Host "项目根目录: $ProjectRoot" -ForegroundColor Green

if ($Mode -eq "compose") {
    Invoke-InCurrentWindow $ProjectRoot "docker compose up -d" "启动 Docker 全量服务"
    Start-InNewWindow $FrontendDir "pnpm dev" "启动前端开发服务"

    Write-Host ""
    Write-Host "推荐模式已执行。" -ForegroundColor Green
    Write-Host "作用说明：" -ForegroundColor Yellow
    Write-Host "- docker compose up -d: 启动 postgres、redis、minio、qdrant、backend、document-worker"
    Write-Host "- pnpm dev: 启动前端开发服务器"
    Write-Host "访问地址：" -ForegroundColor Yellow
    Write-Host "- 前端: http://127.0.0.1:5173"
    Write-Host "- 后端文档: http://127.0.0.1:3101/docs"
    Write-Host "- MinIO Console: http://127.0.0.1:9001"
}
else {
    Invoke-InCurrentWindow $ProjectRoot "docker compose up -d postgres redis minio qdrant document-worker" "启动 Docker 基础依赖与独立 Worker"
    Start-InNewWindow $BackendDir "powershell -ExecutionPolicy Bypass -File `"$BackendStartScript`"" "启动本地 FastAPI 后端"
    Start-InNewWindow $FrontendDir "pnpm dev" "启动前端开发服务"

    Write-Host ""
    Write-Host "本地开发模式已执行。" -ForegroundColor Green
    Write-Host "作用说明：" -ForegroundColor Yellow
    Write-Host "- docker compose up -d postgres redis minio qdrant document-worker: 启动数据库、缓存、对象存储、向量库、独立文档 Worker"
    Write-Host "- ${BackendStartScript}: 唯一的本地后端启动入口，固定使用 backend\\.venv-fastapi311"
    Write-Host "- pnpm dev: 启动前端开发服务器"
    Write-Host "访问地址：" -ForegroundColor Yellow
    Write-Host "- 前端: http://127.0.0.1:5173"
    Write-Host "- 后端文档: http://127.0.0.1:3101/docs"
    Write-Host "- MinIO Console: http://127.0.0.1:9001"
}

if ($DryRun) {
    Write-Host ""
    Write-Host "当前是 DryRun，只打印命令，没有真正执行。" -ForegroundColor Magenta
}
