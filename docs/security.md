# ops-lite 安全与可靠性规范 (Security & Reliability)

## 1. 威胁模型与防御策略

| 威胁类型 | 潜在攻击场景 | ops-lite 防护措施 |
| :--- | :--- | :--- |
| **路径越界 (Path Traversal)** | 参数中包含 `../`、UNC 路径或绝对外部路径以试图读取系统核心文件（如 SAM, hosts） | `validate_and_resolve_path` 将路径解析为绝对规范路径，严格校验必须位于允许的 Workspace 根目录内，越界时抛出 `PolicyViolation`。 |
| **敏感文件窃取** | 试图读取 `.env`, 私钥 (`id_rsa`, `.pem`), 令牌文件 | 黑名单机制严格拒绝所有敏感凭据名称与扩展名访问。 |
| **凭据泄漏 (Secret Leakage)** | 源码、终端日志中包含 API Key、AWS 密钥或 JWT | 集中式正则脱敏器对匹配项进行强替换（如 `[REDACTED_SECRET]`, `[REDACTED_JWT]`）。 |
| **命令注入 (Command Injection)** | 通过 `ops_run` 拼接 `; rm -rf` 或任意 shell 命令 | 严禁任意 shell 执行。`ops_run` 仅接受受限的 schema 枚举任务（`verify`, `git_summary`, `inspect`），子进程命令由项目配置静态映射，参数以数组形式调用 `subprocess.run`，不使用 `shell=True`。 |
| **上下文溢出与 DoS** | 超大文件读取、死循环进程导致输出无限膨胀 | 实施全链路硬上限约束：单次读取限制、搜索上限、日志尾部保留机制（25 行 tail）以及执行超时保护（默认 10-60s）。 |
| **未授权网络访问** | MCP 服务暴露未授权端口 | MCP Server 仅绑定操作系统本地 Stdio，不暴露外部网络端口。 |

## 2. 凭据过滤规则清单

- **JWT 令牌**: `eyJ[a-zA-Z0-9_\-]{10,}\.eyJ...` -> `[REDACTED_JWT]`
- **GitHub 访问令牌**: `gh[pousr]_[A-Za-z0-9_]{36,255}` -> `[REDACTED_GITHUB_TOKEN]`
- **AWS 访问密钥**: `\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b` -> `[REDACTED_AWS_KEY]`
- **HTTP Bearer 标头**: `Bearer \S+` -> `Bearer [REDACTED_TOKEN]`
- **通用 API 密钥**: `api_key = '...'`, `secret = '...'`, `password = '...'` 等键值匹配。

## 3. 运行可靠性保障

1. **测试驱动安全验证**:
   所有安全边界（路径越界、敏感文件访问、超长字符串截断、脱敏、ID 穿透防御）均在 `server/tests/test_policy.py` 和 `test_results.py` 中覆盖自动化单元测试。
2. **非破坏性设计**:
   ops-lite 工具默认均为**只读与诊断性质**，不提供自动提交 Git、强制推流或删除文件的高危操作，保护用户代码资产安全。
