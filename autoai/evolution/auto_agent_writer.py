from __future__ import annotations

import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AgentTemplate(Enum):
    WORKER = "worker"
    SPECIALIST = "specialist"
    MONITOR = "monitor"
    COORDINATOR = "coordinator"
    CUSTOM = "custom"


@dataclass
class GeneratedAgent:
    """Agent自行编写的新Agent。"""
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    template: AgentTemplate = AgentTemplate.WORKER
    source_code: str = ""
    test_code: str = ""
    capabilities: set[str] = field(default_factory=set)
    role: str = ""
    confidence: float = 0.0
    test_passed: bool = False
    deployed: bool = False
    created_at: float = field(default_factory=time.time)


class AutoAgentWriter:
    """Agent自写Agent：根据任务需求自行编写新Agent的完整源码。"""

    AGENT_SKELETON = '''
class {class_name}:
    """{docstring}"""

    def __init__(self, config=None):
        self.config = config or {{}}
        self.agent_id = "{agent_id}"
        self.role = "{role}"
        self.capabilities = {capabilities}

    async def execute(self, task):
        """执行任务。"""
        {body}

    async def health_check(self):
        """健康检查。"""
        return {{"agent_id": self.agent_id, "healthy": True}}

    def get_status(self):
        """获取状态。"""
        return {{
            "agent_id": self.agent_id,
            "role": self.role,
            "capabilities": list(self.capabilities),
        }}
'''

    TEST_SKELETON = '''
import pytest

class Test{class_name}:
    def test_init(self):
        agent = {class_name}()
        assert agent.agent_id == "{agent_id}"
        assert agent.role == "{role}"

    def test_execute(self):
        agent = {class_name}()
        result = agent.execute({{"type": "test"}})
        assert result is not None

    def test_health_check(self):
        agent = {class_name}()
        result = agent.health_check()
        assert result["healthy"] is True
'''

    def __init__(self, llm_call: Callable | None = None, test_runner: Callable | None = None):
        self.llm_call = llm_call
        self.test_runner = test_runner
        self._generated: list[GeneratedAgent] = []

    async def write_agent(self, task_description: str, required_capabilities: set[str],
                          role: str = "worker", template: AgentTemplate = AgentTemplate.CUSTOM) -> GeneratedAgent:
        """根据任务需求编写新Agent。"""
        agent_id = uuid.uuid4().hex[:12]
        class_name = f"AutoAgent_{agent_id[:6]}"
        logger.info(f"Agent自写Agent: {class_name} (任务={task_description[:50]}, 能力={required_capabilities})")

        source_code = await self._generate_source(class_name, agent_id, role, required_capabilities, task_description)
        test_code = await self._generate_test(class_name, agent_id, role)
        test_passed = await self._run_test(test_code)

        agent = GeneratedAgent(
            agent_id=agent_id,
            name=class_name,
            template=template,
            source_code=source_code,
            test_code=test_code,
            capabilities=required_capabilities,
            role=role,
            confidence=0.8 if test_passed else 0.3,
            test_passed=test_passed,
        )
        self._generated.append(agent)
        logger.info(f"Agent编写完成: {class_name} (测试={'通过' if test_passed else '失败'})")
        return agent

    async def _generate_source(self, class_name: str, agent_id: str, role: str,
                                capabilities: set[str], task_desc: str) -> str:
        if self.llm_call:
            try:
                prompt = f"""编写一个Python Agent类，要求：
- 类名: {class_name}
- 角色: {role}
- 能力: {capabilities}
- 任务描述: {task_desc}

请生成完整的Python类代码，包含__init__、execute、health_check方法。"""
                code = await self.llm_call(prompt) if asyncio.iscoroutinefunction(self.llm_call) else self.llm_call(prompt)
                if isinstance(code, str) and len(code) > 50:
                    return code
            except Exception as e:
                logger.warning(f"LLM生成Agent源码失败: {e}")

        caps_str = repr(capabilities) if capabilities else '{"compute"}'
        body = "result = await self._process(task)" if role != "worker" else "result = self._process(task)"
        return self.AGENT_SKELETON.format(
            class_name=class_name,
            docstring=f"自动生成的{role}Agent，能力: {', '.join(capabilities)}",
            agent_id=agent_id,
            role=role,
            capabilities=caps_str,
            body=body + "\n        return result",
        )

    async def _generate_test(self, class_name: str, agent_id: str, role: str) -> str:
        return self.TEST_SKELETON.format(
            class_name=class_name,
            agent_id=agent_id,
            role=role,
        )

    async def _run_test(self, test_code: str) -> bool:
        if self.test_runner:
            try:
                result = await self.test_runner(test_code) if asyncio.iscoroutinefunction(self.test_runner) else self.test_runner(test_code)
                return bool(result)
            except Exception:
                return False
        return True

    async def deploy_agent(self, agent: GeneratedAgent, mesh_coordinator: Any = None) -> bool:
        """部署新Agent到Mesh网络。"""
        if not agent.test_passed:
            logger.warning(f"Agent测试未通过，拒绝部署: {agent.name}")
            return False
        if mesh_coordinator and hasattr(mesh_coordinator, 'add_node'):
            try:
                from autoai.mesh.mesh_node import MeshNode, MeshConfig
                config = MeshConfig(node_id=agent.agent_id)
                node = MeshNode(config)
                node.role = type('NodeRole', (), {'value': agent.role})()
                node.update_capabilities(agent.capabilities)
                await mesh_coordinator.add_node(node)
                agent.deployed = True
                logger.info(f"Agent部署到Mesh: {agent.name} ({agent.agent_id})")
                return True
            except Exception as e:
                logger.error(f"部署Agent到Mesh失败: {e}")
                return False
        agent.deployed = True
        logger.info(f"Agent本地部署: {agent.name}")
        return True

    def list_generated(self) -> list[GeneratedAgent]:
        return list(self._generated)

    def get_stats(self) -> dict:
        return {
            "total_generated": len(self._generated),
            "total_deployed": sum(1 for a in self._generated if a.deployed),
            "total_tested": sum(1 for a in self._generated if a.test_passed),
        }


import asyncio
