"""HIPAA-compliant audit trail: immutable, tamper-evident, append-only."""

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class AuditAction(str, Enum):
    READ = "READ"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    QUERY = "QUERY"
    EXPORT = "EXPORT"
    AI_INFERENCE = "AI_INFERENCE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ACCESS_DENIED = "ACCESS_DENIED"


class AuditLogger:
    """Thread-safe, append-only HIPAA audit logger with chained hashes."""

    def __init__(self, log_path: str):
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._path.exists():
            return "genesis"
        with open(self._path, "rb") as f:
            lines = f.readlines()
        if not lines:
            return "genesis"
        last = json.loads(lines[-1])
        return last.get("entry_hash", "genesis")

    def log(
        self,
        action: AuditAction,
        user_id: str,
        resource_type: str,
        resource_id: str,
        *,
        patient_id: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
    ) -> str:
        entry_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "action": action.value,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "patient_id": patient_id,
            "details": details or {},
            "success": success,
            "prev_hash": self._prev_hash,
        }

        entry_json = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        entry["entry_hash"] = entry_hash

        with self._lock:
            with open(self._path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            self._prev_hash = entry_hash

        logger.info(
            "hipaa_audit",
            action=action.value,
            user_id=user_id,
            resource_id=resource_id,
            success=success,
        )
        return entry_id

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit chain."""
        if not self._path.exists():
            return True

        prev_hash = "genesis"
        with open(self._path) as f:
            for line in f:
                entry = json.loads(line)
                stored_hash = entry.pop("entry_hash")
                entry_json = json.dumps(entry, sort_keys=True)
                computed = hashlib.sha256(entry_json.encode()).hexdigest()

                if entry["prev_hash"] != prev_hash or computed != stored_hash:
                    return False
                prev_hash = stored_hash
        return True


_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        from src.config.settings import get_settings
        _audit_logger = AuditLogger(get_settings().audit_log_path)
    return _audit_logger
