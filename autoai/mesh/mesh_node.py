from __future__ import annotations

import time
import uuid
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

from autoai.mesh.gossip import GossipProtocol, GossipMember, MemberState
from autoai.mesh.crdt import ORSet, LWWRegister, CRDTMap

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    WORKER = "worker"
    COORDINATOR = "coordinator"
    OBSERVER = "observer"


class NodeState(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DRAINING = "draining"
    HIBERNATING = "hibernating"
    TERMINATED = "terminated"


@dataclass
class MeshConfig:
    node_id: str = field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:8]}")
    address: str = "127.0.0.1"
    port: int = 7946
    gossip_interval: float = 1.0
    suspect_timeout: float = 5.0
    dead_timeout: float = 15.0
    gossip_fanout: int = 3
    auto_hibernate_idle_seconds: float = 300.0
    auto_fission_load_threshold: float = 0.85
    auto_fusion_redundancy_threshold: float = 0.7


@dataclass
class TaskMessage:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_type: str = ""
    payload: Any = None
    source: str = ""
    target: str = ""
    priority: int = 0
    timestamp: float = field(default_factory=time.time)


class MeshNode:
    """Agent Mesh节点：无中心自组织网络中的单个Agent节点。"""

    def __init__(self, config: MeshConfig | None = None):
        self.config = config or MeshConfig()
        self.node_id = self.config.node_id
        self.state = NodeState.INITIALIZING
        self.role = NodeRole.WORKER
        self._task_count = 0
        self._total_load = 0.0
        self._last_activity = time.time()

        self_member = GossipMember(
            node_id=self.node_id,
            address=self.config.address,
            port=self.config.port,
            metadata={"role": self.role.value, "capabilities": set()},
        )
        self.gossip = GossipProtocol(
            self_node=self_member,
            probe_interval=self.config.gossip_interval,
            suspect_timeout=self.config.suspect_timeout,
            dead_timeout=self.config.dead_timeout,
            gossip_fanout=self.config.gossip_fanout,
        )

        self.shared_state = CRDTMap(self.node_id)
        self.known_tasks = ORSet(self.node_id)
        self.node_info = LWWRegister(self.node_id, None)

        self._message_handlers: dict[str, list[Callable]] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._tasks: list[asyncio.Task] = []

        self.gossip.on("member_join", self._on_member_join)
        self.gossip.on("member_leave", self._on_member_leave)
        self.gossip.on("member_suspect", self._on_member_suspect)

    async def start(self) -> None:
        self.state = NodeState.ACTIVE
        self._running = True
        await self.gossip.start()
        self.node_info.set({
            "node_id": self.node_id,
            "role": self.role.value,
            "state": self.state.value,
            "started_at": time.time(),
        })
        self._tasks.append(asyncio.create_task(self._task_loop()))
        self._tasks.append(asyncio.create_task(self._auto_manage_loop()))
        logger.info(f"Mesh节点启动: {self.node_id} ({self.role.value})")

    async def stop(self) -> None:
        self.state = NodeState.TERMINATED
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.gossip.stop()
        logger.info(f"Mesh节点停止: {self.node_id}")

    async def spawn_child(self, task_type: str, config_override: dict | None = None) -> str:
        """Agent自生育：按负载自主spawn子Agent。"""
        child_id = f"agent-{uuid.uuid4().hex[:8]}"
        child_meta = {
            "parent": self.node_id,
            "task_type": task_type,
            "spawned_at": time.time(),
            **(config_override or {}),
        }
        child_member = GossipMember(
            node_id=child_id,
            address=self.config.address,
            port=self.config.port + hash(child_id) % 1000 + 1,
            metadata=child_meta,
        )
        self.gossip.add_member(child_member)
        self.shared_state.merge(CRDTMap(child_id))
        logger.info(f"Agent自生育: {child_id} (任务={task_type})")
        return child_id

    async def terminate_self(self, reason: str = "idle") -> None:
        """Agent自消亡：空闲超时自主terminate释放资源。"""
        self.state = NodeState.TERMINATED
        logger.info(f"Agent自消亡: {self.node_id} (原因={reason})")
        await self.stop()

    async def send_task(self, target: str, task: TaskMessage) -> None:
        task.source = self.node_id
        task.target = target
        self.known_tasks.add(task.task_id)
        self.shared_state.set(f"task:{task.task_id}", task)
        logger.debug(f"发送任务: {task.task_id} → {target}")

    async def broadcast_task(self, task: TaskMessage) -> None:
        task.source = self.node_id
        task.target = "broadcast"
        self.known_tasks.add(task.task_id)
        for member in self.gossip.get_alive_members():
            if member.node_id != self.node_id:
                self.shared_state.set(f"task:{task.task_id}:to:{member.node_id}", task)

    def on_message(self, task_type: str, handler: Callable) -> None:
        self._message_handlers.setdefault(task_type, []).append(handler)

    @property
    def load(self) -> float:
        alive = len(self.gossip.get_alive_members())
        if alive == 0:
            return 1.0
        return self._task_count / max(1, alive * 5)

    @property
    def is_idle(self) -> bool:
        return time.time() - self._last_activity > self.config.auto_hibernate_idle_seconds

    def update_capabilities(self, caps: set[str]) -> None:
        self.gossip.self_node.metadata["capabilities"] = caps

    def _on_member_join(self, member: GossipMember) -> None:
        logger.info(f"Mesh拓扑变更: {member.key} 加入 (当前{len(self.gossip.members)}节点)")

    def _on_member_leave(self, member: GossipMember) -> None:
        logger.info(f"Mesh拓扑变更: {member.key} 离开，待接管其任务")

    def _on_member_suspect(self, member: GossipMember) -> None:
        logger.warning(f"Mesh健康预警: {member.key} 疑似离线")

    async def _task_loop(self) -> None:
        while self._running:
            try:
                priority, task = await asyncio.wait_for(
                    self._task_queue.get(), timeout=1.0
                )
                self._task_count += 1
                self._last_activity = time.time()
                handlers = self._message_handlers.get(task.task_type, [])
                for h in handlers:
                    try:
                        result = h(task)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error(f"任务处理异常: {e}")
                self._task_count -= 1
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _auto_manage_loop(self) -> None:
        while self._running:
            try:
                if self.is_idle and self.role == NodeRole.WORKER:
                    self.state = NodeState.HIBERNATING
                    logger.info(f"Agent自动休眠: {self.node_id}")
                elif self.state == NodeState.HIBERNATING and not self.is_idle:
                    self.state = NodeState.ACTIVE
                    logger.info(f"Agent自动唤醒: {self.node_id}")
                if self.load > self.config.auto_fission_load_threshold:
                    logger.info(f"负载过高({self.load:.2f})，考虑自分裂")
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自管理循环异常: {e}")
                await asyncio.sleep(10.0)

    def get_status(self) -> dict:
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "state": self.state.value,
            "load": self.load,
            "task_count": self._task_count,
            "mesh_size": len(self.gossip.members),
            "alive_members": len(self.gossip.get_alive_members()),
        }
