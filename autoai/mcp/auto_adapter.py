from __future__ import annotations

import re
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class APIEndpoint:
    path: str
    method: str = "GET"
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class GeneratedAdapter:
    target_framework: str
    adapter_code: str
    tool_mappings: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


class MCPAutoAdapter:
    """Agent自写协议适配器: 遇到新框架, 自行阅读API文档, 生成MCP适配代码。"""

    FRAMEWORK_PATTERNS = {
        "langchain": {
            "identifiers": ["langchain", "LangChain", "Chain", "AgentExecutor"],
            "adapter_template": (
                "class LangChainMCPAdapter:\n"
                "    # LangChain -> MCP adapter (auto-generated)\n"
                "    def __init__(self, mcp_client):\n"
                "        self.mcp_client = mcp_client\n"
                "\n"
                "    def chain_to_mcp_tool(self, chain):\n"
                "        return MCPTool(\n"
                "            name=f'lc_{chain.__class__.__name__}',\n"
                "            description=chain.__doc__ or 'LangChain chain',\n"
                "            input_schema=self._infer_schema(chain),\n"
                "        )\n"
                "\n"
                "    def _infer_schema(self, chain):\n"
                "        if hasattr(chain, 'input_schema'):\n"
                "            return chain.input_schema.schema()\n"
                "        return {'query': {'type': 'string', 'description': 'input query'}}\n"
            ),
        },
        "crewai": {
            "identifiers": ["crewai", "CrewAI", "Crew", "Agent", "Task"],
            "adapter_template": (
                "class CrewAIMCPAdapter:\n"
                "    # CrewAI -> MCP adapter (auto-generated)\n"
                "    def __init__(self, mcp_client):\n"
                "        self.mcp_client = mcp_client\n"
                "\n"
                "    def crew_to_mcp_tool(self, crew):\n"
                "        return MCPTool(\n"
                "            name=f'crew_{crew.__class__.__name__}',\n"
                "            description=getattr(crew, 'goal', 'CrewAI crew'),\n"
                "            input_schema={'task': {'type': 'string', 'description': 'task desc'}},\n"
                "        )\n"
            ),
        },
        "autogen": {
            "identifiers": ["autogen", "AutoGen", "AssistantAgent", "GroupChat"],
            "adapter_template": (
                "class AutoGenMCPAdapter:\n"
                "    # AutoGen -> MCP adapter (auto-generated)\n"
                "    def __init__(self, mcp_client):\n"
                "        self.mcp_client = mcp_client\n"
                "\n"
                "    def agent_to_mcp_tool(self, agent):\n"
                "        return MCPTool(\n"
                "            name=f'ag_{agent.name}',\n"
                "            description=getattr(agent, 'system_message', 'AutoGen agent'),\n"
                "            input_schema={'message': {'type': 'string', 'description': 'message'}},\n"
                "        )\n"
            ),
        },
    }

    def __init__(self):
        self._generated_adapters: dict[str, GeneratedAdapter] = {}
        self._api_patterns: list[re.Pattern] = [
            re.compile(r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE),
            re.compile(r'@(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE),
            re.compile(r'def\s+(\w+)\s*\([^)]*\)\s*:', re.MULTILINE),
        ]

    def detect_framework(self, api_docs: str) -> str | None:
        best_match = None
        best_score = 0
        for framework, config in self.FRAMEWORK_PATTERNS.items():
            score = sum(1 for ident in config["identifiers"] if ident.lower() in api_docs.lower())
            if score > best_score:
                best_score = score
                best_match = framework
        return best_match if best_score > 0 else None

    def generate_adapter(self, target_framework: str, api_docs: str = "") -> GeneratedAdapter:
        config = self.FRAMEWORK_PATTERNS.get(target_framework)
        if config:
            adapter_code = config["adapter_template"]
            confidence = 0.85
        else:
            adapter_code = self._generate_generic_adapter(api_docs, target_framework)
            confidence = 0.4
        adapter = GeneratedAdapter(
            target_framework=target_framework,
            adapter_code=adapter_code,
            confidence=confidence,
        )
        self._generated_adapters[target_framework] = adapter
        logger.info(f"生成MCP适配器: {target_framework} (置信度={confidence:.2f})")
        return adapter

    def _generate_generic_adapter(self, api_docs: str, framework_name: str) -> str:
        endpoints = self._extract_endpoints(api_docs)
        methods = []
        for ep in endpoints:
            method_name = self._path_to_method(ep.path)
            methods.append(f"    def {method_name}(self, **kwargs): return self.mcp_client.call_tool('{framework_name}_{method_name}', kwargs)")
        body = "\n".join(methods) if methods else "    pass"
        return (
            f"class {framework_name.capitalize()}MCPAdapter:\n"
            f"    # {framework_name} -> MCP generic adapter (auto-generated)\n"
            f"    def __init__(self, mcp_client):\n"
            f"        self.mcp_client = mcp_client\n"
            f"{body}\n"
        )

    def _extract_endpoints(self, api_docs: str) -> list[APIEndpoint]:
        endpoints = []
        for pattern in self._api_patterns:
            for match in pattern.finditer(api_docs):
                groups = match.groups()
                if len(groups) >= 2:
                    endpoints.append(APIEndpoint(path=groups[1], method=groups[0].upper()))
                elif len(groups) == 1:
                    endpoints.append(APIEndpoint(path=groups[0]))
        return endpoints[:50]

    @staticmethod
    def _path_to_method(path: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', path).strip('_')
        parts = clean.split('_')
        return parts[0] + ''.join(p.capitalize() for p in parts[1:]) if parts else 'unknown'

    def get_adapter(self, framework: str) -> GeneratedAdapter | None:
        return self._generated_adapters.get(framework)

    def list_adapters(self) -> list[str]:
        return list(self._generated_adapters.keys())
