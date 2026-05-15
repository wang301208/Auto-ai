from __future__ import annotations

import time
import uuid
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

from autoai.mesh.mesh_node import MeshNode, MeshConfig, NodeState, NodeRole, TaskMessage

logger = logging.getLogger(__name__)


class TopologyEvent(Enum):
    NODE_SPAWNED = "node_spawned"
    NODE_TERMINATED = "node_terminated"
    NODE_HIBERNATED = "node_hibernated"
    NODE_AWAKENED = "node_awakened"
    ROLE_EMERGED = "role_emerged"
    FISSION = "fission"
    FUSION = "fusion"


@dataclass
class TopologyRecord:
    event: TopologyEvent
    node_id: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MeshCoordinator:
    """Agent Mesh协调器：监控拓扑、触发自分裂/自融合、角色涌现。"""

    def __init__(self, config: MeshConfig | None = None):
        self.config = config or MeshConfig()
        self.nodes: dict[str, MeshNode] = {}
        self._topology_log: list[TopologyRecord] = []
        self._event_handlers: dict[TopologyEvent, list[Callable]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._coordination_loop())
        logger.info("Mesh协调器启动")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        for node in list(self.nodes.values()):
            await node.stop()
        logger.info("Mesh协调器停止")

    async def add_node(self, node: MeshNode) -> None:
        self.nodes[node.node_id] = node
        await node.start()
        self._record(TopologyEvent.NODE_SPAWNED, node.node_id, {"role": node.role.value})

    async def remove_node(self, node_id: str) -> None:
        node = self.nodes.pop(node_id, None)
        if node:
            await node.terminate_self("coordinator_request")
            self._record(TopologyEvent.NODE_TERMINATED, node_id)

    async def request_fission(self, node_id: str, task_type: str) -> str | None:
        """请求Agent自分裂：负载过高时分裂为两个。"""
        parent = self.nodes.get(node_id)
        if not parent:
            return None
        child_id = await parent.spawn_child(task_type)
        child_config = MeshConfig(
            node_id=child_id,
            address=parent.config.address,
            port=parent.config.port + len(self.nodes) + 1,
        )
        child = MeshNode(child_config)
        await self.add_node(child)
        self._record(TopologyEvent.FISSION, node_id, {"child": child_id, "task_type": task_type})
        return child_id

    async def request_fusion(self, node_a: str, node_b: str) -> bool:
        """请求Agent自融合：两个做同样事的Agent合并为一个。"""
        na = self.nodes.get(node_a)
        nb = self.nodes.get(node_b)
        if not na or not nb:
            return False
        a_caps = na.gossip.self_node.metadata.get("capabilities", set())
        b_caps = nb.gossip.self_node.metadata.get("capabilities", set())
        overlap = len(a_caps & b_caps) / max(1, len(a_caps | b_caps))
        if overlap > self.config.auto_fusion_redundancy_threshold:
            await self.remove_node(node_b)
            na.update_capabilities(a_caps | b_caps)
            self._record(TopologyEvent.FUSION, node_a, {"absorbed": node_b, "overlap": overlap})
            return True
        return False

    def detect_role_emergence(self) -> list[dict]:
        """能力聚类→角色涌现：无需预定义角色，自动发现。"""
        capability_map: dict[str, set[str]] = {}
        for nid, node in self.nodes.items():
            caps = node.gossip.self_node.metadata.get("capabilities", set())
            if isinstance(caps, set):
                capability_map[nid] = caps
            elif isinstance(caps, list):
                capability_map[nid] = set(caps)
        clusters: list[dict] = []
        assigned: set[str] = set()
        for nid, caps in capability_map.items():
            if nid in assigned:
                continue
            cluster = {"center": nid, "capabilities": caps, "members": [nid]}
            assigned.add(nid)
            for other_id, other_caps in capability_map.items():
                if other_id in assigned:
                    continue
                if not caps or not other_caps:
                    continue
                overlap = len(caps & other_caps) / max(1, len(caps | other_caps))
                if overlap > 0.5:
                    cluster["members"].append(other_id)
                    assigned.add(other_id)
            clusters.append(cluster)
        for cluster in clusters:
            if len(cluster["members"]) > 2:
                emergent_role = f"auto_role_{hash(frozenset(cluster['capabilities'])) % 1000}"
                cluster["emergent_role"] = emergent_role
                self._record(TopologyEvent.ROLE_EMERGED, cluster["center"],
                             {"role": emergent_role, "size": len(cluster["members"])})
        return clusters

    def get_topology_stats(self) -> dict:
        active = sum(1 for n in self.nodes.values() if n.state == NodeState.ACTIVE)
        hibernating = sum(1 for n in self.nodes.values() if n.state == NodeState.HIBERNATING)
        total_tasks = sum(n._task_count for n in self.nodes.values())
        avg_load = 0.0
        if self.nodes:
            avg_load = sum(n.load for n in self.nodes.values()) / len(self.nodes)
        return {
            "total_nodes": len(self.nodes),
            "active_nodes": active,
            "hibernating_nodes": hibernating,
            "total_tasks": total_tasks,
            "avg_load": avg_load,
            "topology_events": len(self._topology_log),
        }

    def on(self, event: TopologyEvent, handler: Callable) -> None:
        self._event_handlers.setdefault(event, []).append(handler)

    def _record(self, event: TopologyEvent, node_id: str, details: dict | None = None) -> None:
        record = TopologyRecord(event=event, node_id=node_id, details=details or {})
        self._topology_log.append(record)
        for handler in self._event_handlers.get(event, []):
            try:
                handler(record)
            except Exception as e:
                logger.error(f"拓扑事件处理器异常: {e}")

    async def _coordination_loop(self) -> None:
        while self._running:
            try:
                for node in list(self.nodes.values()):
                    if node.state == NodeState.ACTIVE and node.load > self.config.auto_fission_load_threshold:
                        logger.info(f"协调器触发自分裂: {node.node_id} (负载={node.load:.2f})")
                self.detect_role_emergence()
                await asyncio.sleep(30.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"协调循环异常: {e}")
                await asyncio.sleep(30.0)
