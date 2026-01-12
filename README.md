# WhoisAI 域名查询系统

域名批量查询服务，提供 HTTP API 和 Web 界面。

## 快速开始

### 1. 配置环境

复制 `.env.example` 到 `.env` 并根据需要修改配置：

```bash
cp .env.example .env
```

### 2. 启动服务

**使用 PowerShell（推荐）：**
```powershell
.\manage.ps1 start
```

**使用 Makefile（需要安装 make）：**
```bash
make start
```

**直接运行：**
```bash
python server/app.py
```

### 3. 访问服务

- Web 界面：http://127.0.0.1:8888/ui/domain-query
- Swagger 文档：http://127.0.0.1:8888/swagger

## 管理命令

### PowerShell 脚本（Windows 推荐）

```powershell
# 查看所有可用命令
.\manage.ps1 help

# 安装依赖
.\manage.ps1 install

# 前台运行服务（开发调试）
.\manage.ps1 run

# 后台启动服务
.\manage.ps1 start

# 停止服务
.\manage.ps1 stop

# 重启服务
.\manage.ps1 restart

# 查看服务状态
.\manage.ps1 status

# 查看日志
.\manage.ps1 logs

# 运行测试
.\manage.ps1 test

# 清理临时文件
.\manage.ps1 clean

# 构建项目（语法检查）
.\manage.ps1 build

# 完整部署流程
.\manage.ps1 deploy
```

### Makefile（需要安装 make）

```bash
# 查看所有可用命令
make help

# 其他命令与 PowerShell 脚本相同
make install
make start
make stop
make status
make logs
make test
make clean
make build
make deploy
```

## 安装 Make（可选）

如果你想使用 Makefile，需要安装 make 工具：

**使用 Chocolatey：**
```powershell
choco install make
```

**使用 winget：**
```powershell
winget install GnuWin32.Make
```

**使用 Git Bash：**
Git for Windows 通常包含 make，可以在 Git Bash 中使用。

## 项目结构

```
whoisai/
├── server/              # HTTP 服务器
│   └── app.py          # 主服务文件
├── domain_query/        # 域名查询模块
│   └── line_query.py   # 查询逻辑
├── static/             # 静态文件
│   ├── domain_query_ui.html
│   ├── swagger.html
│   └── swagger.json
├── tests/              # 测试文件
├── config/             # 配置文件
│   └── domain_suffixes.json
├── logs/               # 日志目录
├── .env                # 环境配置
├── manage.ps1          # PowerShell 管理脚本
├── Makefile            # Make 管理脚本
└── README.md           # 本文件
```

## API 使用

### 批量查询域名

**请求：**
```bash
curl -X POST http://127.0.0.1:8888/domain-query/batch \
  -H "Content-Type: application/json" \
  -d '{"text": "example\ntest"}'
```

**响应：**
```json
{
  "items": [
    {
      "domain": "example.com",
      "domain_suffix": ".com",
      "is_registered": true,
      "query_time": "2026-01-12T12:00:00"
    }
  ]
}
```

### 流式查询

```bash
curl -X POST http://127.0.0.1:8888/domain-query/batch-stream \
  -H "Content-Type: application/json" \
  -d '{"text": "example\ntest"}'
```

## 配置说明

`.env` 文件配置项：

```bash
# 服务监听地址
DOMAIN_QUERY_HOST=127.0.0.1

# 服务监听端口
DOMAIN_QUERY_PORT=8888

# 域名后缀配置文件路径（可选）
# DOMAIN_QUERY_CONFIG=config/domain_suffixes.json
```

## 开发

### 运行测试

```powershell
.\manage.ps1 test
```

或

```bash
python -m pytest tests/ -v
```

### 代码检查

```powershell
.\manage.ps1 build
```

## 故障排查

### 端口被占用

如果 8888 端口被占用，可以：

1. 修改 `.env` 文件中的 `DOMAIN_QUERY_PORT`
2. 或查看占用端口的进程：
   ```powershell
   netstat -ano | findstr :8888
   ```

### 服务无法启动

1. 检查 Python 是否正确安装：
   ```bash
   python --version
   ```

2. 查看错误日志：
   ```powershell
   .\manage.ps1 logs
   ```

3. 检查服务状态：
   ```powershell
   .\manage.ps1 status
   ```

## 许可证

本项目使用的许可证信息请查看项目根目录。
