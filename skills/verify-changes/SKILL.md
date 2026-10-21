---
name: verify-changes
description: >-
  Executes configured format, test, and build checks in a batch with compact status summaries
  and error tail logs.
---

# Verify Changes Runbook

Use this skill after modifying code to run automated checks (formatters, unit tests, build tools) without flooding the model context with endless terminal logs.

## Step-by-Step Workflow

1. **Batch Check Execution**:
   - Call `ops_run(task="verify", checks=["test"], path=".")` (or include `format`, `build`).
   - The tool automatically inspects project configuration (`pyproject.toml`, `package.json`, `Cargo.toml`, etc.) and invokes only pre-configured commands.

2. **Evaluate Status**:
   - Each check returns one of:
     - `passed`: All checks succeeded (exit 0).
     - `failed`: Check failed with exit code and tail error lines.
     - `timed_out`: Check exceeded allowed execution limit.
     - `not_configured`: Project has no configured script for this check type.
   - Never claim an unconfigured or skipped test passed.

3. **Drill Down into Failures**:
   - When a check fails, inspect the returned `log_preview` (last 10-25 lines).
   - If the error origin is outside the tail log, use `ops_result(result_id="<res_id>")` to page through earlier diagnostic output.
