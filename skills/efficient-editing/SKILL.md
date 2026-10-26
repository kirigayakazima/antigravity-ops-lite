---
name: efficient-editing
description: >-
  Minimizes token consumption when preparing, making, and checking code edits using ops_read_files,
  deterministic ops_replace, and safe ops_batch operations.
---

# Efficient Editing Runbook

Use this skill when preparing to edit code, inspecting preexisting diffs, executing multi-file batch operations, or performing cross-file replacements.

## Step-by-Step Workflow

1. **Pre-flight Status & Diff Check**:
   - Call `ops_run(task="git_summary", path=".")` to identify unstaged, staged, and untracked files before making changes.
   - Separate pre-existing user modifications from the task at hand.

2. **Batched Context Acquisition**:
   - Read definitions and dependent tests simultaneously using `ops_read_files(files=[...])` in a single tool call.
   - Files previously read in the session are automatically deduplicated by hash, saving tokens.

3. **Deterministic Cross-File Replacement**:
   - For symbol renaming, import updates, or configuration refactors across multiple files, use `ops_replace(pattern="old_val", replacement="new_val", dry_run=True)` to preview changes.
   - Verify the preview, then set `dry_run=False` to apply deterministically without generating repetitive diffs.

4. **Structured File Reorganization**:
   - For moving, copying, or removing files, use `ops_batch(action="plan", operations=[...])` to preflight-verify paths and permissions.
   - Once verified, execute with `action="run"`.

5. **Verify Incremental Diff**:
   - Call `ops_run(task="git_summary", path=".")` to inspect the unified diff snippet.
   - Confirm that no unintended files or lines were altered.
