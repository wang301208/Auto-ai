"""
Human approval gate for meta-skill upgrades.

This module provides a simple approval workflow that requires an explicit human
action to approve any change to the meta-skill. In a production system this
could integrate with a dashboard or code review system. Here we provide a
filesystem-based toggle and an event-driven interface.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    ticket_id: str
    meta_current_version: str
    meta_proposed_version: str
    created_at: str


class ApprovalGate:
    """Filesystem-based approval gate.

    A human architect must create a file named `<ticket_id>.approved` in the
    approval directory for the approval to pass.
    """

    def __init__(self, approval_dir: Path) -> None:
        self.approval_dir = Path(approval_dir)
        self.approval_dir.mkdir(parents=True, exist_ok=True)

    def request(self, req: ApprovalRequest) -> Path:
        path = self.approval_dir / f"{req.ticket_id}.request.json"
        payload = {
            "ticket_id": req.ticket_id,
            "meta_current_version": req.meta_current_version,
            "meta_proposed_version": req.meta_proposed_version,
            "created_at": req.created_at,
            "instruction": "To approve, create an empty file named '<ticket_id>.approved' in this directory. To reject, create '<ticket_id>.rejected'.",
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Approval requested for ticket %s", req.ticket_id)
        return path

    def check(self, ticket_id: str) -> Optional[str]:
        """Return 'approved' | 'rejected' | None"""
        if (self.approval_dir / f"{ticket_id}.approved").exists():
            return "approved"
        if (self.approval_dir / f"{ticket_id}.rejected").exists():
            return "rejected"
        return None


