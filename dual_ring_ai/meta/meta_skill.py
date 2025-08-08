"""
Meta Skill registry and operations for Strategy Evolution

This module defines the protected MetaSkill that represents the strategist's
own methodology and provides facilities to persist, propose upgrades, and
apply approved upgrades under a human-controlled approval gate.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


@dataclass
class MetaSkill:
    name: str
    version: str
    content: str
    updated_at: str


DEFAULT_META_SKILL_NAME = "MetaSkill_StrategyEvolution"
DEFAULT_META_SKILL_VERSION = "v1.0"


DEFAULT_META_SKILL_CONTENT = (
    "这不是一个用于完成外部任务的技能，而是“策略师”代理进行自我思考和分析的方法论。"
    "它包含了“策略师”如何收集数据、如何进行因果推断、如何从案例中提炼新战略原则的完整逻辑。"
    "地位：系统的宪法或哲学内核。"
)


class MetaSkillRegistry:
    """Persist and protect MetaSkill state on disk.

    The registry is intended to be the single source of truth for the current
    meta-skill version and contents. It writes to a JSON file under the
    configured workspace path. Only upgrades that pass the human approval gate
    should be applied via this registry.
    """

    def __init__(self, store_path: Path) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            logger.info("Initializing meta-skill store at %s", self.store_path)
            self._write(
                MetaSkill(
                    name=DEFAULT_META_SKILL_NAME,
                    version=DEFAULT_META_SKILL_VERSION,
                    content=DEFAULT_META_SKILL_CONTENT,
                    updated_at=datetime.utcnow().isoformat(),
                )
            )

    def load(self) -> MetaSkill:
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            return MetaSkill(**data)
        except Exception as exc:
            logger.error("Failed to load meta-skill: %s", exc)
            # Reinitialize on failure
            meta = MetaSkill(
                name=DEFAULT_META_SKILL_NAME,
                version=DEFAULT_META_SKILL_VERSION,
                content=DEFAULT_META_SKILL_CONTENT,
                updated_at=datetime.utcnow().isoformat(),
            )
            self._write(meta)
            return meta

    def _write(self, meta: MetaSkill) -> None:
        self.store_path.write_text(
            json.dumps(asdict(meta), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def apply_upgrade(self, new_version: str, new_content: str) -> MetaSkill:
        """Apply an approved upgrade to the MetaSkill and persist it."""
        meta = MetaSkill(
            name=DEFAULT_META_SKILL_NAME,
            version=new_version,
            content=new_content,
            updated_at=datetime.utcnow().isoformat(),
        )
        self._write(meta)
        logger.info("Meta-skill upgraded to %s", new_version)
        return meta


@dataclass
class MetaTicket:
    ticket_id: str
    created_at: str
    title: str
    description: str
    current_version: str
    proposed_version: Optional[str] = None
    proposal_path: Optional[str] = None
    status: str = "pending_approval"  # pending_approval | approved | rejected | applied
    details: Dict[str, Any] = None


class MetaTicketStore:
    """File-based ticket store for meta upgrades."""

    def __init__(self, ticket_dir: Path) -> None:
        self.ticket_dir = Path(ticket_dir)
        self.ticket_dir.mkdir(parents=True, exist_ok=True)

    def create(self, ticket: MetaTicket) -> Path:
        path = self.ticket_dir / f"{ticket.ticket_id}.json"
        payload = asdict(ticket)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def update_status(self, ticket_id: str, status: str) -> None:
        path = self.ticket_dir / f"{ticket_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Ticket {ticket_id} not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = status
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


