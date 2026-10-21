# Antigravity 2.0 `ops-lite` 插件

> 面向 Windows 平台的 Antigravity 2.0 Agent 脚本优先与 Token 深度优化插件。

---

## 1. 核心价值与优化指标

在日常开发与多轮对话中，Agent 常常因反复读取整个文件、进行大范围零碎终端命令执行、陷入超大日志泥潭而浪费巨额输入/输出 Token，并导致上下文窗口快速耗尽。

`ops-lite` 借鉴确定性脚本优先思路，通过封装高质量原子工具与渐进式披露机制，在不篡改 Antigravity 宿主二进制与系统环境的前提下，实现了大幅性能与效率飞跃：

- **Token 代理字符吞吐量降低 93.9%**（基准测试 71,506 字符降至 4,343 字符）；
- **工具调用轮次降低 76.2%**（从 21 轮交互往返缩减至 5 轮）；
- **上下文爆炸防护**：大输出自动沉淀至受限本地 `ResultStore`，仅向上下文返回短摘要与安全引用 ID，支持按需分页拉取；
- **全链路安全防护**：内置严格路径沙箱、凭据正则脱敏、敏感文件黑名单与命令白名单。

---

## 2. 工具矩阵

| 工具名称 | 作用说明 | 典型输入示例 |
| :--- | :--- | :--- |
| **`ops_summary`** | 快速扫描工程元数据、构建配置、入口文件与 2 级精简目录树。 | `ops_summary(path=".")` |
| **`ops_search`** | 排除构建与依赖噪点，进行符号/代码段有限上下文搜索，超限自动分页。 | `ops_search(query="getUserById", path="src")` |
| **`ops_read`** | 精准读取文件指定行区间（1-indexed），附带行号与 SHA-256 哈希校验。 | `ops_read(path="src/main.py", start_line=10, end_line=30)` |
| **`ops_run`** | 批处理预定义安全的流水线任务（`verify`, `git_summary`, `inspect`），拒绝任意 Shell 拼接。 | `ops_run(task="verify", checks=["test"])` |
| **`ops_result`** | 使用 `result_id` 分页拉取历史超限日志或搜索结果。 | `ops_result(result_id="res_xxx", offset=0, limit=20)` |

---

## 3. 快速安装与配置

### 3.1 一键安装 (PowerShell)

在当前插件目录中以管理员或普通用户运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

安装流程自动完成：
1. 检查 Python 3.10+、Git 与 `agy` CLI 环境；
2. 在项目内建立独立虚拟环境 `.venv` 并安装 `mcp>=2.3.0` 等依赖；
3. 生成正确的 `mcp_config.json`；
4. 运行全量单元测试与安全测试；
5. 调用 `agy plugin install .` 将插件注册进全局 Antigravity 插件中心。

### 3.2 卸载

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

卸载脚本仅移除本插件注册项及关联缓存，不触碰任何用户项目文件或其它插件。

---

## 4. 目录结构

```text
.
├── plugin.json                 # Antigravity 插件清单
├── mcp_config.json             # MCP 服务器配置
├── rules/
│   ├── AGENTS.md               # 脚本优先自动生效规则
│   └── script-first.md
├── skills/                     # 渐进式披露技能
│   ├── repo-inspection/
│   ├── efficient-editing/
│   └── verify-changes/
├── server/
│   ├── pyproject.toml
│   ├── ops_lite/               # 核心服务端实现 (MCP 2.x)
│   └── tests/                  # 26 项单元与边界测试
├── scripts/
│   ├── install.ps1             # 安装与注册脚本
│   ├── uninstall.ps1           # 干净卸载脚本
│   └── benchmark.ps1           # A/B 基准测量脚本
└── docs/
    ├── environment-audit.md    # 本机环境实测审计
    ├── architecture.md         # 架构设计
    ├── security.md             # 安全与脱敏规范
    └── benchmark.md            # A/B 实测数据报告
```

---

## 5. 许可证

本项目基于 MIT License 开源。
