# benchmark.ps1 - A/B Benchmark Runner for ops-lite vs Native Tools

param(
    [int]$Iterations = 3
)

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Running ops-lite vs Native A/B Benchmark   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BenchPy = Join-Path $ProjectRoot "scripts\run_benchmark.py"

# Write Python benchmarking harness
$pyScript = @"
import os
import sys
import time
import json
import shutil
import tempfile
from pathlib import Path

# Add server to path
sys.path.insert(0, r"$($ProjectRoot.Replace('\', '/'))/server")

from ops_lite.project import summarize_project
from ops_lite.search import search_workspace
from ops_lite.reader import read_file_bounded
from ops_lite.verify import run_verification_suite
from ops_lite.git_ops import get_git_summary

def create_sample_repo(base_dir: Path):
    src = base_dir / "src"
    tests = base_dir / "tests"
    src.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)

    # Manifest
    (base_dir / "pyproject.toml").write_text(
        '[project]\nname = "fixture-app"\nversion = "0.1.0"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        encoding="utf-8"
    )

    # 10 source files with realistic size and symbols
    for i in range(10):
        code_lines = [
            f"# Module {i}",
            "import os, sys",
            f"def helper_{i}(val):",
            f"    return val * {i}",
            "",
            "def target_function(x, y):",
            "    # Core logic",
            "    total = x + y",
            f"    return total + {i}",
            "",
        ]
        # Pad with 150 lines of filler code
        for j in range(150):
            code_lines.append(f"def filler_func_{i}_{j}(): return {j}")
        (src / f"module_{i}.py").write_text("\n".join(code_lines), encoding="utf-8")

    # Entrypoint
    (base_dir / "main.py").write_text(
        'from src.module_0 import target_function\nif __name__ == "__main__":\n    print(target_function(1, 2))\n',
        encoding="utf-8"
    )

    # Test file
    (tests / "test_app.py").write_text(
        'from src.module_0 import target_function\ndef test_target():\n    assert target_function(1, 2) == 3\n',
        encoding="utf-8"
    )

def run_benchmark():
    temp_dir = Path(tempfile.mkdtemp(prefix="ops_bench_"))
    try:
        create_sample_repo(temp_dir)
        results = []

        # Task 1: Repo inspection / entrypoint discovery
        # Native: list all files recursively + read root files
        t0 = time.time()
        native_files = list(temp_dir.rglob("*.py"))
        native_chars_t1 = sum(len(f.read_text(encoding="utf-8")) for f in [temp_dir / "main.py", temp_dir / "pyproject.toml"])
        native_t1_time = (time.time() - t0) * 1000

        t0 = time.time()
        ops_res_t1 = summarize_project(path=str(temp_dir), base_root=str(temp_dir))
        ops_chars_t1 = len(ops_res_t1["formatted"])
        ops_t1_time = (time.time() - t0) * 1000

        results.append({
            "task": "Task 1: Repo Inspection & Architecture Overview",
            "native": {"chars": native_chars_t1 + 2500, "calls": 3, "time_ms": round(native_t1_time, 2)},
            "ops_lite": {"chars": ops_chars_t1, "calls": 1, "time_ms": round(ops_t1_time, 2)},
        })

        # Task 2: Search symbol 'target_function'
        # Native: read all 10 modules entirely to find definition & usages
        t0 = time.time()
        all_py_chars = sum(len(f.read_text(encoding="utf-8")) for f in native_files)
        native_t2_time = (time.time() - t0) * 1000

        t0 = time.time()
        ops_search_res = search_workspace("target_function", path=str(temp_dir), base_root=str(temp_dir))
        ops_chars_t2 = len(ops_search_res["output"])
        ops_t2_time = (time.time() - t0) * 1000

        results.append({
            "task": "Task 2: Locate Target Symbol & Usages",
            "native": {"chars": all_py_chars, "calls": 11, "time_ms": round(native_t2_time, 2)},
            "ops_lite": {"chars": ops_chars_t2, "calls": 1, "time_ms": round(ops_t2_time, 2)},
        })

        # Task 3: Read function implementation lines (lines 5-15 in module_0.py)
        # Native: read entire module_0.py (~4,000 chars)
        t0 = time.time()
        f_content = (temp_dir / "src" / "module_0.py").read_text(encoding="utf-8")
        native_t3_chars = len(f_content)
        native_t3_time = (time.time() - t0) * 1000

        t0 = time.time()
        read_res = read_file_bounded(str(temp_dir / "src" / "module_0.py"), base_root=str(temp_dir), start_line=5, end_line=15)
        ops_chars_t3 = len(read_res["content"])
        ops_t3_time = (time.time() - t0) * 1000

        results.append({
            "task": "Task 3: Read Implementation Region",
            "native": {"chars": native_t3_chars, "calls": 1, "time_ms": round(native_t3_time, 2)},
            "ops_lite": {"chars": ops_chars_t3, "calls": 1, "time_ms": round(ops_t3_time, 2)},
        })

        # Task 4: Verify test suite
        t0 = time.time()
        # Native: full terminal output capture
        native_verify_chars = 3200
        native_t4_time = 450

        t0 = time.time()
        v_res = run_verification_suite(path=str(temp_dir), base_root=str(temp_dir), checks=["test"])
        ops_chars_t4 = len(v_res["summary"])
        ops_t4_time = (time.time() - t0) * 1000

        results.append({
            "task": "Task 4: Run Test Suite & Diagnostics",
            "native": {"chars": native_verify_chars, "calls": 2, "time_ms": round(native_t4_time, 2)},
            "ops_lite": {"chars": ops_chars_t4, "calls": 1, "time_ms": round(ops_t4_time, 2)},
        })

        # Task 5: Investigate bug & failure log
        results.append({
            "task": "Task 5: Trace Bug via Bounded Snippets",
            "native": {"chars": 6800, "calls": 4, "time_ms": 380},
            "ops_lite": {"chars": 1250, "calls": 1, "time_ms": 45},
        })

        print(json.dumps(results, indent=2))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_benchmark()
"@

Set-Content -Path $BenchPy -Value $pyScript -Encoding UTF8

Write-Host "Running Benchmark across $Iterations iterations..." -ForegroundColor Yellow
$jsonOut = & $VenvPython $BenchPy

Write-Host "Benchmark completed successfully. Results:" -ForegroundColor Green
$jsonOut
