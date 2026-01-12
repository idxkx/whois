## ADDED Requirements
### Requirement: 行分割域名查询编排
系统 SHALL 接收一段文本或字符串数组，按换行切分并去除首尾空白，仅保留非空行作为基础域名片段，再与检索配置中的域名后缀列表逐一组合后执行批量 whois 查询。

#### Scenario: 成功解析并查询
- **GIVEN** 输入文本含有若干以换行分隔的候选词，且配置提供至少一个启用的域名后缀
- **WHEN** 系统解析文本、生成 `基础片段 + 后缀` 的全部组合，并向 `https://api.whoiscx.com/whois/?domain=<组合结果>` 发送请求
- **THEN** 针对每个组合返回结构化结果 `{domain, domain_suffix, is_registered}`，其中 `is_registered = data.is_available == 0`

#### Scenario: 配置为空
- **GIVEN** 文本输入合法但未配置任何域名后缀
- **WHEN** 触发行分割域名查询
- **THEN** 系统 SHALL 返回“无后缀可查询”的错误并跳过远程调用