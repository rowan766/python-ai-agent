param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPython = Join-Path $BackendDir ".venv-fastapi311\Scripts\python.exe"

if (-not (Test-Path $BackendPython)) {
    throw "未找到后端专用解释器: $BackendPython。请先在 backend 目录执行 `uv venv --python 3.11 .venv-fastapi311` 并安装依赖。"
}

Push-Location $BackendDir
try {
    $uvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3101")
    if (-not $NoReload) {
        $uvicornArgs += "--reload"
    }
    Write-Host "后端启动解释器: $BackendPython" -ForegroundColor Cyan
    Write-Host "后端启动参数: $($uvicornArgs -join ' ')" -ForegroundColor DarkGray
    & $BackendPython @uvicornArgs
}
finally {
    Pop-Location
}
