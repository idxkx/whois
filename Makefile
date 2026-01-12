# WhoisAI 域名查询系统 Makefile
# 用于管理项目的编译、部署、日志查看、服务控制等操作

.PHONY: help install run start stop restart status logs test clean build deploy

# 默认目标
help:
	@echo "WhoisAI 域名查询系统 - 可用命令:"
	@echo ""
	@echo "  make install    - 安装项目依赖"
	@echo "  make run        - 前台运行服务（用于开发调试）"
	@echo "  make start      - 后台启动服务"
	@echo "  make stop       - 停止服务"
	@echo "  make restart    - 重启服务"
	@echo "  make status     - 查看服务状态"
	@echo "  make logs       - 查看服务日志"
	@echo "  make test       - 运行测试"
	@echo "  make clean      - 清理临时文件和缓存"
	@echo "  make build      - 构建项目（检查语法）"
	@echo "  make deploy     - 部署项目"
	@echo ""

# 安装依赖
install:
	@echo "检查 Python 环境..."
	@python --version
	@echo "安装项目依赖..."
	@if exist requirements.txt (pip install -r requirements.txt) else (echo "未找到 requirements.txt，跳过依赖安装")
	@echo "依赖安装完成"

# 前台运行服务（开发模式）
run:
	@echo "启动服务（前台运行）..."
	@python server/app.py

# 后台启动服务
start:
	@echo "后台启动服务..."
	@powershell -Command "Start-Process python -ArgumentList 'server/app.py' -WindowStyle Hidden -RedirectStandardOutput logs/server.log -RedirectStandardError logs/error.log"
	@timeout /t 2 /nobreak >nul
	@echo "服务已启动，日志文件: logs/server.log"
	@make status

# 停止服务
stop:
	@echo "正在停止服务..."
	@powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$$_.CommandLine -like '*server/app.py*'} | Stop-Process -Force"
	@echo "服务已停止"

# 重启服务
restart: stop start
	@echo "服务已重启"

# 查看服务状态
status:
	@echo "检查服务状态..."
	@powershell -Command "$$proc = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$$_.CommandLine -like '*server/app.py*'}; if ($$proc) { Write-Host '服务运行中 - PID:' $$proc.Id -ForegroundColor Green } else { Write-Host '服务未运行' -ForegroundColor Red }"
	@echo ""
	@echo "检查端口占用..."
	@netstat -ano | findstr :8888 || echo "端口 8888 未被占用"

# 查看日志
logs:
	@if exist logs\server.log (type logs\server.log) else (echo "日志文件不存在")
	@echo ""
	@echo "=== 错误日志 ==="
	@if exist logs\error.log (type logs\error.log) else (echo "错误日志文件不存在")

# 运行测试
test:
	@echo "运行测试..."
	@python -m pytest tests/ -v

# 清理临时文件
clean:
	@echo "清理临时文件..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist domain_query\__pycache__ rmdir /s /q domain_query\__pycache__
	@if exist server\__pycache__ rmdir /s /q server\__pycache__
	@if exist tests\__pycache__ rmdir /s /q tests\__pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist logs\*.log del /q logs\*.log
	@echo "清理完成"

# 构建项目（语法检查）
build:
	@echo "检查 Python 语法..."
	@python -m py_compile server/app.py
	@python -m py_compile domain_query/line_query.py
	@echo "语法检查通过"

# 部署项目
deploy: clean install build test
	@echo "部署准备完成"
	@echo "请确保 .env 文件配置正确"
	@echo "运行 'make start' 启动服务"
