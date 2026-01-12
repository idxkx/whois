# Change: 域名批量查询界面/Swagger

## Why
目前的行分割域名查询能力只能通过代码触发，运营或其他同学无法直接体验，需要提供一个简单界面或 Swagger 控制台来发起批量查询并查看“是否已注册”结果。

## What Changes
- 提供一个 HTTP 服务，暴露批量域名查询接口，接收多行文本输入并调用既有解析+whois 编排逻辑。
- 使用自动生成的 Swagger（或等效交互文档）供用户在浏览器里粘贴文本并执行请求。
- 可选：提供一个极简 Web 表单（textarea + 查询按钮）作为更友好的界面，底层仍调用同一 API。
- 返回结果包含域名、后缀、是否注册，并展示错误原因。

## Impact
- Affected specs: domain-query-ui
- Affected code: HTTP 服务入口、Swagger 定义、（可选）Web 表单资源