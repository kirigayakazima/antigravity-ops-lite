"""Local result store for managing, paginating, and expiring large operation outputs."""

import json
import os
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ops_lite.policy import (
    DEFAULT_RESULT_PAGE_LIMIT,
    DEFAULT_RESULT_PAGE_MAX_CHARS,
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
)

MAX_STORED_RESULTS = 50
RESULT_TTL_SECONDS = 86400  # 24 hours


@dataclass
class StoredResult:
    result_id: str
    result_type: str
    created_at: float
    total_items: int
    summary: str
    items: List[str]  # Lines or stringified items


class ResultStore:
    def __init__(self, store_dir: Optional[Path] = None):
        if store_dir is None:
            # Stored in user temp dir scoped to ops-lite to avoid polluting user workspace
            base_temp = Path(os.environ.get("TEMP", os.path.expanduser("~")))
            self.store_dir = base_temp / "antigravity_ops_lite_results"
        else:
            self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _cleanup_old_results(self) -> None:
        """Purge expired results or maintain result count cap."""
        now = time.time()
        files = list(self.store_dir.glob("*.json"))
        
        # Remove expired files
        valid_files = []
        for f in files:
            try:
                mtime = f.stat().st_mtime
                if now - mtime > RESULT_TTL_SECONDS:
                    f.unlink(missing_ok=True)
                else:
                    valid_files.append((mtime, f))
            except OSError:
                continue

        # If exceeding max count, remove oldest
        if len(valid_files) > MAX_STORED_RESULTS:
            valid_files.sort(key=lambda x: x[0])
            to_remove = len(valid_files) - MAX_STORED_RESULTS
            for _, f in valid_files[:to_remove]:
                try:
                    f.unlink(missing_ok=True)
                except OSError:
                    pass

    def store(
        self,
        result_type: str,
        summary: str,
        items: List[str],
    ) -> str:
        """Store items and return a unique result_id."""
        self._cleanup_old_results()
        
        # Cryptographically secure random result id
        result_id = f"res_{secrets.token_hex(8)}"
        
        # Redact items before storage
        sanitized_items = [redact_sensitive_text(it) for it in items]
        sanitized_summary = redact_sensitive_text(summary)

        stored = StoredResult(
            result_id=result_id,
            result_type=result_type,
            created_at=time.time(),
            total_items=len(sanitized_items),
            summary=sanitized_summary,
            items=sanitized_items,
        )

        target_file = self.store_dir / f"{result_id}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(asdict(stored), f, ensure_ascii=False)

        return result_id

    def retrieve(
        self,
        result_id: str,
        offset: int = 0,
        limit: int = DEFAULT_RESULT_PAGE_LIMIT,
        max_chars: int = DEFAULT_RESULT_PAGE_MAX_CHARS,
    ) -> Dict[str, Any]:
        """Paginate and return a slice of the stored result."""
        # Sanitize result_id to prevent path injection
        if not result_id or not result_id.isalnum() and not (result_id.startswith("res_") and result_id[4:].isalnum()):
            raise PolicyViolation(f"Invalid result ID format: '{result_id}'")

        target_file = self.store_dir / f"{result_id}.json"
        if not target_file.exists():
            return {
                "error": f"Result '{result_id}' not found or expired.",
                "status": "not_found",
            }

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {"error": f"Failed to read result '{result_id}': {e}", "status": "error"}

        items: List[str] = data.get("items", [])
        total = len(items)
        
        offset = max(0, offset)
        limit = max(1, min(limit, 100))  # hard cap at 100 items per page
        
        slice_items = items[offset : offset + limit]
        has_more = (offset + limit) < total
        
        joined_text = "\n".join(slice_items)
        truncated_text, is_truncated = truncate_output(joined_text, max_chars)

        return {
            "result_id": result_id,
            "result_type": data.get("result_type", "generic"),
            "created_at": data.get("created_at"),
            "summary": data.get("summary", ""),
            "offset": offset,
            "limit": limit,
            "total_items": total,
            "has_more": has_more,
            "is_truncated": is_truncated,
            "items": truncated_text.split("\n"),
        }


# Global store instance
default_store = ResultStore()
