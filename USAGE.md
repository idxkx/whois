# 域名批量查询使用说明

## 1. 准备域名后缀
1. 打开 `config/domain_suffixes.json`。
2. 在 `suffixes` 数组中维护需要查询的后缀，支持两种写法（可混用）：
   - 简写：`"com"`
   - 带状态：`{ "suffix": "com", "enabled": true }`
3. 只有 `enabled: true` 的后缀会参与组合，字符串默认视为启用。

## 2. 提供待查询的域名片段
- 将候选名称整理成多行文本（推荐）或字符串数组，每行对应一个基础片段，例如：
  ```
  alpha
  beta
  gamma-tools
  ```
- 系统会自动按行拆分、裁剪空白并跳过空行。

## 3. 调用编排接口
在任意 Python 模块中调用：

```python
from domain_query.line_query import batch_query_from_text

text_inputs = """
alpha
beta
"""
results = batch_query_from_text(text_inputs)  # 默认读取 config/domain_suffixes.json

for item in results:
    print(item.domain, "已注册" if item.is_registered else "未注册")
```

可选项：
- `config_path="path/to/suffixes.json"`：如果需要使用其他配置文件。
- `client=WhoisApiClient(timeout=5)`：自定义请求超时或扩展行为。
- `batch_query_from_text(..., respect_rate_limit=False, retry_delay=0, max_retries=0)`：关闭限频重试或调整等待间隔，默认情况下系统只在检测到 API “频次/超限” 错误时才等待 `retry_delay`（默认 2 秒）后重试一次。

## 4. 结果解释
- `batch_query_from_text` 返回 `DomainQueryResult` 列表，包含：
  - `domain`：实际查询的完整域名（如 `alpha.com`）
  - `domain_suffix`：解析出的后缀
  - `is_registered`：布尔值，`True` 表示 whoiscx 返回 `is_available == 0`
- 调用失败（如配置缺失、网络异常）会抛出 `DomainQueryError`，捕获后提示用户即可。

## 5. 自检与调试
- 运行 `python -m unittest discover -s tests` 验证解析、后缀过滤和组合逻辑。
- 如需验证真实返回，可在有网络的环境中执行上述示例并观察 whoiscx 响应。

## 6. 启动 Web 界面/Swagger
1. 初始化 `.env`：在 PowerShell 中执行 `./scripts/init_env.ps1`（或 CMD 中执行 `powershell -ExecutionPolicy Bypass -File .\scripts\init_env.ps1`），也可手动复制 `.env.example` 到 `.env`。在文件中维护 `DOMAIN_QUERY_HOST`、`DOMAIN_QUERY_PORT` 以及可选的 `DOMAIN_QUERY_CONFIG`。
2. 在项目根目录运行 `python server/app.py`。程序会读取 `.env` 和环境变量中的配置；亦可通过命令行参数覆盖，例如 `python server/app.py --port 8080`。
3. 访问：
   - `http://127.0.0.1:8000/ui/domain-query`：可视化表单，粘贴多行文本并查看查询结果。
   - `http://127.0.0.1:8000/swagger`：Swagger Playground，可查看 `swagger.json` 并直接调用 `POST /domain-query/batch`。
4. API 入口：`POST http://127.0.0.1:8000/domain-query/batch`，请求体同上。服务端响应结构与 `batch_query_from_text` 返回值一致。
