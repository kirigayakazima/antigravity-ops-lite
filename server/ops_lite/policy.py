"""Security, resource budget, and redaction policies for ops-lite."""

import os
import re
from pathlib import Path
from typing import Optional, Set

# Budget caps
DEFAULT_SUMMARY_MAX_ITEMS = 40
DEFAULT_SUMMARY_MAX_CHARS = 8000
DEFAULT_SEARCH_MAX_RESULTS = 20
DEFAULT_SEARCH_MAX_CHARS = 12000
DEFAULT_READ_MAX_LINES = 200
DEFAULT_READ_MAX_CHARS = 10000
DEFAULT_RESULT_PAGE_LIMIT = 20
DEFAULT_RESULT_PAGE_MAX_CHARS = 10000

# Prohibited sensitive files (case-insensitive checks)
BLOCKED_FILE_PATTERNS = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".pypirc",
    ".npmrc",
    "id_rsa",
    "id_ed25519",
    "id_dsa",
    "id_ecdsa",
    "secrets.json",
    "credentials.json",
    "service-account.json",
}

BLOCKED_EXTENSIONS = {
    ".pem",
    ".key",
    ".pkcs12",
    ".pfx",
    ".p12",
    ".kdbx",
}

# Directories commonly ignored in summaries and searches
DEFAULT_IGNORED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    ".next",
    ".nuxt",
    ".cache",
    "coverage",
    ".ops_results",
}

# Regex patterns for credential redaction
REDACTION_PATTERNS = [
    # JWT tokens
    (re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+"), "[REDACTED_JWT]"),
    # GitHub personal tokens
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"), "[REDACTED_GITHUB_TOKEN]"),
    # AWS Access Key ID
    (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Bearer tokens
    (re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9\-\._~\+\/]+=*", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # Generic API Keys / Passwords in key-value pairs
    (
        re.compile(
            r"(?i)(api[_-]?key|secret|password|passwd|private[_-]?key|auth[_-]?token)\s*([:=])\s*(['\"]?)([\w\-\.]{8,})(\3)"
        ),
        r"\1 \2 \3[REDACTED_SECRET]\3",
    ),
]


class PolicyViolation(Exception):
    """Raised when an operation violates security policy."""
    pass


def get_canonical_root(root_path: Optional[str] = None) -> Path:
    """Resolve and return the canonical base root path."""
    if not root_path:
        root_path = os.getcwd()
    return Path(root_path).resolve()


def validate_and_resolve_path(
    target_path: str,
    base_root: Optional[str] = None,
    allow_non_existent: bool = False,
) -> Path:
    """
    Validate that target_path resolves strictly within base_root and is not sensitive.
    """
    root = get_canonical_root(base_root)
    
    # Handle relative or absolute paths
    raw_path = Path(target_path)
    if not raw_path.is_absolute():
        resolved = (root / raw_path).resolve()
    else:
        resolved = raw_path.resolve()

    # Check confinement: resolved must be within root or equal to root
    try:
        resolved.relative_to(root)
    except ValueError:
        raise PolicyViolation(
            f"Path traversal denied: '{target_path}' resolves outside workspace root '{root}'."
        )

    # Check for sensitive files
    lower_name = resolved.name.lower()
    if lower_name in BLOCKED_FILE_PATTERNS:
        raise PolicyViolation(f"Access to sensitive credential file '{resolved.name}' is prohibited.")

    if resolved.suffix.lower() in BLOCKED_EXTENSIONS:
        raise PolicyViolation(f"Access to sensitive file type '{resolved.suffix}' is prohibited.")

    if not allow_non_existent and not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: '{target_path}'")

    return resolved


def redact_sensitive_text(text: str) -> str:
    """Redact passwords, secret tokens, and credentials from string output."""
    if not text:
        return ""
    redacted = text
    for pattern, replacement in REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def truncate_output(text: str, max_chars: int, truncation_message: Optional[str] = None) -> tuple[str, bool]:
    """
    Truncate text to max_chars without splitting unicode surrogate pairs.
    Returns (truncated_text, is_truncated).
    """
    if len(text) <= max_chars:
        return text, False
    
    msg = truncation_message or f"\n... [Truncated: limit {max_chars}]"
    if len(msg) >= max_chars:
        msg = " ...[Truncated]"
        if len(msg) >= max_chars:
            return text[:max_chars], True

    cut_point = max(0, max_chars - len(msg))
    return text[:cut_point] + msg, True
