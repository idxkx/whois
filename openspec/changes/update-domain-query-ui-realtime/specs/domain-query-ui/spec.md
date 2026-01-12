## MODIFIED Requirements
### Requirement: 域名批量查询 API/界面
系统 SHALL 提供一个可通过浏览器访问的接口（Swagger 或 Web 表单），允许用户粘贴多行候选名称并触发批量 whois 查询，返回每个组合域名是否已被注册。

#### Scenario: Swagger 发起批量查询
- **GIVEN** 用户访问 Swagger UI 并调用 POST /domain-query/batch
- **WHEN** 请求体包含字段 text（多行字符串）或 lines（字符串数组），系统解析文本并调用既有行分割+后缀组合逻辑
- **THEN** 响应 SHALL 返回 200，body 包含 items 数组，每项提供 domain、domain_suffix、is_registered、query_time

#### Scenario: Web 表单查询成功
- **GIVEN** 用户打开 /ui/domain-query 页面，粘贴候选列表并点击“查询”
- **WHEN** 页面向后端 API 发送请求，并通过实时通道（如 SSE/轮询）接收逐条进度
- **THEN** 页面 SHALL 即时显示“正在查询/已注册/未注册”等状态，展示已完成/总数，并在检测到未注册结果时加入“未注册列表”分区

#### Scenario: 输入无效
- **GIVEN** 请求体为空或解析后无有效行
- **WHEN** 发起查询
- **THEN** API SHALL 返回 400 并附带“无有效域名片段”错误描述

#### Scenario: 未注册导出
- **GIVEN** 页面中出现未注册列表
- **WHEN** 用户点击“导出未注册”
- **THEN** 浏览器 SHALL 生成包含所有未注册域名（每行一个）的 txt 文件并触发下载

#### Scenario: 查询过程中断
- **GIVEN** whois 接口返回限频/错误
- **WHEN** 后端无法继续查询
- **THEN** 页面 SHALL 即时显示错误原因，并允许用户在原输入基础上重试