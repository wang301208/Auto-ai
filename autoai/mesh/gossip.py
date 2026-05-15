from __future__ import annotations

import time
import random
import hashlib
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MemberState(Enum):
    ALIVE = "alive"
    SUSPECT = "suspect"
    DEAD = "dead"


@dataclass
class GossipMember:
    node_id: str
    address: str
    port: int
    state: MemberState = MemberState.ALIVE
    incarnation: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    heartbeat: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    @property
    def key(self) -> str:
        return f"{self.node_id}@{self.address}:{self.port}"

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "state": self.state.value,
            "incarnation": self.incarnation,
            "metadata": self.metadata,
            "heartbeat": self.heartbeat,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GossipMember:
        return cls(
            node_id=data["node_id"],
            address=data["address"],
            port=data["port"],
            state=MemberState(data.get("state", "alive")),
            incarnation=data.get("incarnation", 0),
            metadata=data.get("metadata", {}),
            heartbeat=data.get("heartbeat", time.time()),
        )


class GossipProtocol:
    """Gossip协议实现：无中心服务发现，用于Agent Mesh自组织。"""

    def __init__(
        self,
        self_node: GossipMember,
        probe_interval: float = 1.0,
        suspect_timeout: float = 5.0,
        dead_timeout: float = 15.0,
        gossip_fanout: int = 3,
        protocol_period: float = 1.0,
    ):
        self.self_node = self_node
        self.members: dict[str, GossipMember] = {self_node.key: self_node}
        self.probe_interval = probe_interval
        self.suspect_timeout = suspect_timeout
        self.dead_timeout = dead_timeout
        self.gossip_fanout = gossip_fanout
        self.protocol_period = protocol_period
        self._sequence_number = 0
        self._event_handlers: dict[str, list[Callable]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_member(self, member: GossipMember) -> None:
        key = member.key
        if key not in self.members:
            self.members[key] = member
            self._emit("member_join", member)
            logger.info(f"Agent加入Mesh: {key}")

    def remove_member(self, member: GossipMember) -> None:
        key = member.key
        if key in self.members and key != self.self_node.key:
            member.state = MemberState.DEAD
            self._emit("member_leave", member)
            logger.info(f"Agent离开Mesh: {key}")

    def suspect_member(self, member: GossipMember) -> None:
        if member.state == MemberState.ALIVE:
            member.state = MemberState.SUSPECT
            member.incarnation += 1
            self._emit("member_suspect", member)
            logger.warning(f"Agent疑似离线: {member.key}")

    def revive_member(self, member: GossipMember) -> None:
        if member.state in (MemberState.SUSPECT, MemberState.DEAD):
            member.state = MemberState.ALIVE
            member.last_seen = time.time()
            self._emit("member_revive", member)

    def merge_membership(self, incoming: list[dict]) -> list[dict]:
        """合并来自其他节点的成员信息，返回本地增量。"""
        deltas = []
        for data in incoming:
            remote = GossipMember.from_dict(data)
            existing = self.members.get(remote.key)
            if existing is None:
                self.add_member(remote)
            elif remote.incarnation > existing.incarnation:
                existing.incarnation = remote.incarnation
                existing.state = remote.state
                existing.metadata.update(remote.metadata)
                existing.last_seen = time.time()
            else:
                deltas.append(existing.to_dict())
        self.self_node.heartbeat = time.time()
        deltas.insert(0, self.self_node.to_dict())
        return deltas

    def create_gossip_message(self) -> dict:
        self._sequence_number += 1
        fanout = min(self.gossip_fanout, len(self.members) - 1)
        targets = [
            m for k, m in self.members.items()
            if k != self.self_node.key and m.state != MemberState.DEAD
        ]
        selected = random.sample(targets, min(fanout, len(targets))) if targets else []
        return {
            "type": "gossip",
            "seq": self._sequence_number,
            "from": self.self_node.to_dict(),
            "members": [m.to_dict() for m in selected],
            "timestamp": time.time(),
        }

    def check_timeouts(self) -> None:
        now = time.time()
        for key, member in list(self.members.items()):
            if key == self.self_node.key:
                continue
            age = now - member.last_seen
            if member.state == MemberState.ALIVE and age > self.suspect_timeout:
                self.suspect_member(member)
            elif member.state == MemberState.SUSPECT and age > self.dead_timeout:
                self.remove_member(member)

    def on(self, event: str, handler: Callable) -> None:
        self._event_handlers.setdefault(event, []).append(handler)

    def _emit(self, event: str, data: Any) -> None:
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"事件处理器异常: {e}")

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._gossip_loop())
        logger.info(f"Gossip协议启动: {self.self_node.key}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Gossip协议停止: {self.self_node.key}")

    async def _gossip_loop(self) -> None:
        while self._running:
            try:
                self.check_timeouts()
                self.self_node.heartbeat = time.time()
                self.self_node.last_seen = time.time()
                await asyncio.sleep(self.protocol_period)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Gossip循环异常: {e}")
                await asyncio.sleep(self.protocol_period)

    def get_alive_members(self) -> list[GossipMember]:
        return [m for m in self.members.values() if m.state == MemberState.ALIVE]

    def get_mesh_stats(self) -> dict:
        alive = sum(1 for m in self.members.values() if m.state == MemberState.ALIVE)
        suspect = sum(1 for m in self.members.values() if m.state == MemberState.SUSPECT)
        dead = sum(1 for m in self.members.values() if m.state == MemberState.DEAD)
        return {"alive": alive, "suspect": suspect, "dead": dead, "total": len(self.members)}
