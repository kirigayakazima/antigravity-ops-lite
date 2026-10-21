---
name: efficient-editing
description: >-
  Minimizes token consumption and repetitive reads when preparing, making, and checking
  code edits in a workspace.
---

# Efficient Editing Runbook

Use this skill when preparing to edit code, inspecting preexisting diffs, and reviewing incremental changes.

## Step-by-Step Workflow

1. **Pre-flight Status & Diff Check**:
   - Call `ops_run(task="git_summary", path=".")` to identify unstaged, staged, and untracked files before making changes.
   - Separate pre-existing user modifications from the task at hand.

2. **Scoped Context Acquisition**:
   - Locate only the target functions or definitions via `ops_search`.
   - Read the minimum relevant line bounds using `ops_read`.
   - Avoid reading whole files or unrelated dependencies.

3. **Perform Semantic Edits**:
   - Make precise edits using the standard editing tools.
   - Do not re-read entire files to verify an edit; check only the modified section.

4. **Verify Incremental Diff**:
   - Call `ops_run(task="git_summary", path=".")` to inspect the unified diff snippet.
   - Confirm that no unintended files or lines were altered.
   - If diff exceeds preview length, use `ops_result` with the returned `result_id`.
