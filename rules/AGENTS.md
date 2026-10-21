# Script-First Operations

For repository inspection, repetitive file operations, search,
diagnostics, and verification:

1. Prefer ops-lite tools when they cover the task.
2. Inspect project metadata and existing scripts before
   inventing new commands.
3. Use targeted search and bounded reads. Do not read entire
   directories or large files without a reason.
4. Batch independent, deterministic, safe operations into one
   ops_run call.
5. Return summaries, locations, and error details rather than
   forwarding complete terminal logs.
6. Use ops_result to retrieve additional output only when the
   summary is insufficient.
7. Never hide errors or truncate evidence required for a
   correct decision.
8. Read source directly when architecture, semantics,
   correctness, or security requires it.
9. Do not use scripts to replace reasoning about requirements
   or program behavior.
10. After edits, inspect the relevant diff and verify affected
    behavior with configured checks.
11. If ops-lite is unavailable or unsuitable, fall back to
    native tools and continue the task.
12. Do not repeatedly invoke summary/search tools when existing
    evidence is fresh and sufficient.
