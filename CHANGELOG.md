# Changelog

All notable changes to the `ops-lite` plugin will be documented in this file.

## [0.2.0] - 2026-10-26

### Added
- **Multi-File Batch Reading (`ops_read_files`)**: Read bounded ranges across 1-32 files in a single tool call with per-file error isolation.
- **Pattern File Discovery (`ops_glob`)**: Supports glob patterns with exclusions (`!vendor/**`), sorting by path/modification time, and file size metadata.
- **Advanced Regular Expression Search (`ops_grep`)**: Multi-mode search supporting `content` (with context lines), `files_with_matches` (file list only), `count`, and `summary`.
- **Deterministic Cross-File Replacement (`ops_replace`)**: Literal string replacement across files with `dry_run` preview support.
- **Safe Batch File Operations (`ops_batch`)**: Structured preflight validation (`plan`) and execution (`run`) of copy, move, and remove operations.
- **Bounded Table Reader (`ops_read_table`)**: Automatic delimiter detection for CSV/TSV, pagination, and aligned markdown table rendering.
- **In-Session Read Deduplication**: Caches file hash per range to prevent re-reading identical files within the same session.
- **Data Inspection Skill (`skills/data-inspection/`)**: Guide for viewing tabular datasets with `ops_read_table`.
- **Robust Windows Installation**: Enhanced `install.ps1` with in-place synchronization fallback when Language Server holds directory file locks.
- **13 New Unit Tests**: Test suite expanded to 39 tests with 100% pass rate.

## [0.1.0] - 2026-10-21

### Added
- Complete environment audit on Windows 11 with Antigravity 2.0 (Language Server hub-2.24.0, agy CLI 1.3.3).
- MCP 2.x server implementation supporting stdio transport.
- Five atomic tools: `ops_summary`, `ops_search`, `ops_read`, `ops_run`, `ops_result`.
- Security layer with workspace jail confinement, sensitive file blacklists, and credential regex redaction.
- Rules (`rules/AGENTS.md`, `rules/script-first.md`) and 3 Skills (`repo-inspection`, `efficient-editing`, `verify-changes`).
- Automated PowerShell installer (`install.ps1`), uninstaller (`uninstall.ps1`), and A/B benchmark runner (`benchmark.ps1`).
