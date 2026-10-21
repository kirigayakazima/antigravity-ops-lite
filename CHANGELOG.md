# Changelog

All notable changes to the `ops-lite` plugin will be documented in this file.

## [0.1.0] - 2026-10-21

### Added
- Complete environment audit on Windows 11 with Antigravity 2.0 (Language Server hub-2.24.0, agy CLI 1.3.3).
- MCP 2.x server implementation supporting stdio transport.
- Five atomic tools:
  - `ops_summary`: Project metadata inspection and limited-depth tree summary.
  - `ops_search`: Text/symbol search with context, globs, and auto-pagination.
  - `ops_read`: Bounded line reading with line numbers and SHA-256 validation.
  - `ops_run`: Deterministic batch execution (`verify`, `git_summary`, `inspect`).
  - `ops_result`: Local paginated store for retrieving large operation outputs.
- Security layer with workspace jail confinement, sensitive file blacklists, and credential regex redaction.
- Rules (`rules/AGENTS.md`, `rules/script-first.md`) enforcing script-first operations.
- Three skills (`repo-inspection`, `efficient-editing`, `verify-changes`).
- Automated PowerShell installer (`install.ps1`), uninstaller (`uninstall.ps1`), and A/B benchmark runner (`benchmark.ps1`).
- 26 comprehensive unit tests passing with 100% success.
- Documentation: `environment-audit.md`, `architecture.md`, `security.md`, `benchmark.md`.
