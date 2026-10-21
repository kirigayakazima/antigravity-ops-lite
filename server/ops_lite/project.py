"""Project structure analysis, metadata inspection, and configuration discovery."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ops_lite.policy import (
    DEFAULT_IGNORED_DIRS,
    DEFAULT_SUMMARY_MAX_CHARS,
    DEFAULT_SUMMARY_MAX_ITEMS,
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)

COMMON_ENTRYPOINT_NAMES = [
    "main.py",
    "app.py",
    "cli.py",
    "index.ts",
    "index.js",
    "server.js",
    "server.ts",
    "src/main.rs",
    "src/lib.rs",
    "main.go",
    "src/index.ts",
    "src/index.js",
    "src/main.py",
]


def detect_project_type(root: Path) -> Dict[str, Any]:
    """Detect language and build framework from manifest files."""
    types = []
    manifests = []
    scripts = {}

    # Python
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        types.append("Python (pyproject.toml)")
        manifests.append("pyproject.toml")
    elif (root / "setup.py").exists() or (root / "requirements.txt").exists():
        types.append("Python")
        if (root / "setup.py").exists():
            manifests.append("setup.py")
        if (root / "requirements.txt").exists():
            manifests.append("requirements.txt")

    # Node.js
    pkg_json = root / "package.json"
    if pkg_json.exists():
        types.append("Node.js / JavaScript / TypeScript")
        manifests.append("package.json")
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "scripts" in data and isinstance(data["scripts"], dict):
                    scripts["npm"] = data["scripts"]
        except Exception:
            pass

    # Rust
    if (root / "Cargo.toml").exists():
        types.append("Rust (Cargo)")
        manifests.append("Cargo.toml")

    # Go
    if (root / "go.mod").exists():
        types.append("Go (go.mod)")
        manifests.append("go.mod")

    # Java / Kotlin
    if (root / "pom.xml").exists():
        types.append("Java (Maven)")
        manifests.append("pom.xml")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        types.append("Java/Kotlin (Gradle)")
        manifests.append("build.gradle")

    # C# / .NET
    sln_files = list(root.glob("*.sln"))
    csproj_files = list(root.glob("*.csproj"))
    if sln_files or csproj_files:
        types.append(".NET / C#")
        manifests.extend([p.name for p in (sln_files + csproj_files)])

    return {
        "project_types": types or ["unknown"],
        "manifests": manifests,
        "scripts": scripts,
    }


def find_entrypoints(root: Path) -> List[str]:
    """Find conventional entrypoints if they exist."""
    found = []
    for name in COMMON_ENTRYPOINT_NAMES:
        target = root / name
        if target.exists() and target.is_file():
            found.append(name.replace("\\", "/"))
    return found


def get_git_info(root: Path) -> Dict[str, Any]:
    """Get compact git branch and status if inside git repository."""
    git_dir = root / ".git"
    if not git_dir.exists():
        return {"is_git": False, "status": "Not a git repository"}

    try:
        # Branch
        res_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = res_branch.stdout.strip() or "HEAD detached"

        # Short status
        res_status = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        status_lines = [line.strip() for line in res_status.stdout.splitlines() if line.strip()]
        
        # Latest commit
        res_log = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        latest_commit = res_log.stdout.strip()

        return {
            "is_git": True,
            "branch": branch,
            "latest_commit": latest_commit,
            "modified_files_count": len(status_lines),
            "status_preview": status_lines[:10],
            "has_more_status": len(status_lines) > 10,
        }
    except Exception as e:
        return {"is_git": True, "error": str(e)}


def build_directory_tree(
    root: Path,
    max_depth: int = 2,
    max_items: int = DEFAULT_SUMMARY_MAX_ITEMS,
) -> Dict[str, Any]:
    """
    Build a limited-depth tree structure excluding ignored directories.
    """
    items_count = 0
    tree_lines = []

    def walk_dir(current_dir: Path, depth: int, prefix: str = ""):
        nonlocal items_count
        if depth > max_depth or items_count >= max_items:
            return

        try:
            entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return

        for idx, entry in enumerate(entries):
            if items_count >= max_items:
                tree_lines.append(f"{prefix}... [Truncated at {max_items} items]")
                break

            name = entry.name
            if name in DEFAULT_IGNORED_DIRS:
                continue

            items_count += 1
            is_last = (idx == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            child_prefix = "    " if is_last else "│   "

            if entry.is_dir():
                tree_lines.append(f"{prefix}{connector}{name}/")
                walk_dir(entry, depth + 1, prefix + child_prefix)
            else:
                tree_lines.append(f"{prefix}{connector}{name}")

    tree_lines.append(f"{root.name}/")
    walk_dir(root, 1)

    return {
        "items_included": items_count,
        "max_items": max_items,
        "tree": "\n".join(tree_lines),
    }


def summarize_project(
    path: str = ".",
    base_root: Optional[str] = None,
    sections: Optional[List[str]] = None,
    max_items: int = DEFAULT_SUMMARY_MAX_ITEMS,
    max_chars: int = DEFAULT_SUMMARY_MAX_CHARS,
) -> Dict[str, Any]:
    """
    Produce a concise, token-budgeted summary of the project.
    """
    resolved_root = validate_and_resolve_path(path, base_root)
    if not resolved_root.is_dir():
        raise PolicyViolation(f"Summary target is not a directory: '{path}'")

    active_sections = sections or ["structure", "project_type", "entrypoints", "scripts", "git"]
    summary_data: Dict[str, Any] = {"path": str(resolved_root)}

    # Project metadata & scripts
    proj_info = detect_project_type(resolved_root)
    if "project_type" in active_sections:
        summary_data["project_types"] = proj_info["project_types"]
        summary_data["manifests"] = proj_info["manifests"]

    if "scripts" in active_sections:
        summary_data["scripts"] = proj_info["scripts"]

    # Entrypoints
    if "entrypoints" in active_sections:
        summary_data["entrypoints"] = find_entrypoints(resolved_root)

    # Git
    if "git" in active_sections:
        summary_data["git"] = get_git_info(resolved_root)

    # Directory Structure
    if "structure" in active_sections:
        summary_data["structure"] = build_directory_tree(
            resolved_root, max_depth=2, max_items=max_items
        )

    # Format into markdown-like compact text
    lines = [f"# Project Summary: {resolved_root.name}"]
    if "project_types" in summary_data:
        lines.append(f"- **Types**: {', '.join(summary_data['project_types'])}")
        lines.append(f"- **Manifests**: {', '.join(summary_data['manifests']) or 'None'}")
    if "entrypoints" in summary_data and summary_data["entrypoints"]:
        lines.append(f"- **Entrypoints**: {', '.join(summary_data['entrypoints'])}")
    if "git" in summary_data:
        git_val = summary_data["git"]
        if git_val.get("is_git"):
            lines.append(f"- **Git**: branch `{git_val.get('branch')}`, modified files: {git_val.get('modified_files_count')}")
        else:
            lines.append("- **Git**: Not a git repository")
    if "scripts" in summary_data and summary_data["scripts"]:
        lines.append("- **Configured Scripts**:")
        for runner, script_map in summary_data["scripts"].items():
            for sname, scmd in list(script_map.items())[:10]:
                lines.append(f"  - `{sname}`: {scmd}")
    if "structure" in summary_data:
        lines.append("\n## Structure Preview:")
        lines.append("```text")
        lines.append(summary_data["structure"]["tree"])
        lines.append("```")

    full_text = "\n".join(lines)
    truncated_text, is_truncated = truncate_output(full_text, max_chars)
    sanitized_text = redact_sensitive_text(truncated_text)

    summary_data["formatted"] = sanitized_text
    summary_data["is_truncated"] = is_truncated
    return summary_data
