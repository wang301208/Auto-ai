from __future__ import annotations

"""Simple audit logging for denied access attempts."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from autogpt.logs import logger

AUDIT_LOG_FILE = Path(__file__).with_suffix('.log')


@dataclass
class AuditEntry:
    timestamp: str
    plugin: str
    agent: str


def log_denied_access(plugin: str, agent: str) -> None:
    """Record a denied access attempt to the audit log."""
    entry = AuditEntry(
        timestamp=datetime.utcnow().isoformat(),
        plugin=plugin,
        agent=agent,
    )
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry)) + "\n")
    logger.warn(
        "Access to source code for plugin '%s' requested by '%s' denied", plugin, agent
    )


def load_log() -> List[Dict[str, Any]]:
    """Load audit log entries as a list of dictionaries."""
    if not AUDIT_LOG_FILE.is_file():
        return []
    with AUDIT_LOG_FILE.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
