---
name: repo-inspection
description: >-
  Navigate unfamiliar repositories, investigate bug causes, and explore project architecture
  using script-first bounded summaries, symbol searches, and targeted reads.
---

# Repository Inspection Runbook

Use this skill when exploring an unfamiliar codebase, tracing symbol definitions, or locating the root cause of an issue with minimal token overhead.

## Step-by-Step Workflow

1. **High-Level Overview**:
   - Call `ops_summary(path=".")` to discover the project type, build tool, manifests, configured scripts, entry points, and top-level directory layout.
   - Do NOT read full directory listings or large source files upfront.

2. **Targeted Symbol & Definition Search**:
   - Call `ops_search(query="TargetSymbol", path=".")` to pinpoint definition and usage sites.
   - Use `include` and `exclude` globs to focus on relevant source directories (e.g., `include=["src/**"]`).
   - If search returns more matches than the budget, a `result_id` is provided. Only call `ops_result` if the initial preview lacks necessary context.

3. **Bounded Source Reading**:
   - Inspect specific line ranges around the target symbol using `ops_read(path="...", start_line=..., end_line=...)`.
   - Never read entire large files without line boundaries.

4. **Iterative Evidence Gathering**:
   - If findings are incomplete, expand search bounds intentionally.
   - Note down confirmed facts, affected modules, and open assumptions before proceeding to code modifications.
