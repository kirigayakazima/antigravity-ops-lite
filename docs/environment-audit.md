# Antigravity 2.0 本机环境审计报告 (Environment Audit)

**审计时间**: 2026-10-21  
**审计执行者**: Antigravity Agent  
**操作系统**: Windows 11 (amd64)  
**工作区根目录**: `d:\CodePackage\反重力`  

---

## 1. 核心运行环境

| 组件 | 版本 / 路径 | 状态 | 详细说明 |
| :--- | :--- | :--- | :--- |
| **Python** | 3.14.7 (`C:\Python314\python.exe`) | **CONFIRMED** | 具备标准 `venv` 支持；`pip 26.2.1` 可正常访问 PyPI 解析与安装包。 |
| **Git** | 2.47.1.windows.1 | **CONFIRMED** | Windows 下原生 Git 正常可用。 |
| **agy CLI** | 1.3.3 (`C:\Users\xuaner\AppData\Local\agy\bin\agy.exe`) | **CONFIRMED** | 原生 CLI，提供 `plugin`, `mcp`, `agent`, `sandbox` 等完整子命令。 |
| **Language Server** | hub-2.24.0 (`localhost:11070`) | **CONFIRMED** | 正在运行，Connect RPC `/healthz` 正常响应；支持 `GetAllPlugins`、`JetboxWriteState` 等。 |
| **MCP SDK** | Python `mcp 2.3.0` | **CONFIRMED** | MCP 2.x 正式架构，使用 `from mcp.server.mcpserver import MCPServer` 代替已废弃的 FastMCP。 |
| **Ripgrep (`rg`)** | 缺失 (系统 PATH 及 Antigravity 目录下均无) | **UNSUPPORTED** | 需使用优化纯 Python 实现的搜索遍历器作为核心兜底，预留外部 `rg` 适配接口。 |

---

## 2. 插件体系与定制能力审计

### 2.1 插件机制 (Plugins)
* **状态**: **CONFIRMED**
* **全局插件目录**: `C:\Users\xuaner\.gemini\config\plugins\<plugin_name>`
* **清单规范 (`plugin.json`)**:
  ```json
  {
    "name": "ops-lite",
    "description": "...",
    "version": "0.1.0"
  }
  ```
* **CLI 支持**:
  * `agy plugin validate <dir>`: 实测通过，可静态检验 `skills`, `agents`, `commands`, `mcpServers`, `hooks`。
  * `agy plugin install <dir>`: 实测通过，接受本地目录参数并部署至全局插件目录。
  * `agy plugin uninstall <name>`: 实测通过，干净卸载插件。
  * `agy plugin enable <name>` / `disable <name>`: 实测通过。
* **运行时发现**: Language Server 启动或热重载时自动遍历扫描 `~/.gemini/config/plugins` 目录。

### 2.2 MCP 服务器配置 (Model Context Protocol)
* **状态**: **CONFIRMED**
* **配置规范 (`mcp_config.json`)**:
  放在插件根目录下：
  ```json
  {
    "mcpServers": {
      "ops-lite": {
        "command": "path/to/.venv/Scripts/python.exe",
        "args": ["-m", "ops_lite.server"],
        "env": {}
      }
    }
  }
  ```
* **通信协议**: Stdio 模式，基于标准 JSON-RPC 2.0；MCP 2.x `MCPServer` 支持标准 stdio 传输。
* **隔离与安全要求**:
  * stdout 必须严格保留给 MCP 协议 JSON 帧；
  * 所有诊断、调试信息必须输出到 stderr 或本地日志文件。

### 2.3 规则机制 (Rules)
* **状态**: **CONFIRMED**
* **规则文件规范**: 插件内位于 `rules/AGENTS.md`（推荐规范，无 frontmatter，插件启用时自动激活并合并）。
* **预算约束**: 全局规则共享 20,000 tokens 预算，单文件上限 24,000 字节。`ops-lite` 规则应保持精简，复杂流程下沉至 Skills。

### 2.4 技能机制 (Skills)
* **状态**: **CONFIRMED**
* **技能目录结构**:
  ```text
  skills/<skill_name>/
  ├── SKILL.md          # 包含 YAML frontmatter (name, description)
  └── references/       # 可选的按需长文档
  ```
* **渐进式披露**: 初始仅向模型上下文注入 `name` 和 `description`，只有模型显式激活技能时才注入正文，符合 Token 优化目标。

### 2.5 钩子机制 (Hooks)
* **状态**: **CONFIRMED** (但第一版不强制依赖)
* **规范**: 插件根目录 `hooks.json`，支持 `SessionStart`, `SessionEnd`, `BeforeAgent`, `BeforeTool`, `AfterAgent` 等事件。

---

## 3. 审计结论与架构适配决策

1. **安装方案**:
   - `scripts/install.ps1` 将在项目目录内建立独立的 Python 虚拟环境 `.venv`，安装固定版本依赖 `mcp==2.3.0` 等；
   - 生成指向该虚拟环境绝对 Python 路径的 `mcp_config.json`；
   - 调用 `agy plugin install .` 将插件注册进全局插件环境；或在未开启全局安装时支持工作区模式与回滚。
2. **MCP SDK 选型**:
   - 使用官方 `mcp==2.3.0`，代码适配 MCP 2.x API（使用 `from mcp.server.mcpserver import MCPServer`）；
   - 保持服务端轻量化，无不必要的网络与进程开销。
3. **搜索实现**:
   - 本机无 `rg.exe`，因此以 Python 高性能内置并发/分批搜索（结合 `.gitignore` / 默认忽略黑名单）为主实现，同时兼顾 Windows 长路径与编码问题；若检测到 PATH 存在 `rg`，自动提升性能。
4. **测试与安全边界**:
   - 所有路径解析严格限制在 workspace 根目录内，禁止 `..` 越界与敏感文件访问（如 `.env`, `.git/config` 等凭据）。
