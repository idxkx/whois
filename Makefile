# WhoisAI 域名查询系统 Makefile
# 用于管理项目的编译、部署、日志查看、服务控制等操作

# 检测 Python 命令
PYTHON := $(shell command -v python3 2> /dev/null || command -v python 2> /dev/null)
PIP := $(shell command -v pip3 2> /dev/null || command -v pip 2> /dev/null)

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
	@if [ -z "$(PYTHON)" ]; then \
		echo "错误: 未找到 Python，请先安装 Python3"; \
		exit 1; \
	fi
	@$(PYTHON) --version
	@echo "安装项目依赖..."
	@if [ -f requirements.txt ]; then \
		$(PIP) install -r requirements.txt; \
	else \
		echo "未找到 requirements.txt，跳过依赖安装"; \
	fi
	@echo "依赖安装完成"

# 前台运行服务（开发模式）
run:
	@echo "启动服务（前台运行）..."
	@$(PYTHON) server/app.py

# 后台启动服务
start:
	@echo "后台启动服务..."
	@mkdir -p logs
	@nohup $(PYTHON) server/app.py > logs/server.log 2> logs/error.log &
	@sleep 2
	@echo "服务已启动，日志文件: logs/server.log"
	@$(MAKE) status

# 停止服务
stop:
	@echo "正在停止服务..."
	@pkill -f "server/app.py" || echo "未找到运行中的服务"
	@echo "服务已停止"

# 重启服务
restart: stop start
	@echo "服务已重启"

# 查看服务状态
status:
	@echo "检查服务状态..."
	@if pgrep -f "server/app.py" > /dev/null; then \
		echo "服务运行中 - PID: $$(pgrep -f 'server/app.py')"; \
		ps aux | grep "server/app.py" | grep -v grep; \
	else \
		echo "服务未运行"; \
	fi
	@echo ""
	@echo "检查端口占用..."
	@netstat -tlnp 2>/dev/null | grep :8888 || ss -tlnp 2>/dev/null | grep :8888 || echo "端口 8888 未被占用"

# 查看日志
logs:
	@if [ -f logs/server.log ]; then \
		tail -n 50 logs/server.log; \
	else \
		echo "日志文件不存在"; \
	fi
	@echo ""
	@echo "=== 错误日志 ==="
	@if [ -f logs/error.log ]; then \
		tail -n 50 logs/error.log; \
	else \
		echo "错误日志文件不存在"; \
	fi

# 运行测试
test:
	@echo "运行测试..."
	@$(PYTHON) -m pytest tests/ -v

# 清理临时文件
clean:
	@echo "清理临时文件..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -f logs/*.log 2>/dev/null || true
	@echo "清理完成"

# 构建项目（语法检查）
build:
	@echo "检查 Python 语法..."
	@$(PYTHON) -m py_compile server/app.py
	@$(PYTHON) -m py_compile domain_query/line_query.py
	@echo "语法检查通过"

# 部署项目
deploy: clean install build test
	@echo "部署准备完成"
	@echo "请确保 .env 文件配置正确"
	@echo "运行 'make start' 启动服务"
