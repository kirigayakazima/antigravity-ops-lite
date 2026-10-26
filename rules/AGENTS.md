# Script-First Operations

For repository inspection, repetitive file operations, search, diagnostics, and verification:

1. **Prefer ops-lite tools**: Use `ops_summary`, `ops_glob`, `ops_grep`, `ops_read_files`, `ops_replace`, `ops_batch`, `ops_read_table`, and `ops_run` whenever they cover the task.
2. **Discover before reading**: Use `ops_glob` to list relevant files by pattern rather than invoking noisy terminal directory commands.
3. **Filter-first search**: Use `ops_grep` with `files_with_matches` or `count` when discovering candidate files, reserving `content` mode for necessary context.
4. **Batch file reads**: Inspect 1-32 related files simultaneously via `ops_read_files` in a single tool call rather than issuing multiple round-trip reads.
5. **Respect read deduplication**: Unmodified files already read in the current session are automatically deduplicated to conserve tokens. Do not repeatedly re-read static files without `force=True`.
6. **Deterministic cross-file replacement**: Use `ops_replace` with `dry_run=True` to preview literal text replacements across files before applying them.
7. **Safe file batch operations**: Use `ops_batch` with `action="plan"` to preflight copy/move/remove operations before executing them with `action="run"`.
8. **Bounded table viewing**: Use `ops_read_table` to inspect CSV/TSV data in compact markdown tables rather than dumping raw file text.
9. **Batch verification**: Execute format, test, build, and git summary checks together via `ops_run`.
10. **Paginate via references**: Use `ops_result` to retrieve additional output only when the returned summary or initial preview is insufficient.
11. **Preserve reasoning & evidence**: Never hide errors or truncate evidence required for correct decisions. Read source directly when architecture, semantics, or safety requires it.
12. **Graceful fallback**: If ops-lite is unavailable or unsuitable, fall back to native tools and continue the task.
