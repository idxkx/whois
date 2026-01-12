# WhoisAI 域名查询系统管理脚本
# PowerShell 版本 - 用于 Windows 环境

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$LogsDir = Join-Path $ProjectRoot "logs"

# 确保日志目录存在
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

function Show-Help {
    Write-Host "WhoisAI 域名查询系统 - 可用命令:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  .\manage.ps1 install    - 安装项目依赖" -ForegroundColor White
    Write-Host "  .\manage.ps1 run        - 前台运行服务（用于开发调试）" -ForegroundColor White
    Write-Host "  .\manage.ps1 start      - 后台启动服务" -ForegroundColor White
    Write-Host "  .\manage.ps1 stop       - 停止服务" -ForegroundColor White
    Write-Host "  .\manage.ps1 restart    - 重启服务" -ForegroundColor White
    Write-Host "  .\manage.ps1 status     - 查看服务状态" -ForegroundColor White
    Write-Host "  .\manage.ps1 logs       - 查看服务日志" -ForegroundColor White
    Write-Host "  .\manage.ps1 test       - 运行测试" -ForegroundColor White
    Write-Host "  .\manage.ps1 clean      - 清理临时文件和缓存" -ForegroundColor White
    Write-Host "  .\manage.ps1 build      - 构建项目（检查语法）" -ForegroundColor White
    Write-Host "  .\manage.ps1 deploy     - 部署项目" -ForegroundColor White
    Write-Host ""
}

function Install-Dependencies {
    Write-Host "检查 Python 环境..." -ForegroundColor Yellow
    python --version

    Write-Host "安装项目依赖..." -ForegroundColor Yellow
    $requirementsFile = Join-Path $ProjectRoot "requirements.txt"
    if (Test-Path $requirementsFile) {
        pip install -r $requirementsFile
    } else {
        Write-Host "未找到 requirements.txt，跳过依赖安装" -ForegroundColor Gray
    }
    Write-Host "依赖安装完成" -ForegroundColor Green
}

function Start-ServiceForeground {
    Write-Host "启动服务（前台运行）..." -ForegroundColor Yellow
    $serverScript = Join-Path $ProjectRoot "server\app.py"
    python $serverScript
}

function Start-ServiceBackground {
    Write-Host "后台启动服务..." -ForegroundColor Yellow

    $serverScript = Join-Path $ProjectRoot "server\app.py"
    $logFile = Join-Path $LogsDir "server.log"
    $errorFile = Join-Path $LogsDir "error.log"

    $process = Start-Process python -ArgumentList $serverScript `
        -WindowStyle Hidden `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError $errorFile `
        -PassThru

    Start-Sleep -Seconds 2

    if ($process -and !$process.HasExited) {
        Write-Host "服务已启动 - PID: $($process.Id)" -ForegroundColor Green
        Write-Host "日志文件: $logFile" -ForegroundColor Gray
    } else {
        Write-Host "服务启动失败，请查看错误日志: $errorFile" -ForegroundColor Red
    }

    Show-Status
}

function Stop-Service {
    Write-Host "正在停止服务..." -ForegroundColor Yellow

    $processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*server/app.py*" -or $_.CommandLine -like "*server\app.py*"
    }

    if ($processes) {
        $processes | ForEach-Object {
            Write-Host "停止进程 PID: $($_.Id)" -ForegroundColor Gray
            Stop-Process -Id $_.Id -Force
        }
        Write-Host "服务已停止" -ForegroundColor Green
    } else {
        Write-Host "未找到运行中的服务" -ForegroundColor Gray
    }
}

function Restart-Service {
    Stop-Service
    Start-Sleep -Seconds 1
    Start-ServiceBackground
    Write-Host "服务已重启" -ForegroundColor Green
}

function Show-Status {
    Write-Host "检查服务状态..." -ForegroundColor Yellow

    $processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*server/app.py*" -or $_.CommandLine -like "*server\app.py*"
    }

    if ($processes) {
        Write-Host "服务运行中:" -ForegroundColor Green
        $processes | ForEach-Object {
            Write-Host "  PID: $($_.Id) | CPU: $($_.CPU) | 内存: $([math]::Round($_.WorkingSet64/1MB, 2)) MB" -ForegroundColor White
        }
    } else {
        Write-Host "服务未运行" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "检查端口占用..." -ForegroundColor Yellow
    $portCheck = netstat -ano | Select-String ":8888"
    if ($portCheck) {
        Write-Host "端口 8888 占用情况:" -ForegroundColor White
        $portCheck | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Write-Host "端口 8888 未被占用" -ForegroundColor Gray
    }
}

function Show-Logs {
    $serverLog = Join-Path $LogsDir "server.log"
    $errorLog = Join-Path $LogsDir "error.log"

    Write-Host "=== 服务日志 ===" -ForegroundColor Cyan
    if (Test-Path $serverLog) {
        Get-Content $serverLog -Tail 50
    } else {
        Write-Host "日志文件不存在" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "=== 错误日志 ===" -ForegroundColor Cyan
    if (Test-Path $errorLog) {
        Get-Content $errorLog -Tail 50
    } else {
        Write-Host "错误日志文件不存在" -ForegroundColor Gray
    }
}

function Run-Tests {
    Write-Host "运行测试..." -ForegroundColor Yellow
    $testsDir = Join-Path $ProjectRoot "tests"
    python -m pytest $testsDir -v
}

function Clean-Project {
    Write-Host "清理临时文件..." -ForegroundColor Yellow

    # 清理 __pycache__ 目录
    Get-ChildItem -Path $ProjectRoot -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
        Write-Host "删除: $($_.FullName)" -ForegroundColor Gray
        Remove-Item $_.FullName -Recurse -Force
    }

    # 清理 .pytest_cache
    $pytestCache = Join-Path $ProjectRoot ".pytest_cache"
    if (Test-Path $pytestCache) {
        Write-Host "删除: $pytestCache" -ForegroundColor Gray
        Remove-Item $pytestCache -Recurse -Force
    }

    # 清理日志文件
    Get-ChildItem -Path $LogsDir -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "删除: $($_.FullName)" -ForegroundColor Gray
        Remove-Item $_.FullName -Force
    }

    Write-Host "清理完成" -ForegroundColor Green
}

function Build-Project {
    Write-Host "检查 Python 语法..." -ForegroundColor Yellow

    $serverScript = Join-Path $ProjectRoot "server\app.py"
    $queryScript = Join-Path $ProjectRoot "domain_query\line_query.py"

    python -m py_compile $serverScript
    python -m py_compile $queryScript

    Write-Host "语法检查通过" -ForegroundColor Green
}

function Deploy-Project {
    Write-Host "开始部署流程..." -ForegroundColor Cyan

    Clean-Project
    Install-Dependencies
    Build-Project
    Run-Tests

    Write-Host ""
    Write-Host "部署准备完成" -ForegroundColor Green
    Write-Host "请确保 .env 文件配置正确" -ForegroundColor Yellow
    Write-Host "运行 '.\manage.ps1 start' 启动服务" -ForegroundColor Yellow
}

# 主命令分发
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "run" { Start-ServiceForeground }
    "start" { Start-ServiceBackground }
    "stop" { Stop-Service }
    "restart" { Restart-Service }
    "status" { Show-Status }
    "logs" { Show-Logs }
    "test" { Run-Tests }
    "clean" { Clean-Project }
    "build" { Build-Project }
    "deploy" { Deploy-Project }
    default {
        Write-Host "未知命令: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
