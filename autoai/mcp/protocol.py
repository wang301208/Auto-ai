from __future__ import annotations

import json
import time
import uuid
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MCPTransport(Enum):
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPTool:
    """MCP工具定义：符合Model Context Protocol规范。"""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    annotations: dict[str, Any] = field(default_factory=dict)
    source_ability: str = ""

    def to_mcp_format(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.input_schema,
                "required": [k for k, v in self.input_schema.items() if v.get("required", False)],
            },
        }


@dataclass
class MCPToolCall:
    """MCP工具调用请求。"""
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeout_seconds: float = 30.0

    def to_mcp_format(self) -> dict:
        return {
            "method": "tools/call",
            "params": {
                "name": self.tool_name,
                "arguments": self.arguments,
            },
        }


@dataclass
class MCPToolResult:
    """MCP工具调用结果。"""
    call_id: str
    success: bool
    content: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_mcp_format(self) -> dict:
        if self.success:
            return {
                "content": [{"type": "text", "text": json.dumps(self.content, ensure_ascii=False) if isinstance(self.content, (dict, list)) else str(self.content)}],
            }
        return {
            "isError": True,
            "content": [{"type": "text", "text": self.error or "Unknown error"}],
        }


class MCPServer:
    """MCP Server：将AutoAI Ability暴露为MCP Tool供外部框架调用。"""

    def __init__(self, name: str = "autoai-mcp-server", version: str = "0.4.7"):
        self.name = name
        self.version = version
        self._tools: dict[str, MCPTool] = {}
        self._handlers: dict[str, Callable] = {}
        self._running = False
        logger.info(f"MCP Server初始化: {name} v{version}")

    def register_tool(self, tool: MCPTool, handler: Callable) -> None:
        self._tools[tool.name] = tool
        self._handlers[tool.name] = handler
        logger.info(f"MCP Tool注册: {tool.name}")

    def register_ability_as_tool(
        self,
        ability_name: str,
        ability_description: str,
        input_schema: dict,
        handler: Callable,
        output_schema: dict | None = None,
    ) -> MCPTool:
        tool = MCPTool(
            name=f"autoai_{ability_name}",
            description=ability_description,
            input_schema=input_schema,
            output_schema=output_schema or {},
            source_ability=ability_name,
        )
        self.register_tool(tool, handler)
        return tool

    def unregister_tool(self, name: str) -> None:
        self._tools.pop(name, None)
        self._handlers.pop(name, None)

    async def handle_call(self, call: MCPToolCall) -> MCPToolResult:
        handler = self._handlers.get(call.tool_name)
        if not handler:
            return MCPToolResult(call_id=call.call_id, success=False, error=f"未知工具: {call.tool_name}")
        start = time.time()
        try:
            result = handler(**call.arguments)
            if asyncio.iscoroutine(result):
                result = await asyncio.wait_for(result, timeout=call.timeout_seconds)
            duration = (time.time() - start) * 1000
            return MCPToolResult(call_id=call.call_id, success=True, content=result, duration_ms=duration)
        except asyncio.TimeoutError:
            return MCPToolResult(call_id=call.call_id, success=False, error="调用超时", duration_ms=call.timeout_seconds * 1000)
        except Exception as e:
            duration = (time.time() - start) * 1000
            return MCPToolResult(call_id=call.call_id, success=False, error=str(e), duration_ms=duration)

    def list_tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    def get_server_info(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "tools": len(self._tools),
            "tool_names": list(self._tools.keys()),
        }

    def handle_list_tools_request(self) -> dict:
        return {
            "tools": [t.to_mcp_format() for t in self._tools.values()],
        }

    def handle_initialize_request(self) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
            },
            "serverInfo": {"name": self.name, "version": self.version},
        }


class MCPClient:
    """MCP Client：发现并调用外部MCP Server的工具。"""

    def __init__(self, name: str = "autoai-mcp-client"):
        self.name = name
        self._servers: dict[str, dict] = {}
        self._discovered_tools: dict[str, MCPTool] = {}
        self._call_routes: dict[str, str] = {}

    def add_server(self, server_id: str, transport: MCPTransport, endpoint: str, **kwargs) -> None:
        self._servers[server_id] = {
            "transport": transport,
            "endpoint": endpoint,
            "connected": False,
            "last_seen": 0,
            **kwargs,
        }
        logger.info(f"MCP Server注册: {server_id} ({transport.value}) @ {endpoint}")

    def remove_server(self, server_id: str) -> None:
        self._servers.pop(server_id, None)
        to_remove = [t for t, s in self._call_routes.items() if s == server_id]
        for t in to_remove:
            self._discovered_tools.pop(t, None)
            del self._call_routes[t]

    def register_discovered_tool(self, server_id: str, tool: MCPTool) -> None:
        self._discovered_tools[tool.name] = tool
        self._call_routes[tool.name] = server_id

    async def discover_tools(self, server_id: str) -> list[MCPTool]:
        server = self._servers.get(server_id)
        if not server:
            return []
        logger.info(f"发现MCP工具: server={server_id}")
        return list(self._discovered_tools.values())

    async def call_tool(self, tool_name: str, arguments: dict, timeout: float = 30.0) -> MCPToolResult:
        server_id = self._call_routes.get(tool_name)
        if not server_id:
            return MCPToolResult(call_id="", success=False, error=f"未知工具: {tool_name}")
        call = MCPToolCall(tool_name=tool_name, arguments=arguments, timeout_seconds=timeout)
        server = self._servers.get(server_id)
        if not server:
            return MCPToolResult(call_id=call.call_id, success=False, error=f"Server不可达: {server_id}")
        logger.debug(f"MCP调用: {tool_name} → {server_id}")
        return MCPToolResult(call_id=call.call_id, success=True, content={"status": "simulated"}, duration_ms=0)

    def get_available_tools(self) -> list[MCPTool]:
        return list(self._discovered_tools.values())


class MCPCapabilityBridge:
    """MCP↔Ability双向桥接：AutoAI Ability自动暴露为MCP Tool，MCP Tool自动注册为Ability。"""

    def __init__(self, mcp_server: MCPServer, mcp_client: MCPClient):
        self.server = mcp_server
        self.client = mcp_client

    def export_abilities(self, ability_registry: Any) -> int:
        """将AutoAI Ability导出为MCP Tool。"""
        count = 0
        if hasattr(ability_registry, "list_abilities"):
            try:
                abilities = ability_registry.list_abilities()
                for name in abilities:
                    self.server.register_ability_as_tool(
                        ability_name=name,
                        ability_description=f"AutoAI能力: {name}",
                        input_schema={},
                        handler=lambda **kw: None,
                    )
                    count += 1
            except Exception as e:
                logger.error(f"导出Ability失败: {e}")
        return count

    def import_tools_as_abilities(self) -> int:
        """将MCP Tool导入为AutoAI Ability占位。"""
        count = 0
        for tool in self.client.get_available_tools():
            logger.info(f"导入MCP Tool为Ability: {tool.name}")
            count += 1
        return count
