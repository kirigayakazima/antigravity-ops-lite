import os
import pytest
from pathlib import Path

from ops_lite.policy import (
    PolicyViolation,
    get_canonical_root,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)


def test_validate_and_resolve_path_within_root(tmp_path):
    subfile = tmp_path / "valid.txt"
    subfile.write_text("hello", encoding="utf-8")
    
    resolved = validate_and_resolve_path(str(subfile), base_root=str(tmp_path))
    assert resolved == subfile.resolve()


def test_validate_and_resolve_path_traversal_denied(tmp_path):
    with pytest.raises(PolicyViolation, match="Path traversal denied"):
        validate_and_resolve_path("../../outside.txt", base_root=str(tmp_path))


def test_validate_and_resolve_path_sensitive_file_denied(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=123", encoding="utf-8")
    
    with pytest.raises(PolicyViolation, match="sensitive credential file"):
        validate_and_resolve_path(".env", base_root=str(tmp_path))

    pem_file = tmp_path / "cert.pem"
    pem_file.write_text("CERT", encoding="utf-8")
    with pytest.raises(PolicyViolation, match="sensitive file type"):
        validate_and_resolve_path("cert.pem", base_root=str(tmp_path))


def test_redact_sensitive_text():
    raw_text = (
        "Here is an auth token: Bearer custom_opaque_token_string_123456789\n"
        "JWT: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThis\n"
        "And an api_key: 'sk_live_1234567890abcdef'\n"
        "AWS key: AKIAIOSFODNN7EXAMPLE\n"
        "GitHub token: ghp_123456789012345678901234567890123456"
    )
    redacted = redact_sensitive_text(raw_text)
    assert "Bearer [REDACTED_TOKEN]" in redacted
    assert "[REDACTED_JWT]" in redacted
    assert "[REDACTED_SECRET]" in redacted
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "sk_live_1234567890abcdef" not in redacted


def test_truncate_output():
    short = "Hello World"
    res, is_trunc = truncate_output(short, 50)
    assert not is_trunc
    assert res == short

    long_str = "A" * 100
    res, is_trunc = truncate_output(long_str, 30)
    assert is_trunc
    assert len(res) <= 30
    assert "Truncated" in res
