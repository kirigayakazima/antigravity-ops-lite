---
name: repo-inspection
description: >-
  Navigate unfamiliar repositories, discover file structures with ops_glob, investigate patterns
  with ops_grep, and explore project architecture using script-first bounded summaries.
---

# Repository Inspection Runbook

Use this skill when exploring an unfamiliar codebase, discovering file layouts, tracing symbol definitions, or locating the root cause of an issue with minimal token overhead.

## Step-by-Step Workflow

1. **High-Level Overview**:
   - Call `ops_summary(path=".")` to discover the project type, build tool, manifests, configured scripts, entry points, and top-level directory layout.
   - Do NOT read full directory listings or large source files upfront.

2. **Pattern-Based File Discovery**:
   - When looking for specific types of files, call `ops_glob(patterns=["**/*.py", "!tests/**"])` instead of running terminal directory commands.
   - Set `output_mode="details"` to inspect file sizes and modification timestamps.

3. **Targeted Regex & Symbol Search**:
   - Use `ops_grep(pattern="class MyTarget", output_mode="files_with_matches")` to quickly locate matching files without dumping massive code lines.
   - When context is needed, use `ops_grep(pattern="...", output_mode="content", before_context=2, after_context=2)`.
   - If search returns more matches than the budget, a `result_id` is provided. Only call `ops_result` if the initial preview lacks necessary context.

4. **Bounded Multi-File Source Reading**:
   - Inspect related files together using `ops_read_files(files=[{"path": "...", "start_line": ..., "end_line": ...}])`.
   - In-session read deduplication automatically skips re-displaying unmodified files.

5. **Iterative Evidence Gathering**:
   - If findings are incomplete, expand search bounds intentionally.
   - Note down confirmed facts, affected modules, and open assumptions before proceeding to code modifications.
