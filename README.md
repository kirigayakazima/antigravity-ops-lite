# Antigravity 2.0 `ops-lite` 插件 (v0.2.0)

> 面向 Windows 平台 Antigravity 2.0 Agent 的脚本优先与 Token 深度优化插件。
> 参考并深度融合 [T-Auto/dsh-ops](https://github.com/T-Auto/dsh-ops) 设计模式。

---

## 1. 核心价值与优化指标

在日常软件开发任务中，Agent 常常因反复读取整个文件、进行大范围零碎终端命令执行、陷入超大日志泥潭而浪费巨额输入/输出 Token，并导致上下文窗口快速耗尽。

`ops-lite` 借鉴确定性脚本优先思路与 `dsh-ops` 的现代工程设计，通过封装高质量原子工具与渐进式披露机制，在不篡改 Antigravity 宿主二进制的前提下实现大幅性能飞跃：

- **Token 代理字符吞吐量降低 93.9%**（基准测试 71,506 字符降至 4,343 字符）；
- **工具调用轮次降低 76.2%**（从 21 轮交互往返缩减至 5 轮）；
- **上下文爆炸防护**：大输出自动沉淀至受限本地 `ResultStore`，仅向上下文返回短摘要与安全引用 ID，支持按需分页拉取；
- **读取去重与会话缓存**：同会话内重复读取相同 Hash 文件自动标记并跳过重复正文；
- **全链路安全防护**：内置严格路径沙箱、凭据正则脱敏、敏感文件黑名单与命令白名单。

---

## 2. 工具矩阵 (全量 10 工具)

| 工具名称 | 作用说明 | 典型输入示例 |
| :--- | :--- | :--- |
| **`ops_summary`** | 快速扫描工程元数据、构建配置、入口文件与 2 级精简目录树。 | `ops_summary(path=".")` |
| **`ops_glob`** | 模式匹配文件发现（支持负向排除 `!vendor/**`），支持按大小/修改时间排序。 | `ops_glob(patterns=["**/*.py", "!tests/**"], sort="modified")` |
| **`ops_grep`** | 正则搜索，支持 `content`, `files_with_matches`, `count`, `summary` 多种输出模式。 | `ops_grep(pattern="class MyService", output_mode="files_with_matches")` |
| **`ops_search`** | 关键字快速搜索，附带有限上下文与自动分页。 | `ops_search(query="getUserById", path="src")` |
| **`ops_read`** | 单文件精准区间读取（1-indexed），附带行号、SHA-256 哈希校验与会话去重。 | `ops_read(path="src/main.py", start_line=10, end_line=30)` |
| **`ops_read_files`** | **多文件批量读取（1-32 个文件）**，一次调用获取全部所需文件，隔离单文件错误。 | `ops_read_files(files=[{"path": "a.py"}, {"path": "b.py"}])` |
| **`ops_replace`** | **确定性跨文件字面量替换**，支持 `dry_run=True` 预演防误伤。 | `ops_replace(pattern="oldFunc", replacement="newFunc", dry_run=True)` |
| **`ops_batch`** | **文件批量安全操作（copy/move/remove）**，支持 `plan` 预检与 `run` 事务执行。 | `ops_batch(action="plan", operations=[{"op": "copy", "path": "a", "to": "b"}])` |
| **`ops_read_table`** | **CSV/TSV 有界表格解析器**，自动推断分隔符，渲染紧凑对齐的 Markdown 表格。 | `ops_read_table(path="metrics.csv", offset=1, limit=20)` |
| **`ops_run`** | 批处理预定义安全的流水线任务（`verify`, `git_summary`, `inspect`）。 | `ops_run(task="verify", checks=["test"])` |
| **`ops_result`** | 使用 `result_id` 分页拉取历史超限日志或搜索结果。 | `ops_result(result_id="res_xxx", offset=0, limit=20)` |

---

## 3. 技能列表 (Skills)

1. **`repo-inspection`**：结合 `ops_summary`、`ops_glob` 与 `ops_grep` 探索陌生仓库与定位代码。
2. **`efficient-editing`**：结合 `ops_read_files`、`ops_replace` 与 `ops_batch` 进行无冗余代码重构与变更。
3. **`verify-changes`**：通过 `ops_run` 批处理运行测试与构建检查，尾部裁剪日志。
4. **`data-inspection`**：通过 `ops_read_table` 高效查看表格数据集。

---

## 4. 快速安装与配置

### 4.1 一键安装 (PowerShell)

在当前插件目录中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

安装流程自动完成：
1. 检查 Python 3.10+、Git 与 `agy` CLI 环境；
2. 建立独立虚拟环境 `.venv` 并安装 `mcp>=2.3.0` 等依赖；
3. 生成正确的 `mcp_config.json`；
4. 运行全量 39 项单元与安全测试；
5. 将插件注册进全局 Antigravity 插件中心（含文件锁鲁棒同步机制）。

### 4.2 卸载

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

---

## 5. 许可证

本项目基于 MIT License 开源。
参考项目：[T-Auto/dsh-ops](https://github.com/T-Auto/dsh-ops) (MIT License)。
