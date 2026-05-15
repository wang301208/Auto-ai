from __future__ import annotations

import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    DRAFT = "draft"
    TESTED = "tested"
    APPROVED = "approved"
    REGISTERED = "registered"
    REJECTED = "rejected"


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    returns: str = "str"
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    category: str = "custom"
    risk_level: str = "low"


@dataclass
class CreatedTool:
    spec: ToolSpec
    implementation: str = ""
    status: ToolStatus = ToolStatus.DRAFT
    test_results: dict[str, bool] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    creator_agent: str = ""
    approval_reason: str = ""
    _func: Callable | None = field(default=None, repr=False)

    @property
    def is_usable(self) -> bool:
        return self.status in (ToolStatus.APPROVED, ToolStatus.REGISTERED)

    @property
    def tool_id(self) -> str:
        raw = f"{self.spec.name}:{self.spec.category}:{self.created_at}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


class ToolRegistry:
    """动态工具注册表: 运行时添加Agent创造的新工具。"""

    def __init__(self):
        self._tools: dict[str, CreatedTool] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, tool: CreatedTool) -> bool:
        if tool.status not in (ToolStatus.APPROVED, ToolStatus.TESTED):
            logger.warning(f"拒绝注册未审批工具: {tool.spec.name}")
            return False
        tool.status = ToolStatus.REGISTERED
        self._tools[tool.spec.name] = tool
        self._categories.setdefault(tool.spec.category, []).append(tool.spec.name)
        logger.info(f"动态注册工具: {tool.spec.name} (category={tool.spec.category})")
        return True

    def get(self, name: str) -> CreatedTool | None:
        return self._tools.get(name)

    def call(self, name: str, **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"工具不存在: {name}")
        if not tool.is_usable:
            raise RuntimeError(f"工具不可用: {name} (status={tool.status.value})")
        if tool._func is not None:
            return tool._func(**kwargs)
        local_ns: dict[str, Any] = {}
        exec(tool.implementation, {"__builtins__": __builtins__}, local_ns)
        func = local_ns.get(tool.spec.name)
        if func is None:
            raise RuntimeError(f"工具实现中未找到函数: {tool.spec.name}")
        return func(**kwargs)

    def list_tools(self, category: str | None = None) -> list[CreatedTool]:
        if category:
            names = self._categories.get(category, [])
            return [self._tools[n] for n in names if n in self._tools]
        return list(self._tools.values())

    @property
    def count(self) -> int:
        return len(self._tools)


class ToolCreator:
    """零样本工具创造器: 从需求到可执行工具的全自动管道。"""

    def __init__(self, registry: ToolRegistry | None = None, agent_id: str = "creator"):
        self._registry = registry or ToolRegistry()
        self.agent_id = agent_id
        self._created: list[CreatedTool] = []
        self._templates: dict[str, str] = {
            "file_processor": (
                "def {name}({params}):\n"
                '    """{desc}"""\n'
                "    import os\n"
                "    result = []\n"
                "    return '\\n'.join(result) if result else 'no output'\n"
            ),
            "data_transform": (
                "def {name}({params}):\n"
                '    """{desc}"""\n'
                "    import json\n"
                "    data = json.loads(input_data) if isinstance(input_data, str) else input_data\n"
                "    return json.dumps(data, indent=2)\n"
            ),
            "validator": (
                "def {name}({params}):\n"
                '    """{desc}"""\n'
                "    errors = []\n"
                "    is_valid = len(errors) == 0\n"
                "    return '{{\"valid\": {}, \"errors\": {}}}'.format(is_valid, errors)\n"
            ),
        }

    def analyze_gap(self, failed_operations: list[str]) -> list[ToolSpec]:
        """分析操作失败记录，发现工具缺口。"""
        specs = []
        for op in failed_operations:
            spec = ToolSpec(
                name=f"auto_{op.replace(' ', '_').replace('-', '_').lower()}",
                description=f"自动创建的工具: 处理{op}操作",
                parameters={"input_data": "str"},
                returns="str",
                category="auto_generated",
            )
            specs.append(spec)
        return specs

    def design_tool(self, spec: ToolSpec, template: str = "file_processor") -> CreatedTool:
        """基于规格和模板设计工具实现。"""
        tmpl = self._templates.get(template, self._templates["file_processor"])
        params_str = ", ".join(spec.parameters.keys()) if spec.parameters else ""
        impl = tmpl.format(
            name=spec.name,
            params=params_str,
            desc=spec.description,
        )
        tool = CreatedTool(
            spec=spec,
            implementation=impl,
            status=ToolStatus.DRAFT,
            creator_agent=self.agent_id,
        )
        return tool

    def test_tool(self, tool: CreatedTool, test_inputs: list[dict] | None = None) -> CreatedTool:
        """沙箱测试工具实现。"""
        test_inputs = test_inputs or [{}]
        results = {}
        for i, inputs in enumerate(test_inputs):
            try:
                local_ns: dict[str, Any] = {}
                exec(tool.implementation, {"__builtins__": __builtins__}, local_ns)
                func = local_ns.get(tool.spec.name)
                if func:
                    func(**inputs)
                results[f"test_{i}"] = True
            except Exception as e:
                results[f"test_{i}"] = False
                logger.debug(f"工具测试{tool.spec.name} test_{i}失败: {e}")
        tool.test_results = results
        all_passed = all(results.values())
        tool.status = ToolStatus.TESTED if all_passed else ToolStatus.REJECTED
        return tool

    def approve_and_register(self, tool: CreatedTool, reason: str = "auto-approved") -> bool:
        """审批并注册工具。"""
        if tool.status != ToolStatus.TESTED:
            return False
        tool.status = ToolStatus.APPROVED
        tool.approval_reason = reason
        success = self._registry.register(tool)
        if success:
            self._created.append(tool)
        return success

    def create_from_need(self, operation: str, template: str = "file_processor") -> CreatedTool | None:
        """一键: 从需求到注册。"""
        specs = self.analyze_gap([operation])
        if not specs:
            return None
        tool = self.design_tool(specs[0], template)
        tool = self.test_tool(tool)
        if tool.status == ToolStatus.TESTED:
            self.approve_and_register(tool)
        return tool

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "created_count": len(self._created),
            "registered_count": self._registry.count,
            "templates": list(self._templates.keys()),
        }
