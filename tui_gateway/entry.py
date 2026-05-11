"""JSON-RPC backend for the terminal UI.

The terminal frontend owns rendering. This process owns sessions, runtime calls,
slash commands, completions, and prompt/approval flows. The transport uses
newline-delimited JSON-RPC over standard streams:

- stdin receives newline-delimited JSON-RPC requests
- stdout emits JSON-RPC responses and `method: "event"` notifications
- stderr is reserved for logs and is surfaced by the frontend
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import yaml

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("tui_gateway")


SlashCommand = dict[str, str]
APPROVAL_TIMEOUT_SECONDS = 30
AUTONOMY_LEVEL = "bounded_autonomous_maintenance"
APPROVAL_POLICY_BYPASS_METHODS = {"approval.respond", "governance.decide"}
PUBLIC_DIRECT_METHODS = {
    "approval.respond",
    "clarify.respond",
    "clipboard.paste",
    "command.dispatch",
    "complete.path",
    "complete.slash",
    "input.interpolate",
    "model.options",
    "model.providers",
    "natural.capabilities",
    "natural.invoke",
    "natural.resolve",
    "prompt.submit",
    "session.create",
    "session.interrupt",
    "session.list",
    "session.resume",
    "slash.exec",
}

MODEL_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-405b-instruct"],
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "models": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "nous": {
        "name": "Nous Portal",
        "base_url": "https://inference-api.nousresearch.com/v1",
        "api_key_env": "NOUS_API_KEY",
        "models": ["portal-chat", "portal-reasoning"],
        "auth_types": ["api_key", "oauth"],
    },
    "openai_compatible": {
        "name": "OpenAI-compatible",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "models": ["gpt-4o-mini", "custom-model"],
    },
    "custom": {
        "name": "自定义 OpenAI 兼容模型",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "models": ["custom-model"],
    },
}

CUSTOM_MODEL_PROVIDER_SLUG = "custom"
VISIBLE_MODEL_PROVIDER_SLUGS = (CUSTOM_MODEL_PROVIDER_SLUG,)


SLASH_COMMANDS: list[SlashCommand] = [
    {"text": "/help", "display": "/help", "meta": "显示可用命令"},
    {"text": "/new", "display": "/new [会话编号]", "meta": "开启新会话，或继续指定历史会话"},
    {"text": "/model", "display": "/model [模型名]", "meta": "打开模型选择器，或切换模型"},
]


NATURAL_DIRECT_ALIASES: dict[str, list[str]] = {
    "natural.capabilities": ["help", "commands", "帮助", "命令", "怎么用"],
    "session.create": ["clear", "清屏", "清空", "清除记录", "new session", "新会话", "重新开始"],
    "runtime.status_snapshot": ["status", "runtime status", "状态", "运行状态", "当前状态"],
    "runtime.health": ["health", "health report", "健康", "健康报告", "体检"],
    "runtime.preflight": ["preflight", "readiness", "预检", "就绪", "准备情况"],
    "runtime.write_preflight": ["write preflight", "save preflight", "写入预检", "保存预检", "生成预检报告"],
    "runtime.host_probe": ["host", "host probe", "主机", "宿主机", "环境探测"],
    "runtime.messaging_status": ["messaging", "message gateway", "通讯", "通信", "飞书", "钉钉", "微信"],
    "runtime.blueprints": ["blueprints", "agents", "蓝图", "智能体列表", "角色"],
    "runtime.skills": ["skills", "技能", "能力"],
    "runtime.algorithms": ["algorithms", "算法", "实验"],
    "runtime.audits": ["audits", "audit", "审计", "审核记录"],
    "runtime.avatar": ["avatar", "形象", "表情", "动画"],
    "runtime.events": ["events", "事件", "运行事件"],
    "runtime.terminal_ui": ["terminal ui", "tui", "终端界面", "界面状态", "details", "detail", "详情", "详细信息"],
    "runtime.operational_smoke": ["smoke", "smoke test", "冒烟", "冒烟测试"],
    "runtime.interaction_stress": ["stress", "stress test", "压测", "压力测试"],
    "governance.requests": ["approvals", "approval queue", "审批", "审核", "审批列表", "待审批"],
    "runtime.adapters": ["tools", "tool list", "工具", "工具列表"],
    "model.options": ["model", "模型", "当前模型"],
    "session.usage": ["usage", "tokens", "用量", "token", "消耗"],
    "runtime.logs": ["logs", "log", "日志"],
    "session.status": ["queue", "队列", "排队"],
    "session.list": ["resume", "恢复会话", "会话列表"],
    "session.compress": ["compact", "compress context", "压缩", "压缩上下文", "上下文压缩"],
    "session.steer": ["personality", "persona", "style", "个性", "人格", "风格"],
    "session.save": ["save session", "save transcript", "保存会话", "保存记录"],
    "session.close": ["quit", "exit", "q", "退出", "关闭", "结束", "快速退出"],
}

AUTONOMOUS_SYSTEM_METHODS: set[str] = {
    "runtime.status_snapshot",
    "runtime.health",
    "runtime.preflight",
    "runtime.write_preflight",
    "runtime.write_host_probe",
    "runtime.host_probe",
    "runtime.adapters",
    "runtime.logs",
    "runtime.events",
    "runtime.terminal_ui",
    "runtime.operational_smoke",
    "runtime.interaction_stress",
    "session.status",
    "session.usage",
    "session.list",
    "session.resume",
    "session.compress",
    "session.save",
    "memory.periodic_tick",
    "self_model.update",
    "user_model.update",
    "skill.autonomous_from_task",
    "skill.improve_from_usage",
    "development.task.start",
    "development.task.status",
    "development.task.resume",
    "development.task.verify",
    "development.task.learn",
}

NATURAL_BACKEND_ACTIONS: list[dict[str, Any]] = [
    {
        "command": "runtime.adapters",
        "method": "runtime.adapters",
        "description": "显示适配器与模型连接器健康状态。",
        "aliases": [
            "adapter health",
            "adapter status",
            "show adapter health",
            "list adapters",
            "adapters",
        ],
    },
    {
        "command": "runtime.platform_message",
        "method": "runtime.platform_message",
        "description": "将平台消息路由到运行时。",
        "aliases": [
            "platform message",
            "send platform message",
            "route platform message",
            "handle platform message",
        ],
    },
    {
        "command": "runtime.final_acceptance",
        "method": "runtime.final_acceptance",
        "description": "运行并写入最终后端验收报告。",
        "aliases": ["final acceptance", "acceptance report", "最终验收", "验收报告"],
    },
    {
        "command": "governance.requests",
        "method": "governance.requests",
        "description": "列出治理审批请求。",
        "aliases": ["governance requests", "approval requests", "治理请求", "审批请求"],
    },
    {
        "command": "governance.decide",
        "method": "governance.decide",
        "description": "按 ID 同意或拒绝治理请求。",
        "aliases": ["decide approval", "approve request", "reject request", "审批决定"],
    },
    {
        "command": "approval.respond",
        "method": "approval.respond",
        "description": "同意或拒绝待处理的 TUI 审批请求。",
        "aliases": [
            "approve latest request",
            "approve request",
            "deny request",
            "reject request",
        ],
    },
    {
        "command": "skill.request_publish",
        "method": "skill.request_publish",
        "description": "创建技能发布审批请求。",
        "aliases": ["publish skill request", "request skill publish", "技能发布请求"],
    },
    {
        "command": "algorithm.request_research",
        "method": "algorithm.request_research",
        "description": "创建算法研究审批请求。",
        "aliases": ["algorithm research request", "算法研究请求"],
    },
    {
        "command": "organization.request_change",
        "method": "organization.request_change",
        "description": "创建组织变更审批请求。",
        "aliases": ["organization change request", "组织变更请求"],
    },
    {
        "command": "conversation.record",
        "method": "conversation.record",
        "description": "将一轮对话写入跨会话记忆。",
        "aliases": ["record conversation", "remember conversation", "store session memory"],
    },
    {
        "command": "memory.periodic_tick",
        "method": "memory.periodic_tick",
        "description": "运行一次计划记忆与规划周期。",
        "aliases": ["periodic memory", "memory tick", "planning tick"],
    },
    {
        "command": "user_model.update",
        "method": "user_model.update",
        "description": "更新辩证用户模型。",
        "aliases": ["update user model", "honcho user model", "dialectic user model"],
    },
    {
        "command": "user_model.query",
        "method": "user_model.query",
        "description": "查询辩证用户模型。",
        "aliases": ["query user model", "read user model", "user preferences"],
    },
    {
        "command": "skill.autonomous_from_task",
        "method": "skill.autonomous_from_task",
        "description": "在复杂任务后生成技能草案。",
        "aliases": ["create skill from task", "autonomous skill", "draft skill from complex task"],
    },
    {
        "command": "skill.improve_from_usage",
        "method": "skill.improve_from_usage",
        "description": "根据使用反馈改进技能草案。",
        "aliases": ["improve skill", "skill feedback", "self improve skill"],
    },
    {
        "command": "skill.merge_preview",
        "method": "skill.merge_preview",
        "description": "预览多个技能的确定性合并结果。",
        "aliases": [
            "preview skill merge",
            "skill merge preview",
            "merge skills preview",
            "check skill merge",
            "技能合并预览",
        ],
    },
    {
        "command": "skill.merge",
        "method": "skill.merge",
        "description": "将多个技能合并为可发布的技能提案。",
        "aliases": [
            "merge skills",
            "skill merge",
            "combine skills",
            "consolidate skills",
            "合并技能",
            "技能合并",
        ],
    },
    {
        "command": "agent.parallel",
        "method": "agent.parallel",
        "description": "并发运行独立智能体或工具任务并合并结果。",
        "aliases": [
            "parallel agents",
            "parallel tools",
            "run tasks in parallel",
            "concurrent agents",
            "代理并行化",
            "并行代理",
            "并行执行",
            "并行工具",
        ],
    },
    {
        "command": "development.task.start",
        "method": "development.task.start",
        "description": "创建复杂开发任务，并自动完成规划、执行、验证与学习闭环。",
        "aliases": [
            "development task",
            "start development task",
            "autonomous development",
            "plan and execute development task",
            "复杂开发任务",
            "自主规划与执行",
            "自主开发任务",
            "完成复杂开发任务",
        ],
    },
    {
        "command": "development.task.status",
        "method": "development.task.status",
        "description": "查看持久化开发任务状态。",
        "aliases": ["development task status", "开发任务状态"],
    },
    {
        "command": "development.task.resume",
        "method": "development.task.resume",
        "description": "继续推进未完成开发任务。",
        "aliases": ["resume development task", "继续开发任务"],
    },
    {
        "command": "development.task.verify",
        "method": "development.task.verify",
        "description": "验证开发任务执行结果。",
        "aliases": ["verify development task", "验证开发任务"],
    },
    {
        "command": "development.task.learn",
        "method": "development.task.learn",
        "description": "将开发任务结果沉淀为经验或技能候选。",
        "aliases": ["learn from development task", "开发任务学习"],
    },
    {
        "command": "mcp.call",
        "method": "mcp.call",
        "description": "调用已配置 MCP 标准输入输出服务器上的工具。",
        "aliases": ["mcp call", "call mcp tool", "mcp tool", "调用 mcp 工具"],
    },
    {
        "command": "mcp.tools",
        "method": "mcp.tools",
        "description": "列出已配置 MCP 服务器暴露的工具。",
        "aliases": ["mcp tools", "list mcp tools", "mcp 工具"],
    },
    {
        "command": "cron.create",
        "method": "cron.create",
        "description": "创建持久化后端计划任务。",
        "aliases": ["create cron", "schedule task", "计划任务", "定时任务"],
    },
    {
        "command": "cron.run_due",
        "method": "cron.run_due",
        "description": "运行已到期的后端计划任务。",
        "aliases": ["run due cron", "run scheduled tasks", "执行到期任务"],
    },
    {
        "command": "context.attach",
        "method": "context.attach",
        "description": "将项目文件附加为提示上下文。",
        "aliases": ["attach context", "attach file", "添加上下文文件"],
    },
]

SHELL_INTENT_PREFIXES = [
    "run command",
    "execute command",
    "shell",
    "cmd",
    "运行命令",
    "执行命令",
    "帮我运行命令",
    "帮我执行命令",
    "帮我跑一下",
    "跑一下",
    "运行命令",
    "执行命令",
    "执行一下",
    "运行一下",
]


INTENT_BY_METHOD: dict[str, str] = {
    "agent.parallel": "agent.parallel",
    "approval.respond": "approval.respond",
    "conversation.search": "memory.search_conversation",
    "development.task.start": "development.task.start",
    "development.task.status": "development.task.status",
    "development.task.resume": "development.task.resume",
    "development.task.verify": "development.task.verify",
    "development.task.learn": "development.task.learn",
    "experience.record": "memory.record_experience",
    "experience.search": "memory.search_experience",
    "model.configure": "model.configure",
    "model.options": "model.options",
    "natural.capabilities": "ui.help",
    "prompt.submit": "conversation.chat",
    "runtime.final_acceptance": "runtime.final_acceptance",
    "runtime.platform_message": "messaging.send",
    "session.create": "session.create",
    "session.resume": "session.resume",
    "shell.exec": "system.shell_exec",
}

PLATFORM_ALIASES: dict[str, tuple[str, ...]] = {
    "feishu": ("feishu", "lark", "飞书", "椋炰功"),
    "dingtalk": ("dingtalk", "dingding", "钉钉", "閽夐拤"),
    "weixin": ("weixin", "wechat", "微信", "企业微信", "寰俊"),
}


TOOL_POLICIES: dict[str, dict[str, Any]] = {
    "runtime.health": {
        "auth_scope": "runtime:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "runtime.preflight": {
        "auth_scope": "runtime:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "runtime.platform_message": {
        "auth_scope": "runtime:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"platform": {"type": "string"}, "payload": {"type": "object"}},
            "required": ["platform", "payload"],
        },
        "retry": {"max_attempts": 2, "backoff_ms": 50, "retry_on": ["BACKEND_ERROR"]},
    },
    "runtime.final_acceptance": {
        "auth_scope": "runtime:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"stress_cycles": {"type": "integer", "minimum": 1, "maximum": 10}},
            "required": [],
        },
    },
    "runtime.adapters": {
        "auth_scope": "runtime:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "runtime.status_snapshot": {
        "auth_scope": "runtime:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "runtime.start": {
        "auth_scope": "runtime:control",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "runtime.stop": {
        "auth_scope": "runtime:control",
        "risk_level": "high",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "runtime.write_preflight": {
        "auth_scope": "runtime:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "session.status": {
        "auth_scope": "session:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "session.usage": {
        "auth_scope": "session:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "session.list": {
        "auth_scope": "session:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
            "required": [],
        },
    },
    "session.resume": {
        "auth_scope": "session:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": []},
    },
    "session.compress": {
        "auth_scope": "session:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {"trigger": {"type": "string"}}, "required": []},
    },
    "session.save": {
        "auth_scope": "session:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": []},
    },
    "session.close": {
        "auth_scope": "session:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "model.options": {
        "auth_scope": "model:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "model.configure": {
        "auth_scope": "model:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "base_url": {"type": "string"},
                "api_key_env": {"type": "string"},
                "dry_run": {"type": "boolean"},
            },
            "required": [],
        },
    },
    "model.setup": {
        "auth_scope": "model:write",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "base_url": {"type": "string"},
                "api_key": {"type": "string"},
                "api_key_env": {"type": "string"},
                "auth_type": {"type": "string"},
                "client_id": {"type": "string"},
                "auth_url": {"type": "string"},
                "token_url": {"type": "string"},
                "dry_run": {"type": "boolean"},
                "timeout": {"type": "number"},
                "temperature": {"type": "number"},
                "max_tokens": {},
            },
            "required": [],
        },
    },
    "natural.capabilities": {
        "auth_scope": "runtime:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "runtime.logs": {
        "auth_scope": "runtime:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {"lines": {"type": "integer", "minimum": 1, "maximum": 200}},
            "required": [],
        },
    },
    "session.steer": {
        "auth_scope": "session:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": []},
    },
    "experience.record": {
        "auth_scope": "memory:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "source": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["text"],
        },
    },
    "conversation.record": {
        "auth_scope": "memory:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "role": {"type": "string"},
                "text": {"type": "string"},
                "user_id": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["text"],
        },
    },
    "experience.search": {
        "auth_scope": "memory:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": ["query"],
        },
    },
    "conversation.search": {
        "auth_scope": "memory:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": ["query"],
        },
    },
    "memory.periodic_tick": {
        "auth_scope": "memory:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "cadence": {"type": "string"},
            },
            "required": ["task"],
        },
    },
    "self_model.read": {
        "auth_scope": "memory:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "self_model.update": {
        "auth_scope": "memory:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "observation": {"type": "string"},
                "capability": {"type": "string"},
                "preference": {"type": "string"},
            },
            "required": ["observation"],
        },
    },
    "user_model.update": {
        "auth_scope": "memory:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "observation": {"type": "string"},
            },
            "required": ["observation"],
        },
    },
    "user_model.query": {
        "auth_scope": "memory:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "question": {"type": "string"},
            },
            "required": [],
        },
    },
    "skill.draft_from_experience": {
        "auth_scope": "skill:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "skill_name": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    "skill.autonomous_from_task": {
        "auth_scope": "skill:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "task_text": {"type": "string"},
                "skill_name": {"type": "string"},
            },
            "required": ["task_text"],
        },
    },
    "skill.improve_from_usage": {
        "auth_scope": "skill:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"},
                "feedback": {"type": "string"},
            },
            "required": ["skill_name", "feedback"],
        },
    },
    "skill.merge_preview": {
        "auth_scope": "skill:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_paths": {"type": "array"},
                "merged_skill_name": {"type": "string"},
                "strategy": {"type": "string"},
            },
            "required": ["skill_paths"],
        },
    },
    "skill.merge": {
        "auth_scope": "skill:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_paths": {"type": "array"},
                "merged_skill_name": {"type": "string"},
                "strategy": {"type": "string"},
            },
            "required": ["skill_paths", "merged_skill_name"],
        },
    },
    "governance.requests": {
        "auth_scope": "governance:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {"status": {"type": "string"}}, "required": []},
    },
    "governance.decide": {
        "auth_scope": "governance:approve",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "decision": {"type": "string"},
                "decided_by": {"type": "string"},
                "comments": {"type": "string"},
            },
            "required": ["request_id", "decision"],
        },
    },
    "approval.respond": {
        "auth_scope": "governance:approve",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "decision": {"type": "string"},
            },
            "required": ["request_id", "decision"],
        },
    },
    "shell.exec": {
        "auth_scope": "shell:execute",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    },
    "organization.rollback": {
        "auth_scope": "organization:write",
        "risk_level": "critical",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "role_name": {"type": "string"},
                "requested_by": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["role_name"],
        },
    },
    "skill.request_publish": {
        "auth_scope": "skill:write",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {"proposal_dir": {"type": "string"}},
            "required": ["proposal_dir"],
        },
    },
    "skill.publish_approved": {
        "auth_scope": "skill:write",
        "risk_level": "high",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}, "parameters": {"type": "object"}},
            "required": ["request_id"],
        },
    },
    "algorithm.request_research": {
        "auth_scope": "algorithm:write",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {"proposal_path": {"type": "string"}},
            "required": ["proposal_path"],
        },
    },
    "algorithm.run_experiment": {
        "auth_scope": "algorithm:write",
        "risk_level": "high",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "dataset_path": {"type": "string"},
                "thresholds": {"type": "object"},
            },
            "required": ["request_id", "dataset_path", "thresholds"],
        },
    },
    "algorithm.request_promotion": {
        "auth_scope": "algorithm:write",
        "risk_level": "critical",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {"report_path": {"type": "string"}, "blueprint_path": {"type": "string"}},
            "required": ["report_path", "blueprint_path"],
        },
    },
    "algorithm.apply_promotion": {
        "auth_scope": "algorithm:write",
        "risk_level": "critical",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    },
    "organization.request_change": {
        "auth_scope": "organization:write",
        "risk_level": "critical",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {"proposal_path": {"type": "string"}},
            "required": ["proposal_path"],
        },
    },
    "organization.apply_change": {
        "auth_scope": "organization:write",
        "risk_level": "critical",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    },
    "self_evolution.apply_core_source_change": {
        "auth_scope": "self_evolution:write",
        "risk_level": "critical",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    },
    "self_evolution.run_model_finetune": {
        "auth_scope": "self_evolution:write",
        "risk_level": "critical",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    },
    "self_evolution.deploy_architecture_migration": {
        "auth_scope": "self_evolution:write",
        "risk_level": "critical",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    },
    "agent.parallel": {
        "auth_scope": "agent:execute",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array"},
                "max_concurrency": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["tasks"],
        },
        "retry": {"max_attempts": 1, "backoff_ms": 0, "retry_on": []},
    },
    "development.task.start": {
        "auth_scope": "development:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "context": {"type": "object"},
                "auto_execute": {"type": "boolean"},
            },
            "required": ["goal"],
        },
    },
    "development.task.status": {
        "auth_scope": "development:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": [],
        },
    },
    "development.task.resume": {
        "auth_scope": "development:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    "development.task.cancel": {
        "auth_scope": "development:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    "development.task.verify": {
        "auth_scope": "development:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    "development.task.learn": {
        "auth_scope": "development:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    "mcp.server.add": {
        "auth_scope": "mcp:write",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "command": {"type": "string"},
                "args": {"type": "array"},
                "env": {"type": "object"},
            },
            "required": ["name", "command"],
        },
    },
    "mcp.servers": {
        "auth_scope": "mcp:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "mcp.tools": {
        "auth_scope": "mcp:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {
            "type": "object",
            "properties": {"server": {"type": "string"}},
            "required": ["server"],
        },
    },
    "mcp.call": {
        "auth_scope": "mcp:execute",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string"},
                "tool": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["server", "tool"],
        },
    },
    "cron.create": {
        "auth_scope": "cron:write",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "method": {"type": "string"},
                "params": {"type": "object"},
                "interval_seconds": {"type": "integer", "minimum": 1},
                "run_at": {"type": "string"},
                "rrule": {"type": "string"},
            },
            "required": ["name", "method"],
        },
    },
    "cron.list": {
        "auth_scope": "cron:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "cron.run_due": {
        "auth_scope": "cron:execute",
        "risk_level": "medium",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"now": {"type": "string"}},
            "required": [],
        },
    },
    "context.attach": {
        "auth_scope": "context:write",
        "risk_level": "low",
        "idempotent": False,
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer", "minimum": 1}},
            "required": ["path"],
        },
    },
    "context.files": {
        "auth_scope": "context:read",
        "risk_level": "low",
        "idempotent": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "terminal.redirect": {
        "auth_scope": "filesystem:write",
        "risk_level": "high",
        "idempotent": False,
        "requires_approval": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "path": {"type": "string"},
                "mode": {"type": "string"},
            },
            "required": [],
        },
    },
}

DEFAULT_TOOL_POLICY: dict[str, Any] = {
    "auth_scope": "runtime:read",
    "risk_level": "low",
    "idempotent": True,
    "input_schema": {"type": "object", "properties": {}, "required": []},
    "retry": {"max_attempts": 1, "backoff_ms": 0, "retry_on": []},
}


class JSONRPCServer:
    """Small JSON-RPC server over stdio."""

    def __init__(
        self,
        runtime: LocalRuntime | None = None,
        runtime_root: str | Path | None = None,
        config_path: str | Path | None = None,
        writer: Callable[[dict[str, Any]], None] | None = None,
        stream_delay: float = 0.015,
    ) -> None:
        self.config_path = self._resolve_config_path(config_path)
        self.env_loaded = False
        root = Path(runtime_root) if runtime_root is not None else project_root
        self.runtime = runtime or self._build_runtime(root)
        self.writer = writer
        self.stream_delay = stream_delay
        self.running = False
        self.session_id = uuid.uuid4().hex[:8]
        self.session_started_at = time.time()
        self.history: list[dict[str, Any]] = []
        self.pending_clarifications: dict[str, dict[str, Any]] = {}
        self.pending_secrets: dict[str, dict[str, Any]] = {}
        self.pending_sudo: dict[str, dict[str, Any]] = {}
        self.background_tasks: set[asyncio.Task[Any]] = set()
        self.cols = 80
        self.last_approval_ids: set[str] = set()
        self.mcp_config_path = self.runtime.root_path / "mcp_servers.json"
        self.cron_jobs_path = self.runtime.root_path / "cron_jobs.json"
        self.context_files: dict[str, dict[str, Any]] = {}
        self.personality = "concise operator"
        self.autonomous_remote_loop_task: asyncio.Task[Any] | None = None
        self.approval_timeout_task: asyncio.Task[Any] | None = None
        self.autonomous_remote_loop_interval = max(
            1.0,
            float(os.getenv("AUTONOMOUS_REMOTE_LOOP_INTERVAL_SECONDS", "30") or 30),
        )
        self.approval_timeout_interval = max(
            1.0,
            float(os.getenv("APPROVAL_TIMEOUT_CHECK_SECONDS", "1") or 1),
        )

    def _build_runtime(self, root: Path) -> LocalRuntime:
        if self.config_path is None:
            self.config_path = self._default_config_path(root)
        if self.config_path and self.config_path.exists():
            self.env_loaded = self._load_env_file(self.config_path.parent / ".env")
            config = self._read_config_file(self.config_path)
            return LocalRuntime(self._runtime_config_from_mapping(config))
        return LocalRuntime(
            LocalRuntimeConfig(
                root_path=root,
                security_defaults={
                    "network": True,
                    "shell": True,
                    "filesystem": {"read": ["*"], "write": ["*"]},
                    "environment": {"allow": ["*"], "request": ["OPENAI_API_KEY"]},
                },
            )
        )

    @staticmethod
    def _resolve_config_path(config_path: str | Path | None) -> Path | None:
        raw = (
            str(config_path)
            if config_path is not None
            else os.getenv("LOCAL_AGENT_CONFIG_PATH")
            or os.getenv("DUAL_RING_CONFIG_PATH")
            or ""
        )
        if not raw.strip():
            return None
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = project_root / path
        return path.resolve()

    @staticmethod
    def _load_env_file(env_path: Path) -> bool:
        if not env_path.exists():
            return False
        loaded = False
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", maxsplit=1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip().strip("\"'")
            loaded = True
        return loaded

    @staticmethod
    def _read_config_file(config_path: Path) -> dict[str, Any]:
        text = config_path.read_text(encoding="utf-8")
        if config_path.suffix.lower() in {".yaml", ".yml"}:
            payload = yaml.safe_load(text) or {}
        else:
            payload = json.loads(text or "{}")
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _write_config_file(config_path: Path, payload: dict[str, Any]) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if config_path.suffix.lower() in {".yaml", ".yml"}:
            config_path.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        else:
            config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _runtime_config_from_mapping(self, config: dict[str, Any]) -> LocalRuntimeConfig:
        normalized = self._normalize_runtime_config(config)
        return LocalRuntimeConfig(
            root_path=Path(normalized["root_path"]),
            enable_agents=bool(normalized.get("enable_agents", False)),
            managed_paths=normalized.get("managed_paths", {}),
            adapters=normalized.get("adapters", {}),
            security_defaults=normalized.get("security_defaults", {}),
        )

    @staticmethod
    def _normalize_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(config)
        model_config = normalized.get("model") if isinstance(normalized.get("model"), dict) else {}
        providers = normalized.get("providers") if isinstance(normalized.get("providers"), dict) else {}
        provider = str(model_config.get("provider") or normalized.get("provider") or "").strip()
        model = str(model_config.get("name") or normalized.get("model_name") or "").strip()
        if provider:
            preset = dict(MODEL_PROVIDER_PRESETS.get(provider, MODEL_PROVIDER_PRESETS["custom"]))
            provider_config = providers.get(provider) if isinstance(providers.get(provider), dict) else {}
            preset.update(provider_config)
            provider = CUSTOM_MODEL_PROVIDER_SLUG
            adapters = normalized.setdefault("adapters", {})
            remote = adapters.setdefault("remote_llm", {})
            remote.setdefault("enabled", True)
            remote.setdefault("dry_run", bool(preset.get("dry_run", False)))
            remote["api_key_env"] = str(preset.get("api_key_env", "OPENAI_API_KEY"))
            remote["base_url"] = str(preset.get("base_url", "https://api.openai.com/v1"))
            remote["model"] = model or str((preset.get("models") or ["gpt-4o-mini"])[0])
            remote.setdefault("timeout", 30.0)
            remote.setdefault("temperature", 0.2)
            remote.setdefault("max_tokens", None)
            normalized["model"] = {"provider": provider, "name": remote["model"]}
            normalized["providers"] = {}
            normalized.setdefault("providers", {})[provider] = {
                "base_url": remote["base_url"],
                "api_key_env": remote["api_key_env"],
            }
        normalized.setdefault("root_path", str(project_root))
        normalized.setdefault("enable_agents", False)
        normalized.setdefault("managed_paths", {})
        normalized.setdefault("adapters", {})
        normalized.setdefault(
            "security_defaults",
            {
                "network": True,
                "shell": True,
                "filesystem": {"read": ["*"], "write": ["*"]},
                "environment": {"allow": ["*"], "request": ["OPENAI_API_KEY"]},
            },
        )
        return normalized

    async def start(self) -> None:
        """Start the JSON-RPC request loop."""
        logger.info("Starting TUI Gateway")
        self.running = True
        if not self.runtime.running:
            self.runtime.start()
        self._ensure_autonomous_remote_loop()
        self._ensure_approval_timeout_loop()

        await self.send_event(
            "gateway.ready",
            {
                "skin": {
                    "branding": {
                        "agent": "本地智能体",
                        "prompt": ">",
                        "welcome": "本地自主终端",
                        "goodbye": "会话已关闭",
                    },
                    "colors": {
                        "banner_title": "cyan",
                        "accent": "cyan",
                        "border": "gray",
                        "label": "magenta",
                        "ok": "green",
                        "warn": "yellow",
                        "error": "red",
                    },
                    "help_header": "终端界面",
                    "tool_prefix": "工具",
                }
            },
        )
        await self.send_event("session.info", self._session_info())

        try:
            async for line in self.read_stdin():
                if not self.running:
                    break
                await self.handle_request(line)
        except Exception as exc:  # pragma: no cover - defensive loop logging
            logger.error("Gateway loop failed: %s", exc, exc_info=True)
        finally:
            await self._stop_approval_timeout_loop()
            await self._stop_autonomous_remote_loop()
            self.runtime.stop()
            logger.info("Gateway stopped")

    async def read_stdin(self):
        loop = asyncio.get_event_loop()
        while self.running:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            yield line.strip()

    async def handle_request(self, line: str) -> None:
        request_id: Any = None
        try:
            request = json.loads(line)
            method = str(request.get("method", ""))
            params = request.get("params") or {}
            request_id = request.get("id")
            if not hasattr(self, f"handle_{method.replace('.', '_')}"):
                await self.send_error(request_id, -32601, f"Method not found: {method}")
                return
            if method in PUBLIC_DIRECT_METHODS:
                result = await self._dispatch_rpc_method(method, params)
            elif method in TOOL_POLICIES:
                result = await self._execute_agent_tool(
                    method,
                    params if isinstance(params, dict) else {},
                    auth_scopes=request.get("auth_scopes"),
                )
            else:
                await self.send_error(request_id, -32601, f"Method not found: {method}")
                return
            if request_id is not None:
                await self.send_response(request_id, result)
        except json.JSONDecodeError as exc:
            await self.send_event("gateway.protocol_error", {"preview": str(exc)})
        except Exception as exc:
            logger.error("Handler error: %s", exc, exc_info=True)
            await self.send_error(request_id, -32603, str(exc))

    async def send_response(self, request_id: Any, result: Any) -> None:
        await self.write_stdout({"jsonrpc": "2.0", "id": request_id, "result": result})

    async def send_error(self, request_id: Any, code: int, message: str) -> None:
        await self.write_stdout(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        )

    async def send_event(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        params: dict[str, Any] = {
            "type": event_type,
            "session_id": session_id or self.session_id,
        }
        if payload is not None:
            params["payload"] = payload
        await self.write_stdout({"jsonrpc": "2.0", "method": "event", "params": params})

    async def write_stdout(self, data: dict[str, Any]) -> None:
        if self.writer is not None:
            self.writer(data)
            return
        sys.stdout.write(json.dumps(data, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    async def wait_for_background(self) -> None:
        if not self.background_tasks:
            return
        await asyncio.gather(*list(self.background_tasks), return_exceptions=True)

    def _ensure_approval_timeout_loop(self) -> None:
        if self.approval_timeout_task is not None and not self.approval_timeout_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self.approval_timeout_task = loop.create_task(self._approval_timeout_loop())

    async def _stop_approval_timeout_loop(self) -> None:
        task = self.approval_timeout_task
        self.approval_timeout_task = None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _approval_timeout_loop(self) -> None:
        while True:
            auto_approved = await self._auto_approve_expired_requests()
            if auto_approved:
                approvals = [
                    {
                        "request_id": request.request_id,
                        "request_type": request.request_type,
                        "title": request.title,
                        "risk_level": request.risk_level,
                        "status": request.status,
                        "requested_by": request.requested_by,
                    }
                    for request in self.runtime.governance.list_requests()
                ]
                await self.send_event("approval.queue", {"approvals": approvals})
            await asyncio.sleep(self.approval_timeout_interval)

    def _ensure_autonomous_remote_loop(self) -> None:
        if self.autonomous_remote_loop_task is not None and not self.autonomous_remote_loop_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self.autonomous_remote_loop_task = loop.create_task(self._autonomous_remote_loop())

    async def _stop_autonomous_remote_loop(self) -> None:
        task = self.autonomous_remote_loop_task
        self.autonomous_remote_loop_task = None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _autonomous_remote_loop(self) -> None:
        tick = 0
        while self.running:
            tick += 1
            await self._run_autonomous_remote_loop_tick(tick)
            await asyncio.sleep(self.autonomous_remote_loop_interval)

    async def _run_autonomous_remote_loop_tick(self, tick: int) -> dict[str, Any]:
        trigger = "remote_loop"
        task_text = f"远程自主反思第 {tick} 次"
        actions: list[dict[str, Any]] = []
        plan: dict[str, Any] = {"steps": []}
        execution: dict[str, Any] = {"executed": 0, "verified": 0, "errors": 0}

        def record(name: str, result: Any = None, error: Exception | None = None) -> None:
            payload: dict[str, Any] = {"name": name, "status": "error" if error else "completed"}
            if result is not None:
                payload["result"] = result
            if error is not None:
                payload["error"] = str(error)
            actions.append(payload)

        next_actions = self._autonomous_next_actions(trigger, actions)
        try:
            reflection = self.runtime.autonomous_remote_reflection(
                trigger=trigger,
                task_text=task_text,
                actions=actions,
                next_actions=next_actions,
            )
            record(
                "autonomous.remote_reflection",
                {
                    "status": reflection.get("status"),
                    "remote_status": reflection.get("remote_status"),
                    "provider": reflection.get("provider"),
                    "model": reflection.get("model"),
                    "reflection": reflection.get("reflection", ""),
                    "next_actions": reflection.get("next_actions", []),
                    "risk": reflection.get("risk", ""),
                    "tick": tick,
                },
            )
            if reflection.get("next_actions"):
                next_actions = self._merge_autonomous_next_actions(
                    next_actions,
                    reflection.get("next_actions", []),
                )
        except Exception as exc:
            record("autonomous.remote_reflection", error=exc)

        try:
            plan = self._build_autonomous_execution_plan(trigger, task_text, next_actions)
            record("autonomous.plan", plan)
        except Exception as exc:
            record("autonomous.plan", error=exc)
            plan = {"steps": []}

        try:
            execution = await self._execute_autonomous_plan(plan, record)
        except Exception as exc:
            record("autonomous.execute", error=exc)
            execution = {"executed": 0, "verified": 0, "errors": 1}

        goals = self.runtime.update_autonomous_goals(
            goal_text=task_text or trigger,
            trigger=trigger,
            next_actions=next_actions,
        )
        record(
            "autonomous.goals.update",
            {
                "active_goal_id": goals.get("active_goal_id"),
                "total": len(goals.get("goals", [])),
            },
        )

        autonomy_record = {
            "id": f"autonomy_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}",
            "trigger": trigger,
            "autonomy_level": AUTONOMY_LEVEL,
            "created_at": datetime.now(UTC).isoformat(),
            "actions": actions,
            "next_actions": next_actions,
            "plan": plan,
            "execution": execution,
            "session_id": self.session_id,
            "tick": tick,
        }
        self_state = self._build_self_state(
            trigger=trigger,
            task_text=task_text,
            actions=actions,
            next_actions=next_actions,
            autonomy_record_id=autonomy_record["id"],
        )
        autonomy_record["self_state"] = self_state
        try:
            self_state_path = self.runtime.root_path / "experience" / "self_state.json"
            self_state_path.parent.mkdir(parents=True, exist_ok=True)
            self_state_path.write_text(
                json.dumps(self_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            record("self_state.write", {"path": str(self_state_path)})
        except Exception as exc:
            record("self_state.write", error=exc)
        try:
            autonomy_path = self.runtime.root_path / "experience" / "autonomy_loop.jsonl"
            autonomy_path.parent.mkdir(parents=True, exist_ok=True)
            with autonomy_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(autonomy_record, ensure_ascii=False) + "\n")
            record("autonomy.report", {"path": str(autonomy_path), "id": autonomy_record["id"]})
        except Exception as exc:
            record("autonomy.report", error=exc)

        await self.send_event(
            "system.maintenance",
            {
                "trigger": trigger,
                "actions": actions,
                "autonomous": True,
                "autonomy_level": AUTONOMY_LEVEL,
                "next_actions": next_actions,
                "plan": plan,
                "execution": execution,
                "record_id": autonomy_record["id"],
                "self_state": self_state,
                "tick": tick,
            },
        )
        return {"trigger": trigger, "actions": actions, "next_actions": next_actions, "tick": tick}

    async def handle_session_create(self, params: dict[str, Any]) -> dict[str, Any]:
        self.cols = int(params.get("cols", self.cols) or self.cols)
        self.session_id = uuid.uuid4().hex[:8]
        self.session_started_at = time.time()
        self.history.clear()
        await self._run_autonomous_session_maintenance("session_start", "new terminal session")
        self._ensure_autonomous_remote_loop()
        return {"session_id": self.session_id, "info": self._session_info()}

    async def handle_session_list(self, params: dict[str, Any]) -> dict[str, Any]:
        limit = int(params.get("limit", 50) or 50)
        sessions = [
            {
                "id": self.session_id,
                "title": "当前终端会话",
                "preview": self.history[-1]["text"] if self.history else "暂无消息",
                "started_at": self.session_started_at,
                "message_count": len(self.history),
                "source": "tui",
            }
        ]
        return {"sessions": sessions[:limit]}

    async def handle_session_resume(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": params.get("session_id") or self.session_id,
            "messages": self.history,
            "message_count": len(self.history),
            "info": self._session_info(),
        }

    async def handle_session_history(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"messages": self.history, "info": self._session_info()}

    async def handle_session_status(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"output": self._format_status()}

    async def handle_runtime_logs(self, params: dict[str, Any]) -> dict[str, Any]:
        lines = max(1, min(int(params.get("lines", 20) or 20), 200))
        return {"lines": [], "tail": "", "message": f"最近 {lines} 行网关日志由 TUI 进程捕获。"}

    async def handle_runtime_health(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.health_report()

    async def handle_runtime_preflight(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.preflight_report()

    async def handle_runtime_host_probe(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.host_integration_probe()

    async def handle_runtime_messaging_status(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.messaging_gateway_status()

    async def handle_runtime_blueprints(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"blueprints": self.runtime.list_agent_blueprints()}

    async def handle_runtime_skills(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"skills": self.runtime.list_published_skills()}

    async def handle_runtime_algorithms(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "algorithms": self.runtime.list_algorithms(),
            "experiments": self.runtime.list_algorithm_experiment_reports(),
            "reviews": self.runtime.list_algorithm_reviews(),
        }

    async def handle_runtime_audits(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "skill_lifecycle": self.runtime.read_skill_lifecycle_audit(),
            "algorithm_evolution": self.runtime.read_algorithm_evolution_audit(),
        }

    async def handle_runtime_avatar(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"avatar_event": self.runtime.get_latest_avatar_event()}

    async def handle_runtime_terminal_ui(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.terminal_ui_status()

    async def handle_runtime_events(self, params: dict[str, Any]) -> dict[str, Any]:
        limit = max(1, min(int(params.get("limit", 20) or 20), 100))
        events = [
            {
                "event_type": event.event_type,
                "payload": event.payload,
                "source_agent": event.source_agent,
                "timestamp": event.timestamp,
                "correlation_id": event.correlation_id,
            }
            for event in self.runtime.event_bus.list_events()
        ]
        return {"events": events[-limit:]}

    async def handle_runtime_write_preflight(self, params: dict[str, Any]) -> dict[str, Any]:
        report = self.runtime.preflight_report()
        path = self.runtime.write_preflight_report(report=report)
        await self.send_event(
            "tool.complete",
            {
                "tool_id": "runtime_write_preflight",
                "name": "runtime.write_preflight_report",
                "summary": f"Wrote {path}",
            },
        )
        return {"path": str(path), "report": report}

    async def handle_runtime_write_host_probe(self, params: dict[str, Any]) -> dict[str, Any]:
        report = self.runtime.host_integration_probe()
        path = self.runtime.write_host_integration_probe(report=report)
        return {"path": str(path), "report": report}

    async def handle_runtime_final_acceptance(self, params: dict[str, Any]) -> dict[str, Any]:
        cycles = self._bounded_cycles(params.get("stress_cycles", 3), maximum=10)
        report = self.runtime.final_acceptance_report(stress_cycles=cycles)
        path = self.runtime.write_final_acceptance_report(
            stress_cycles=cycles,
            report=report,
        )
        return {"path": str(path), "report": report}

    async def handle_runtime_adapters(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"adapters": self.runtime.adapter_health()}

    async def handle_runtime_status_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.status_snapshot()

    async def handle_runtime_start(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.runtime.running:
            self.runtime.start()
        return {"running": self.runtime.running, "status": "started"}

    async def handle_runtime_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.runtime.running:
            self.runtime.stop()
        return {"running": self.runtime.running, "status": "stopped"}

    async def handle_runtime_platform_message(self, params: dict[str, Any]) -> dict[str, Any]:
        platform = str(params.get("platform", "")).strip()
        payload = params.get("payload") if isinstance(params.get("payload"), dict) else {}
        try:
            result = self.runtime.handle_platform_message(platform, payload)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": "completed", "result": result}

    async def handle_agent_parallel(self, params: dict[str, Any]) -> dict[str, Any]:
        tasks = self._normalize_parallel_tasks(
            params.get("tasks") if isinstance(params.get("tasks"), list) else []
        )
        if not tasks:
            return self._tool_error("VALIDATION_ERROR", "missing parallel tasks", retryable=False)
        max_concurrency = max(1, min(int(params.get("max_concurrency", 4) or 4), 8))
        group_id = f"parallel_{uuid.uuid4().hex[:8]}"
        plan_steps = [
            {
                "id": f"{group_id}_{task['id']}",
                "title": f"Parallel task {index}: {task.get('method') or 'prompt'}",
                "status": "pending",
                "detail": "queued",
                "parallel_group_id": group_id,
            }
            for index, task in enumerate(tasks, start=1)
        ]
        await self.send_event(
            "agent.parallel.start",
            {
                "parallel_group_id": group_id,
                "total": len(tasks),
                "max_concurrency": max_concurrency,
                "tasks": tasks,
            },
        )
        await self.send_event(
            "plan.update",
            {
                "plan_id": group_id,
                "title": "Parallel Agents",
                "status": "running",
                "steps": plan_steps,
            },
        )

        semaphore = asyncio.Semaphore(max_concurrency)
        indexed_results: list[dict[str, Any] | None] = [None] * len(tasks)

        async def run_one(index: int, task: dict[str, Any]) -> None:
            step = plan_steps[index]
            async with semaphore:
                running_step = {**step, "status": "running", "detail": "running concurrently"}
                plan_steps[index] = running_step
                await self.send_event("step.update", running_step)
                if task.get("method"):
                    method = str(task["method"])
                    result = await self._execute_parallel_tool(method, dict(task.get("params") or {}), group_id)
                    record = {
                        "id": task["id"],
                        "method": method,
                        "ok": bool(result.get("ok")),
                        "result": result,
                    }
                    if result.get("ok") is False:
                        record["error"] = result.get("error")
                else:
                    prompt = str(task.get("prompt", ""))
                    response = await asyncio.to_thread(self.runtime.handle_interaction, prompt)
                    record = {
                        "id": task["id"],
                        "prompt": prompt,
                        "ok": True,
                        "result": response,
                    }
                indexed_results[index] = record
                status = "complete" if record["ok"] else "error"
                detail = "completed" if record["ok"] else str((record.get("error") or {}).get("message", "failed"))
                completed_step = {**running_step, "status": status, "detail": detail}
                plan_steps[index] = completed_step
                await self.send_event("step.update", completed_step)

        await asyncio.gather(*(run_one(index, task) for index, task in enumerate(tasks)))
        results = [item for item in indexed_results if item is not None]
        failed = sum(1 for item in results if not item.get("ok"))
        completed = len(results) - failed
        status = "complete" if failed == 0 else "error"
        await self.send_event(
            "plan.update",
            {
                "plan_id": group_id,
                "title": "Parallel Agents",
                "status": status,
                "steps": plan_steps,
            },
        )
        await self.send_event(
            "agent.parallel.complete",
            {
                "parallel_group_id": group_id,
                "total": len(tasks),
                "completed": completed,
                "failed": failed,
            },
        )
        return {
            "ok": failed == 0,
            "parallel_group_id": group_id,
            "total": len(tasks),
            "completed": completed,
            "failed": failed,
            "results": results,
        }

    async def handle_development_task_start(self, params: dict[str, Any]) -> dict[str, Any]:
        task = self.runtime.start_development_task(
            goal=str(params.get("goal", "")).strip(),
            context=params.get("context") if isinstance(params.get("context"), dict) else {},
            auto_execute=bool(params.get("auto_execute", True)),
        )
        await self._send_development_task_update(task)
        return {"ok": True, "task": task}

    async def handle_development_task_status(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = str(params.get("task_id", "")).strip()
        if task_id:
            return {"ok": True, "task": self.runtime.get_development_task(task_id)}
        return {
            "ok": True,
            "tasks": self.runtime.list_development_tasks(int(params.get("limit", 20) or 20)),
        }

    async def handle_development_task_resume(self, params: dict[str, Any]) -> dict[str, Any]:
        task = self.runtime.execute_development_task(str(params.get("task_id", "")).strip())
        await self._send_development_task_update(task)
        return {"ok": True, "task": task}

    async def handle_development_task_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        task = self.runtime.cancel_development_task(
            str(params.get("task_id", "")).strip(),
            reason=str(params.get("reason", "")).strip(),
        )
        await self._send_development_task_update(task)
        return {"ok": True, "task": task}

    async def handle_development_task_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        task = self.runtime.verify_development_task(str(params.get("task_id", "")).strip())
        await self._send_development_task_update(task)
        return {"ok": True, "task": task}

    async def handle_development_task_learn(self, params: dict[str, Any]) -> dict[str, Any]:
        task = self.runtime.learn_from_development_task(str(params.get("task_id", "")).strip())
        await self._send_development_task_update(task)
        return {"ok": True, "task": task}

    async def _send_development_task_update(self, task: dict[str, Any]) -> None:
        await self.send_event(
            "development.task.update",
            {
                "task_id": task.get("task_id"),
                "goal": task.get("goal"),
                "status": task.get("status"),
                "execution": task.get("execution", {}),
                "verification": task.get("verification", {}),
                "task_path": task.get("task_path"),
            },
        )

    async def _execute_parallel_tool(
        self,
        method: str,
        params: dict[str, Any],
        group_id: str,
    ) -> dict[str, Any]:
        policy = self._tool_policy(method)
        validation_error = self._validate_tool_params(params, policy["input_schema"])
        if validation_error:
            return self._tool_error("VALIDATION_ERROR", validation_error, retryable=False)
        if self._tool_requires_approval(method, policy):
            return self._tool_error(
                "APPROVAL_REQUIRED",
                f"{method} requires approval and cannot be auto-run inside parallel batch",
                retryable=False,
            )
        retry = dict(policy.get("retry", DEFAULT_TOOL_POLICY["retry"]))
        attempts = max(1, int(retry.get("max_attempts", 1)))
        tool_id = self._tool_activity_id(method)
        await self._send_tool_start(
            tool_id,
            method,
            context=f"parallel_group_id={group_id}",
            parallel_group_id=group_id,
        )
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                result = await self._dispatch_rpc_method(method, params)
            except Exception as exc:
                last_error = str(exc)
                if attempt < attempts and retry.get("backoff_ms"):
                    await asyncio.sleep(float(retry["backoff_ms"]) / 1000)
                continue
            if isinstance(result, dict) and result.get("status") == "error":
                last_error = str(result.get("error", "backend error"))
                if attempt < attempts and retry.get("backoff_ms"):
                    await asyncio.sleep(float(retry["backoff_ms"]) / 1000)
                continue
            await self._send_tool_complete(tool_id, method, summary="completed")
            return {"ok": True, "attempts": attempt, **result}
        error = last_error or f"{method} failed"
        await self._send_tool_complete(tool_id, method, error=error)
        return self._tool_error("BACKEND_ERROR", error, retryable=True, attempts=attempts)

    async def handle_mcp_server_add(self, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("name", "")).strip()
        command = str(params.get("command", "")).strip()
        if not name or not command:
            return self._tool_error("VALIDATION_ERROR", "name and command are required", retryable=False)
        servers = self._read_mcp_servers()
        server = {
            "name": name,
            "command": command,
            "args": params.get("args") if isinstance(params.get("args"), list) else [],
            "env": params.get("env") if isinstance(params.get("env"), dict) else {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        servers = [item for item in servers if item.get("name") != name]
        servers.append(server)
        self._write_json_file(self.mcp_config_path, {"servers": servers})
        await self.send_event("mcp.server.add", {"server": server})
        return {"ok": True, "server": server}

    async def handle_mcp_servers(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"servers": self._read_mcp_servers()}

    async def handle_mcp_tools(self, params: dict[str, Any]) -> dict[str, Any]:
        server_name = str(params.get("server", "")).strip()
        server = self._find_mcp_server(server_name)
        if not server:
            return self._tool_error("NOT_FOUND", f"MCP server not found: {server_name}", retryable=False)
        result = await self._mcp_request(server, "tools/list", {})
        tools = result.get("tools") if isinstance(result.get("tools"), list) else []
        return {"ok": True, "server": server_name, "tools": tools}

    async def handle_mcp_call(self, params: dict[str, Any]) -> dict[str, Any]:
        server_name = str(params.get("server", "")).strip()
        tool = str(params.get("tool", "")).strip()
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        server = self._find_mcp_server(server_name)
        if not server:
            return self._tool_error("NOT_FOUND", f"MCP server not found: {server_name}", retryable=False)
        if not tool:
            return self._tool_error("VALIDATION_ERROR", "tool is required", retryable=False)
        result = await self._mcp_request(
            server,
            "tools/call",
            {"name": tool, "arguments": arguments},
        )
        await self.send_event("mcp.call", {"server": server_name, "tool": tool, "result": result})
        return {"ok": not bool(result.get("isError")), "server": server_name, "tool": tool, "result": result}

    async def handle_cron_create(self, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("name", "")).strip()
        method = str(params.get("method", "")).strip()
        if not name or not method:
            return self._tool_error("VALIDATION_ERROR", "name and method are required", retryable=False)
        if method in {"cron.create", "cron.run_due"}:
            return self._tool_error("VALIDATION_ERROR", f"cannot schedule {method}", retryable=False)
        policy = self._tool_policy(method)
        if self._tool_requires_approval(method, policy):
            return self._tool_error(
                "APPROVAL_REQUIRED",
                f"cannot schedule high-risk method: {method}",
                retryable=False,
            )
        jobs = self._read_cron_jobs()
        job = {
            "id": f"cron_{uuid.uuid4().hex[:8]}",
            "name": name,
            "method": method,
            "params": params.get("params") if isinstance(params.get("params"), dict) else {},
            "interval_seconds": int(params.get("interval_seconds", 0) or 0),
            "rrule": str(params.get("rrule", "") or ""),
            "next_run_at": self._normalize_run_at(params.get("run_at")),
            "run_count": 0,
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
            "last_result": None,
        }
        if not job["next_run_at"]:
            job["next_run_at"] = (
                datetime.now(UTC) + timedelta(seconds=max(1, job["interval_seconds"] or 86400))
            ).isoformat()
        jobs.append(job)
        self._write_cron_jobs(jobs)
        await self.send_event("cron.create", {"job": job})
        return {"ok": True, "job": job}

    async def handle_cron_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"jobs": self._read_cron_jobs()}

    async def handle_cron_run_due(self, params: dict[str, Any]) -> dict[str, Any]:
        now = self._parse_datetime(params.get("now")) or datetime.now(UTC)
        jobs = self._read_cron_jobs()
        results: list[dict[str, Any]] = []
        for job in jobs:
            if job.get("status") != "active":
                continue
            next_run = self._parse_datetime(job.get("next_run_at"))
            if next_run and next_run > now:
                continue
            method = str(job.get("method", ""))
            tool_id = self._tool_activity_id(method)
            await self._send_tool_start(tool_id, method, context=f"cron job {job.get('id')}")
            policy = self._tool_policy(method)
            validation_error = self._validate_tool_params(
                job.get("params") if isinstance(job.get("params"), dict) else {},
                policy["input_schema"],
            )
            if method not in TOOL_POLICIES:
                record = {
                    "job_id": job["id"],
                    "method": method,
                    "ok": False,
                    "error": {"code": "METHOD_NOT_FOUND", "message": f"Method not found: {method}", "retryable": False},
                }
                job["status"] = "blocked"
                await self._send_tool_complete(tool_id, method, error=record["error"]["message"])
            elif validation_error:
                record = {
                    "job_id": job["id"],
                    "method": method,
                    "ok": False,
                    "error": {"code": "VALIDATION_ERROR", "message": validation_error, "retryable": False},
                }
                job["status"] = "blocked"
                await self._send_tool_complete(tool_id, method, error=validation_error)
            elif self._tool_requires_approval(method, policy):
                record = {
                    "job_id": job["id"],
                    "method": method,
                    "ok": False,
                    "error": {
                        "code": "APPROVAL_REQUIRED",
                        "message": f"cannot run high-risk scheduled method: {method}",
                        "retryable": False,
                    },
                }
                job["status"] = "blocked"
                await self._send_tool_complete(tool_id, method, error=record["error"]["message"])
            else:
                try:
                    result = await self._dispatch_rpc_method(
                        method,
                        job.get("params") if isinstance(job.get("params"), dict) else {},
                    )
                    record = {"job_id": job["id"], "method": method, "ok": True, "result": result}
                    await self._send_tool_complete(tool_id, method, summary="scheduled job completed")
                except Exception as exc:
                    record = {
                        "job_id": job["id"],
                        "method": method,
                        "ok": False,
                        "error": {"code": "BACKEND_ERROR", "message": str(exc), "retryable": True},
                    }
                    await self._send_tool_complete(tool_id, method, error=str(exc))
            job["run_count"] = int(job.get("run_count", 0) or 0) + 1
            job["last_run_at"] = now.isoformat()
            job["last_result"] = record
            interval = int(job.get("interval_seconds", 0) or 0)
            if job.get("status") == "blocked":
                pass
            elif interval > 0:
                job["next_run_at"] = (now + timedelta(seconds=interval)).isoformat()
            else:
                job["status"] = "completed"
            results.append(record)
        self._write_cron_jobs(jobs)
        await self.send_event("cron.run_due", {"executed": len(results), "results": results})
        return {"ok": True, "executed": len(results), "results": results, "jobs": jobs}

    async def handle_context_attach(self, params: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_context_path(str(params.get("path", "")))
        max_bytes = max(1, min(int(params.get("max_bytes", 65536) or 65536), 262144))
        if not path.exists() or not path.is_file():
            return self._tool_error("NOT_FOUND", f"context file not found: {path}", retryable=False)
        data = path.read_bytes()[:max_bytes]
        text = data.decode("utf-8", errors="replace")
        item = {
            "path": str(path),
            "bytes": len(data),
            "truncated": path.stat().st_size > len(data),
            "text": text,
            "attached_at": datetime.now(UTC).isoformat(),
        }
        self.context_files[str(path)] = item
        await self.send_event(
            "context.files",
            {"files": [self._public_context_file(file) for file in self.context_files.values()]},
        )
        return {"ok": True, "file": self._public_context_file(item)}

    async def handle_context_files(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"files": [self._public_context_file(item) for item in self.context_files.values()]}

    async def handle_experience_record(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.record_experience(
            text=str(params.get("text", "")),
            source=str(params.get("source", "session")),
            tags=params.get("tags") if isinstance(params.get("tags"), list) else None,
            metadata=params.get("metadata") if isinstance(params.get("metadata"), dict) else None,
        )

    async def handle_experience_search(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.search_experience(
            query=str(params.get("query", "")),
            limit=int(params.get("limit", 10) or 10),
        )

    async def handle_conversation_record(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.record_conversation_turn(
            session_id=str(params.get("session_id", self.session_id)),
            role=str(params.get("role", "user")),
            text=str(params.get("text", "")),
            user_id=str(params.get("user_id", "default")),
            metadata=params.get("metadata") if isinstance(params.get("metadata"), dict) else None,
        )

    async def handle_conversation_search(self, params: dict[str, Any]) -> dict[str, Any]:
        result = self.runtime.search_conversations(
            query=str(params.get("query", "")),
            limit=int(params.get("limit", 10) or 10),
            summarize=bool(params.get("summarize", True)),
            user_id=str(params.get("user_id")) if params.get("user_id") else None,
        )
        if not result["matches"]:
            fallback = self.runtime.search_experience(
                query=str(params.get("query", "")),
                limit=int(params.get("limit", 10) or 10),
            )
            result = {
                **result,
                "matches": fallback["matches"],
                "total": fallback["total"],
                "summary": result["summary"]
                or self.runtime._summarize_conversation_matches(
                    str(params.get("query", "")),
                    fallback["matches"],
                ),
            }
        return result

    async def handle_memory_periodic_tick(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.periodic_memory_tick(
            task=str(params.get("task", "")),
            cadence=str(params.get("cadence", "daily")),
        )

    async def handle_self_model_read(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.read_self_model()

    async def handle_self_model_update(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.update_self_model(
            observation=str(params.get("observation", "")),
            capability=params.get("capability"),
            preference=params.get("preference"),
        )

    async def handle_user_model_update(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.update_user_model_dialectic(
            user_id=str(params.get("user_id", "default")),
            observation=str(params.get("observation", "")),
        )

    async def handle_user_model_query(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.query_user_model(
            user_id=str(params.get("user_id", "default")),
            question=str(params.get("question", "")),
        )

    async def handle_skill_draft_from_experience(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.draft_skill_from_experience(
            query=str(params.get("query", "")),
            skill_name=params.get("skill_name"),
        )

    async def handle_skill_autonomous_from_task(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.autonomous_skill_from_task(
            task_text=str(params.get("task_text", "")),
            skill_name=params.get("skill_name"),
        )

    async def handle_skill_improve_from_usage(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.improve_skill_from_usage(
            skill_name=str(params.get("skill_name", "")),
            feedback=str(params.get("feedback", "")),
        )

    async def handle_skill_merge_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.merge_skill_preview(
            list(params.get("skill_paths", [])),
            merged_skill_name=params.get("merged_skill_name"),
            strategy=str(params.get("strategy", "dedupe_union")),
        )

    async def handle_skill_merge(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.merge_skills(
            list(params.get("skill_paths", [])),
            merged_skill_name=params.get("merged_skill_name"),
            strategy=str(params.get("strategy", "dedupe_union")),
        )

    async def handle_governance_requests(self, params: dict[str, Any]) -> dict[str, Any]:
        auto_approved = await self._auto_approve_expired_requests()
        status = params.get("status")
        requests = self.runtime.governance.list_requests(str(status)) if status else self.runtime.governance.list_requests()
        return {
            "requests": [asdict(request) for request in requests],
            "auto_approved": auto_approved,
        }

    async def handle_governance_decide(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            request = self.runtime.governance.decide(
                str(params.get("request_id", "")),
                str(params.get("decision", "rejected")),
                str(params.get("decided_by", "tui")),
                str(params.get("comments", "")),
            )
        except ValueError as exc:
            return self._tool_error("APPROVAL_ALREADY_DECIDED", str(exc), retryable=False)
        await self._send_approval_queue()
        return {"request": asdict(request)}

    async def handle_approval_respond_rpc(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self.handle_approval_respond(params)

    async def handle_skill_request_publish(self, params: dict[str, Any]) -> dict[str, Any]:
        request = self.runtime.create_skill_publication_request(
            params["proposal_dir"],
            requested_by=str(params.get("requested_by", "tui")),
            title=str(params.get("title", "Publish skill")),
            risk_level=str(params.get("risk_level", "medium")),
        )
        await self._send_approval_queue()
        return {"request": asdict(request)}

    async def handle_skill_publish_approved(self, params: dict[str, Any]) -> dict[str, Any]:
        published, run_result = self.runtime.publish_skill_from_approval(
            str(params.get("request_id", "")),
            approved_by=str(params.get("approved_by", "tui")),
            parameters=params.get("parameters") if isinstance(params.get("parameters"), dict) else None,
        )
        return {
            "published": {
                "skill_name": published.skill_name,
                "target_dir": str(published.target_dir),
            },
            "run_result": asdict(run_result),
        }

    async def handle_algorithm_request_research(self, params: dict[str, Any]) -> dict[str, Any]:
        request = self.runtime.create_algorithm_research_request(
            params["proposal_path"],
            requested_by=str(params.get("requested_by", "tui")),
            title=params.get("title"),
            risk_level=str(params.get("risk_level", "high")),
        )
        await self._send_approval_queue()
        return {"request": asdict(request)}

    async def handle_algorithm_run_experiment(self, params: dict[str, Any]) -> dict[str, Any]:
        report = self.runtime.run_algorithm_experiment_from_approval(
            str(params.get("request_id", "")),
            params["dataset_path"],
            dict(params.get("thresholds", {})),
        )
        return {"report": asdict(report)}

    async def handle_algorithm_request_promotion(self, params: dict[str, Any]) -> dict[str, Any]:
        request = self.runtime.create_algorithm_promotion_request(
            params["report_path"],
            params["blueprint_path"],
            requested_by=str(params.get("requested_by", "tui")),
            title=params.get("title"),
            risk_level=str(params.get("risk_level", "critical")),
        )
        await self._send_approval_queue()
        return {"request": asdict(request)}

    async def handle_algorithm_apply_promotion(self, params: dict[str, Any]) -> dict[str, Any]:
        blueprint = self.runtime.apply_algorithm_promotion_from_approval(
            str(params.get("request_id", "")),
            approved_by=str(params.get("approved_by", "tui")),
        )
        return {"blueprint": asdict(blueprint)}

    async def handle_organization_request_change(self, params: dict[str, Any]) -> dict[str, Any]:
        request = self.runtime.create_organization_change_request(
            params["proposal_path"],
            requested_by=str(params.get("requested_by", "tui")),
            title=params.get("title"),
            risk_level=str(params.get("risk_level", "constitutional")),
        )
        await self._send_approval_queue()
        return {"request": asdict(request)}

    async def handle_organization_apply_change(self, params: dict[str, Any]) -> dict[str, Any]:
        blueprint = self.runtime.apply_organization_change_from_approval(
            str(params.get("request_id", "")),
            approved_by=str(params.get("approved_by", "tui")),
        )
        return {"blueprint": asdict(blueprint)}

    async def handle_organization_rollback(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.rollback_organization_change(
            str(params.get("role_name", "")),
            requested_by=str(params.get("requested_by", "tui")),
            reason=str(params.get("reason", "Requested from terminal gateway")),
        )

    async def handle_self_evolution_apply_core_source_change(self, params: dict[str, Any]) -> dict[str, Any]:
        result = self.runtime.apply_core_source_change_from_approval(
            str(params.get("request_id", "")),
            approved_by=str(params.get("approved_by", "tui")),
        )
        await self._send_gateway_reload_required(result, reason="core_source_change_applied")
        return result

    async def handle_self_evolution_run_model_finetune(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.run_model_finetune_from_approval(
            str(params.get("request_id", "")),
            approved_by=str(params.get("approved_by", "tui")),
        )

    async def handle_self_evolution_deploy_architecture_migration(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.deploy_architecture_migration_from_approval(
            str(params.get("request_id", "")),
            approved_by=str(params.get("approved_by", "tui")),
        )

    async def _send_gateway_reload_required(
        self,
        result: dict[str, Any],
        reason: str,
    ) -> None:
        if not result.get("requires_gateway_reload"):
            return
        await self.send_event(
            "gateway.reload_required",
            {
                "reason": reason,
                "request_id": result.get("request_id", ""),
                "changed_files": result.get("changed_files", []),
                "reload_mode": "restart_gateway_subprocess",
            },
        )

    async def handle_runtime_operational_smoke(self, params: dict[str, Any]) -> dict[str, Any]:
        cycles = self._bounded_cycles(params.get("cycles", 1), maximum=5)
        await self.send_event(
            "tool.start",
            {
                "tool_id": "runtime_operational_smoke",
                "name": "runtime.run_operational_smoke",
                "context": f"{cycles} cycle(s)",
            },
        )
        report = self.runtime.run_operational_smoke(cycles=cycles)
        path = self.runtime.write_operational_smoke_report(cycles=cycles, report=report)
        await self.send_event(
            "tool.complete",
            {
                "tool_id": "runtime_operational_smoke",
                "name": "runtime.run_operational_smoke",
                "summary": f"{report['summary']['status']} | wrote {path}",
            },
        )
        return {**report, "path": str(path)}

    async def handle_runtime_interaction_stress(self, params: dict[str, Any]) -> dict[str, Any]:
        cycles = self._bounded_cycles(params.get("cycles", 1), maximum=5)
        await self.send_event(
            "tool.start",
            {
                "tool_id": "runtime_interaction_stress",
                "name": "runtime.run_interaction_stress",
                "context": f"{cycles} cycle(s)",
            },
        )
        report = self.runtime.run_interaction_stress(cycles=cycles)
        await self.send_event(
            "tool.complete",
            {
                "tool_id": "runtime_interaction_stress",
                "name": "runtime.run_interaction_stress",
                "summary": f"{report['status']} | {cycles} cycle(s)",
            },
        )
        return report

    async def handle_session_usage(self, params: dict[str, Any]) -> dict[str, Any]:
        usage = self._usage()
        return {**usage, "model": self._model_name(), "cost_status": "estimated"}

    async def handle_session_interrupt(self, params: dict[str, Any]) -> dict[str, Any]:
        await self.send_event("status.update", {"kind": "interrupt", "text": "Interrupted"})
        return {"ok": True}

    async def handle_session_undo(self, params: dict[str, Any]) -> dict[str, Any]:
        removed = 0
        if self.history:
            self.history.pop()
            removed += 1
        return {"removed": removed}

    async def handle_session_close(self, params: dict[str, Any]) -> dict[str, Any]:
        self.running = False
        await self._stop_autonomous_remote_loop()
        return {"ok": True}

    async def handle_session_compress(self, params: dict[str, Any]) -> dict[str, Any]:
        before = len(self.history)
        before_usage = self._usage()
        if before > 20:
            self.history = self.history[-20:]
        after_usage = self._usage()
        result = {
            "before_messages": before,
            "after_messages": len(self.history),
            "removed": before - len(self.history),
            "summary": {
                "headline": "Kept the newest 20 terminal messages.",
                "noop": before <= 20,
                "token_line": f"{after_usage['total']} estimated tokens",
            },
            "messages": self.history,
            "usage": after_usage,
            "info": self._session_info(),
        }
        await self._send_context_compaction(
            trigger=str(params.get("trigger", "manual")),
            before_usage=before_usage,
            after_usage=after_usage,
            removed_messages=result["removed"],
            summary=result["summary"],
        )
        await self.send_event("session.info", self._session_info(after_usage))
        return result

    async def handle_session_save(self, params: dict[str, Any]) -> dict[str, Any]:
        target = (
            self.runtime.root_path
            / "sessions"
            / f"{str(params.get('session_id') or self.session_id)}.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "session_id": self.session_id,
                    "personality": self.personality,
                    "messages": self.history,
                    "saved_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"file": str(target)}

    async def handle_prompt_submit(self, params: dict[str, Any]) -> dict[str, Any]:
        text, redirect = self._split_terminal_redirect(str(params.get("text", "")).strip())
        if not text:
            return {"status": "empty"}

        self.history.append({"role": "user", "text": text})
        text = await self._attach_context_refs(text)
        task = asyncio.create_task(self._run_prompt_submit(text, redirect))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return {"status": "streaming"}

    async def _run_prompt_submit(
        self,
        text: str,
        redirect: dict[str, Any] | None = None,
    ) -> None:
        await self._maybe_auto_compact_context()
        risk = self._assess_runtime_risk(text)
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        steps = [
            {
                "id": "runtime_snapshot",
                "title": "读取运行状态",
                "status": "running",
                "detail": "收集服务、模型与审批队列。",
            },
            {
                "id": "interaction_pipeline",
                "title": "运行交互管线",
                "status": "pending",
                "detail": "将输入发送到本地运行时。",
            },
            {
                "id": "risk_review",
                "title": "检查风险与审批",
                "status": "pending",
                "detail": "识别操作风险并处理审批门禁。",
            },
            {
                "id": "stream_response",
                "title": "流式输出回复",
                "status": "pending",
                "detail": "展示回复、工具活动与用量。",
            },
        ]
        await self.send_event("session.info", self._session_info())
        await self.send_event("message.start")
        await self.send_event("thinking.delta", {"text": "Reading runtime state"})
        await self.send_event(
            "reasoning.delta",
            {"text": self._reasoning_summary(text, risk)},
        )
        await self.send_event(
            "plan.update",
            {
                "plan_id": plan_id,
                "title": "运行任务",
                "status": "running",
                "steps": steps,
            },
        )
        await self.send_event("step.update", steps[0])
        await self._send_approval_queue()
        await self.send_event("runtime.risk", risk)
        await self.send_event(
            "tool.start",
            {
                "tool_id": "runtime_interaction",
                "name": "runtime.handle_interaction",
                "context": "Send prompt through the local interaction pipeline",
            },
        )

        try:
            steps[0] = {**steps[0], "status": "complete"}
            steps[1] = {**steps[1], "status": "running"}
            await self.send_event("step.update", steps[0])
            await self.send_event("step.update", steps[1])
            result = self.runtime.handle_interaction(text)
        except Exception as exc:
            steps[1] = {**steps[1], "status": "error", "detail": str(exc)}
            await self.send_event("step.update", steps[1])
            await self.send_event(
                "tool.complete",
                {
                    "tool_id": "runtime_interaction",
                    "name": "runtime.handle_interaction",
                    "error": str(exc),
                },
            )
            await self.send_event("error", {"message": str(exc)})
            return

        response_text = str(result.get("response_text") or "")
        steps[1] = {**steps[1], "status": "complete"}
        steps[2] = {
            **steps[2],
            "status": "complete",
            "detail": f"{self._zh_risk_level(risk['level'])}风险 | {risk['approval_policy']}",
        }
        steps[3] = {**steps[3], "status": "running"}
        await self.send_event("step.update", steps[1])
        await self.send_event("step.update", steps[2])
        await self.send_event("step.update", steps[3])
        await self._send_approval_queue()
        await self.send_event(
            "tool.complete",
            {
                "tool_id": "runtime_interaction",
                "name": "runtime.handle_interaction",
                "summary": "Runtime interaction completed",
            },
        )

        for chunk in self._chunks(response_text, 72):
            await self.send_event("message.delta", {"text": chunk})
            if self.stream_delay:
                await asyncio.sleep(self.stream_delay)

        usage = self._estimate_usage(text, response_text)
        self.history.append({"role": "assistant", "text": response_text})
        self._learn_from_completed_prompt(text, response_text)
        if len(self.history) > 20:
            await self.handle_session_compress({"trigger": "auto"})
        await self._run_autonomous_session_maintenance("prompt_complete", text)
        redirect_result = None
        if redirect:
            redirect_result = await self._apply_terminal_redirect_with_policy(response_text, redirect)
        steps[3] = {**steps[3], "status": "complete"}
        await self.send_event("step.update", steps[3])
        await self.send_event(
            "plan.update",
            {
                "plan_id": plan_id,
                "title": "运行任务",
                "status": "complete",
                "steps": steps,
            },
        )
        await self.send_event(
            "message.complete",
            {
                "text": response_text,
                "usage": usage,
                "status": "completed",
                "reasoning": result.get("response", {}).get("status", "local"),
                "redirect": redirect_result,
            },
        )

    def _learn_from_completed_prompt(self, prompt: str, response_text: str) -> None:
        experience_text = (
            f"Conversation prompt: {prompt}\n"
            f"Assistant response: {response_text}"
        ).strip()
        self.runtime.record_experience(
            text=experience_text,
            source="conversation",
            tags=["conversation", "auto"],
            metadata={"session_id": self.session_id},
        )
        self.runtime.record_conversation_turn(
            session_id=self.session_id,
            role="user",
            text=prompt,
            user_id="default",
            metadata={"source": "prompt.submit"},
        )
        self.runtime.record_conversation_turn(
            session_id=self.session_id,
            role="assistant",
            text=response_text,
            user_id="default",
            metadata={"source": "prompt.submit"},
        )
        self.runtime.update_self_model(
            observation=f"Completed chat prompt and stored conversation experience: {prompt}",
            capability="conversation_learning",
            preference=None,
        )
        self.runtime.update_user_model_dialectic(
            user_id="default",
            observation=f"User prompt: {prompt}",
        )

    async def _send_approval_queue(self) -> None:
        self._ensure_approval_timeout_loop()
        await self._auto_approve_expired_requests()
        approvals = [
            {
                "request_id": request.request_id,
                "request_type": request.request_type,
                "title": request.title,
                "risk_level": request.risk_level,
                "status": request.status,
                "requested_by": request.requested_by,
            }
            for request in self.runtime.governance.list_requests()
        ]
        await self.send_event("approval.queue", {"approvals": approvals})
        for approval in approvals:
            if approval["status"] != "pending":
                continue
            if approval["request_id"] in self.last_approval_ids:
                continue
            self.last_approval_ids.add(approval["request_id"])
            await self.send_event(
                "approval.request",
                {
                    "request_id": approval["request_id"],
                    "command": approval["title"],
                    "description": (
                        f"{approval['request_type']} | risk={approval['risk_level']} | "
                        f"requested_by={approval['requested_by']}"
                    ),
                },
            )

    async def _auto_approve_expired_requests(self) -> list[dict[str, Any]]:
        auto_approved: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        for request in self.runtime.governance.list_requests("pending"):
            try:
                created_at = datetime.fromisoformat(str(request.created_at))
            except ValueError:
                continue
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            if now - created_at < timedelta(seconds=APPROVAL_TIMEOUT_SECONDS):
                continue
            try:
                approved = self.runtime.governance.decide(
                    request.request_id,
                    "approved",
                    "auto_approve_timeout",
                    f"{APPROVAL_TIMEOUT_SECONDS}s timeout auto-approved",
                )
            except ValueError:
                continue
            executed = None
            if approved.request_type == "agent_tool":
                executed = await self._execute_approved_agent_tool(approved.payload)
            else:
                executed = await self._execute_approved_self_evolution_request(approved)
            if executed is not None:
                self._mark_approval_execution(approved.request_id, executed)
            item = {
                "request": asdict(approved),
                "request_id": approved.request_id,
                "executed": executed,
            }
            auto_approved.append(item)
            await self.send_event(
                "status.update",
                {
                    "kind": "approval",
                    "text": f"{approved.request_id}: approved by 30s timeout",
                },
            )
        return auto_approved

    async def handle_prompt_background(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = uuid.uuid4().hex[:8]
        text = str(params.get("text", "")).strip()
        await self.send_event(
            "background.complete",
            {"task_id": task_id, "text": f"Background prompt queued: {text}"},
        )
        return {"task_id": task_id}

    async def handle_session_steer(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", "")).strip()
        return {"status": "queued" if text else "rejected", "text": text}

    async def _run_autonomous_session_maintenance(self, trigger: str, task_text: str) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []

        def record(name: str, result: Any = None, error: Exception | None = None) -> None:
            payload: dict[str, Any] = {"name": name, "status": "error" if error else "completed"}
            if result is not None:
                payload["result"] = result
            if error is not None:
                payload["error"] = str(error)
            actions.append(payload)

        if trigger == "session_start":
            try:
                record("autonomous.startup_orchestrator", self._startup_orchestration_plan())
            except Exception as exc:
                record("autonomous.startup_orchestrator", error=exc)

        checks: list[tuple[str, Callable[[], Any]]] = [
            ("runtime.status_snapshot", self.runtime.status_snapshot),
            ("runtime.health", self.runtime.health_report),
            ("runtime.preflight", self.runtime.preflight_report),
            ("runtime.adapters", self.runtime.adapter_health),
        ]
        for name, call in checks:
            try:
                record(name, call())
            except Exception as exc:
                record(name, error=exc)

        try:
            await self._send_approval_queue()
            record("governance.approval_sync", {"status": "sent"})
        except Exception as exc:
            record("governance.approval_sync", error=exc)

        try:
            tick = self.runtime.periodic_memory_tick(task=task_text or trigger, cadence=trigger)
            record("memory.periodic_tick", {"id": tick.get("id"), "status": tick.get("status")})
        except Exception as exc:
            record("memory.periodic_tick", error=exc)

        if trigger == "session_start":
            try:
                cron_result = await self.handle_cron_run_due({"now": datetime.now(UTC).isoformat()})
                record(
                    "cron.run_due",
                    {
                        "executed": cron_result.get("executed", 0),
                        "jobs": [
                            {
                                "id": item.get("job_id"),
                                "method": item.get("method"),
                                "ok": item.get("ok"),
                            }
                            for item in cron_result.get("results", [])
                            if isinstance(item, dict)
                        ],
                    },
                )
            except Exception as exc:
                record("cron.run_due", error=exc)

            try:
                before_usage = self._usage()
                await self._maybe_auto_compact_context()
                after_usage = self._usage()
                record(
                    "context.compaction.check",
                    {
                        "before_tokens": before_usage["total"],
                        "after_tokens": after_usage["total"],
                        "context_percent": after_usage["context_percent"],
                        "history_messages": len(self.history),
                    },
                )
            except Exception as exc:
                record("context.compaction.check", error=exc)

            try:
                record("self_evolution.governance_ready", self._self_evolution_governance_status())
            except Exception as exc:
                record("self_evolution.governance_ready", error=exc)

            try:
                record("self_evolution.startup_policy", self._self_evolution_startup_policy())
            except Exception as exc:
                record("self_evolution.startup_policy", error=exc)

        if trigger == "prompt_complete" and self._should_create_autonomous_skill(task_text):
            try:
                skill = self.runtime.autonomous_skill_from_task(
                    task_text=task_text,
                    skill_name=self._autonomous_skill_name(task_text),
                )
                record(
                    "skill.autonomous_from_task",
                    {
                        "skill_name": skill.get("skill_name"),
                        "proposal_dir": skill.get("proposal_dir"),
                    },
                )
            except Exception as exc:
                record("skill.autonomous_from_task", error=exc)

        for name, handler in (
            ("self_evolution.core_source_change", self._prepare_core_source_change),
            ("self_evolution.model_finetune", self._prepare_model_finetune),
            ("self_evolution.architecture_migration_deploy", self._prepare_architecture_migration_deploy),
        ):
            try:
                prepared = handler(task_text)
                if prepared:
                    record(name, prepared)
            except Exception as exc:
                record(name, error=exc)

        try:
            saved = await self.handle_session_save({"session_id": self.session_id})
            record("session.save", saved)
        except Exception as exc:
            record("session.save", error=exc)

        next_actions = self._autonomous_next_actions(trigger, actions)
        try:
            reflection = self.runtime.autonomous_remote_reflection(
                trigger=trigger,
                task_text=task_text or trigger,
                actions=actions,
                next_actions=next_actions,
            )
            record(
                "autonomous.remote_reflection",
                {
                    "status": reflection.get("status"),
                    "remote_status": reflection.get("remote_status"),
                    "provider": reflection.get("provider"),
                    "model": reflection.get("model"),
                    "reflection": reflection.get("reflection", ""),
                    "next_actions": reflection.get("next_actions", []),
                    "risk": reflection.get("risk", ""),
                },
            )
            if reflection.get("next_actions"):
                next_actions = self._merge_autonomous_next_actions(
                    next_actions,
                    reflection.get("next_actions", []),
                )
        except Exception as exc:
            record("autonomous.remote_reflection", error=exc)

        try:
            model = self.runtime.update_self_model(
                observation=(
                    f"Autonomous maintenance {trigger}: "
                    f"{len([item for item in actions if item['status'] == 'completed'])} completed, "
                    f"{len([item for item in actions if item['status'] == 'error'])} errors."
                ),
                capability="autonomous_self_operation",
                preference="self_run_system_maintenance",
            )
            record(
                "self_model.update",
                {
                    "version": model.get("version"),
                    "capabilities": model.get("capabilities", []),
                },
            )
        except Exception as exc:
            record("self_model.update", error=exc)

        goals = self.runtime.update_autonomous_goals(
            goal_text=task_text or trigger,
            trigger=trigger,
            next_actions=next_actions,
        )
        record(
            "autonomous.goals.update",
            {
                "active_goal_id": goals.get("active_goal_id"),
                "total": len(goals.get("goals", [])),
            },
        )

        autonomy_record = {
            "id": f"autonomy_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}",
            "trigger": trigger,
            "autonomy_level": AUTONOMY_LEVEL,
            "created_at": datetime.now(UTC).isoformat(),
            "actions": actions,
            "next_actions": next_actions,
            "session_id": self.session_id,
        }
        self_state = self._build_self_state(
            trigger=trigger,
            task_text=task_text,
            actions=actions,
            next_actions=next_actions,
            autonomy_record_id=autonomy_record["id"],
        )
        autonomy_record["self_state"] = self_state
        try:
            self_state_path = self.runtime.root_path / "experience" / "self_state.json"
            self_state_path.parent.mkdir(parents=True, exist_ok=True)
            self_state_path.write_text(
                json.dumps(self_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            record("self_state.write", {"path": str(self_state_path)})
        except Exception as exc:
            record("self_state.write", error=exc)
        try:
            autonomy_path = self.runtime.root_path / "experience" / "autonomy_loop.jsonl"
            autonomy_path.parent.mkdir(parents=True, exist_ok=True)
            with autonomy_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(autonomy_record, ensure_ascii=False) + "\n")
            record("autonomy.report", {"path": str(autonomy_path), "id": autonomy_record["id"]})
        except Exception as exc:
            record("autonomy.report", error=exc)

        await self.send_event(
            "system.maintenance",
            {
                "trigger": trigger,
                "actions": actions,
                "autonomous": True,
                "autonomy_level": AUTONOMY_LEVEL,
                "next_actions": next_actions,
                "record_id": autonomy_record["id"],
                "self_state": self_state,
            },
        )
        return {"trigger": trigger, "actions": actions, "next_actions": next_actions}

    def _build_self_state(
        self,
        trigger: str,
        task_text: str,
        actions: list[dict[str, Any]],
        next_actions: list[str],
        autonomy_record_id: str,
    ) -> dict[str, Any]:
        completed = [item["name"] for item in actions if item.get("status") == "completed"]
        failed = [
            {"name": item["name"], "error": item.get("error", "")}
            for item in actions
            if item.get("status") == "error"
        ]
        goals = self.runtime.read_autonomous_goals()
        goal_items = list(goals.get("goals", [])) if isinstance(goals.get("goals"), list) else []
        active_goal = next(
            (
                goal
                for goal in goal_items
                if goal.get("id") == goals.get("active_goal_id")
            ),
            goal_items[0] if goal_items else {},
        )
        return {
            "identity": "local_autonomous_agent",
            "autonomy_level": AUTONOMY_LEVEL,
            "active_goal_id": active_goal.get("id", ""),
            "active_goal": active_goal.get("title") or task_text or trigger,
            "session_id": self.session_id,
            "updated_at": datetime.now(UTC).isoformat(),
            "principles": [
                "self_run_system_maintenance",
                "natural_language_for_user_goals",
                "risk_review_before_high_impact_actions",
                "learn_from_completed_work",
            ],
            "boundaries": [
                "surface approval when risk is high",
                "keep user-facing controls minimal",
                "preserve runtime auditability",
            ],
            "capabilities": [
                "autonomous_self_operation",
                "background_memory_planning",
                "self_model_update",
                "skill_creation_from_complex_tasks",
                "context_compaction",
                *self._remote_autonomy_capabilities(actions),
                *self._self_evolution_capabilities(actions),
                *self._startup_autonomy_capabilities(actions),
            ],
            "last_maintenance": {
                "id": autonomy_record_id,
                "trigger": trigger,
                "completed": completed,
                "failed": failed,
            },
            "goal_pool": {
                "total": len(goal_items),
                "active": active_goal,
            },
            "next_actions": next_actions,
        }

    @staticmethod
    def _self_evolution_capabilities(actions: list[dict[str, Any]]) -> list[str]:
        action_names = {item.get("name") for item in actions if item.get("status") == "completed"}
        capabilities: list[str] = []
        if "self_evolution.core_source_change" in action_names:
            capabilities.append("guarded_core_source_modification")
        if "self_evolution.model_finetune" in action_names:
            capabilities.append("autonomous_model_finetuning")
        if "self_evolution.architecture_migration_deploy" in action_names:
            capabilities.append("governed_architecture_migration")
        return capabilities

    @staticmethod
    def _remote_autonomy_capabilities(actions: list[dict[str, Any]]) -> list[str]:
        action_names = {item.get("name") for item in actions if item.get("status") == "completed"}
        if "autonomous.remote_reflection" in action_names:
            return ["remote_model_autonomous_reflection"]
        return []

    @staticmethod
    def _startup_autonomy_capabilities(actions: list[dict[str, Any]]) -> list[str]:
        action_names = {item.get("name") for item in actions if item.get("status") == "completed"}
        capabilities: list[str] = []
        if "autonomous.startup_orchestrator" in action_names:
            capabilities.append("autonomous_startup_orchestration")
        if "cron.run_due" in action_names:
            capabilities.append("scheduled_task_execution")
        if "self_evolution.governance_ready" in action_names:
            capabilities.append("governed_self_evolution_readiness")
        return capabilities

    def _startup_orchestration_plan(self) -> dict[str, Any]:
        return {
            "status": "started",
            "loops": [
                "runtime_health",
                "approval_sync",
                "memory_periodic_tick",
                "scheduled_task_execution",
                "context_compaction_check",
                "self_model_update",
                "self_evolution_governance_readiness",
            ],
            "high_risk_policy": "prepare and queue for approval; never auto-apply critical changes at startup",
        }

    def _self_evolution_governance_status(self) -> dict[str, Any]:
        pending = [
            {
                "request_id": request.request_id,
                "request_type": request.request_type,
                "risk_level": request.risk_level,
                "status": request.status,
            }
            for request in self.runtime.governance.list_requests("pending")
            if str(request.request_type).startswith(
                ("core_source_change", "model_finetune", "architecture_migration")
            )
        ]
        return {
            "ready": True,
            "pending_requests": pending,
            "approval_timeout_seconds": 30,
            "timeout_decision": "approve_once",
        }

    @staticmethod
    def _self_evolution_startup_policy() -> dict[str, Any]:
        return {
            "core_source_change": "approval_required",
            "model_finetune": "approval_required",
            "architecture_migration_deploy": "approval_required",
            "startup_auto_apply": False,
            "startup_auto_train": False,
            "startup_auto_deploy": False,
        }

    def _prepare_core_source_change(self, task_text: str) -> dict[str, Any] | None:
        normalized = task_text.lower()
        if not any(term in normalized for term in ("核心源码", "core source", "source code", "源码")):
            return None
        root = self.runtime.root_path / "self_evolution" / "core_source_changes" / uuid.uuid4().hex[:8]
        root.mkdir(parents=True, exist_ok=True)
        proposal = {
            "type": "core_source_change",
            "task": task_text,
            "status": "proposed",
            "created_at": datetime.now(UTC).isoformat(),
            "scope": ["tui_gateway", "dual_ring_ai"],
            "safety": {
                "requires_approval": True,
                "requires_tests": True,
                "requires_rollback_plan": True,
                "auto_apply": False,
            },
            "rollback_plan": "revert generated patch and restore previous test-passing state",
        }
        proposal_path = root / "proposal.json"
        patch_path = root / "candidate.patch"
        proposal_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        patch_path.write_text(
            "# Candidate core-source patch will be generated after approval.\n",
            encoding="utf-8",
        )
        request = self.runtime.governance.create_request(
            request_type="core_source_change",
            title="Guarded autonomous core source change",
            payload={
                "proposal_path": str(proposal_path),
                "patch_path": str(patch_path),
                "task": task_text,
                "auto_apply": False,
            },
            requested_by="autonomous_self_evolution",
            risk_level="critical",
        )
        return {"proposal_path": str(proposal_path), "request_id": request.request_id}

    def _prepare_model_finetune(self, task_text: str) -> dict[str, Any] | None:
        normalized = task_text.lower()
        if not any(term in normalized for term in ("微调", "fine-tune", "finetune", "训练", "权重", "model weight")):
            return None
        root = self.runtime.root_path / "self_evolution" / "model_finetunes" / uuid.uuid4().hex[:8]
        root.mkdir(parents=True, exist_ok=True)
        job = {
            "type": "model_finetune",
            "task": task_text,
            "status": "planned",
            "created_at": datetime.now(UTC).isoformat(),
            "dataset_sources": ["experience/conversations.sqlite3", "experience/records.jsonl"],
            "outputs": {"adapter_or_weights": str(root / "outputs")},
            "safety": {
                "requires_approval": True,
                "offline_training_only": True,
                "no_weight_overwrite_without_approval": True,
                "eval_required_before_promotion": True,
            },
        }
        job_path = root / "training_job.json"
        job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        request = self.runtime.governance.create_request(
            request_type="model_finetune",
            title="Autonomous model fine-tuning job",
            payload={"training_job_path": str(job_path), "task": task_text, "auto_apply": False},
            requested_by="autonomous_self_evolution",
            risk_level="critical",
        )
        return {"training_job_path": str(job_path), "request_id": request.request_id}

    def _prepare_architecture_migration_deploy(self, task_text: str) -> dict[str, Any] | None:
        normalized = task_text.lower()
        if not any(term in normalized for term in ("架构", "migration", "迁移", "deploy", "上线", "发布")):
            return None
        root = self.runtime.root_path / "self_evolution" / "architecture_migrations" / uuid.uuid4().hex[:8]
        root.mkdir(parents=True, exist_ok=True)
        plan = {
            "type": "architecture_migration_deploy",
            "task": task_text,
            "status": "planned",
            "created_at": datetime.now(UTC).isoformat(),
            "phases": ["design", "migration_patch", "test", "canary", "deploy", "rollback_ready"],
            "safety": {
                "requires_approval": True,
                "canary_required": True,
                "rollback_required": True,
                "auto_deploy": False,
            },
        }
        plan_path = root / "deployment_plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        request = self.runtime.governance.create_request(
            request_type="architecture_migration_deploy",
            title="Governed architecture migration and deployment",
            payload={"deployment_plan_path": str(plan_path), "task": task_text, "auto_deploy": False},
            requested_by="autonomous_self_evolution",
            risk_level="critical",
        )
        return {"deployment_plan_path": str(plan_path), "request_id": request.request_id}

    @staticmethod
    def _autonomous_next_actions(trigger: str, actions: list[dict[str, Any]]) -> list[str]:
        failed = [item["name"] for item in actions if item.get("status") == "error"]
        if failed:
            return [
                "review failed autonomous maintenance actions",
                "retry recoverable maintenance on the next cycle",
            ]
        if trigger == "session_start":
            return [
                "monitor the next user goal",
                "keep memory and approvals synchronized in the background",
            ]
        return [
            "沉淀已完成工作为可复用记忆",
            "当证据充分时将重复复杂工作提升为技能",
        ]

    @staticmethod
    def _merge_autonomous_next_actions(primary: list[str], remote: Any) -> list[str]:
        merged = [str(item) for item in primary if str(item).strip()]
        if isinstance(remote, list):
            for item in remote:
                text = str(item).strip()
                if text and text not in merged:
                    merged.append(text)
        return merged[:8]

    def _build_autonomous_execution_plan(
        self,
        trigger: str,
        task_text: str,
        next_actions: list[str],
    ) -> dict[str, Any]:
        """Turn autonomous reflection output into auditable low-risk work."""
        objective = next((item for item in next_actions if str(item).strip()), task_text or trigger)
        steps = [
            {
                "id": "runtime.status_snapshot",
                "tool": "runtime.status_snapshot",
                "title": "读取运行状态",
                "reason": "验证运行时服务与会话状态，作为后续自主动作依据。",
                "risk": "low",
                "status": "planned",
            },
            {
                "id": "memory.periodic_tick",
                "tool": "memory.periodic_tick",
                "title": "沉淀维护记忆",
                "reason": "把本轮自主维护目标写入周期性记忆，避免只反思不沉淀。",
                "risk": "low",
                "status": "planned",
                "params": {"task": task_text or objective, "cadence": trigger},
            },
        ]
        return {
            "objective": objective,
            "trigger": trigger,
            "risk_policy": "仅自动执行低风险读取、记忆沉淀和验证动作；高风险变更必须进入审批",
            "steps": steps,
        }

    async def _execute_autonomous_plan(
        self,
        plan: dict[str, Any],
        record: Callable[[str, Any, Exception | None], None],
    ) -> dict[str, Any]:
        steps = [step for step in plan.get("steps", []) if isinstance(step, dict)]
        executed = 0
        verified = 0
        errors = 0
        for step in steps:
            tool = str(step.get("tool", ""))
            try:
                if tool == "runtime.status_snapshot":
                    result = self.runtime.status_snapshot()
                    step["result"] = {
                        "running": result.get("running"),
                        "service_count": len(result.get("services", {})),
                    }
                    step["status"] = "executed"
                    record("autonomous.execute.runtime.status_snapshot", step["result"])
                    if isinstance(result.get("services"), dict) and result["services"]:
                        step["status"] = "verified"
                        verified += 1
                        record(
                            "autonomous.verify.runtime.status_snapshot",
                            {"status": "verified", "service_count": len(result["services"])},
                        )
                elif tool == "memory.periodic_tick":
                    params = step.get("params") if isinstance(step.get("params"), dict) else {}
                    result = self.runtime.periodic_memory_tick(
                        task=str(params.get("task") or plan.get("objective") or "autonomous maintenance"),
                        cadence=str(params.get("cadence") or plan.get("trigger") or "autonomous"),
                    )
                    step["result"] = {"id": result.get("id"), "status": result.get("status")}
                    step["status"] = "executed"
                    record("autonomous.execute.memory.periodic_tick", step["result"])
                    if result.get("id"):
                        step["status"] = "verified"
                        verified += 1
                        record(
                            "autonomous.verify.memory.periodic_tick",
                            {"status": "verified", "id": result.get("id")},
                        )
                else:
                    step["status"] = "skipped"
                    step["reason"] = "tool is not approved for autonomous execution"
                    record(f"autonomous.skip.{tool or 'unknown'}", {"reason": step["reason"]})
                    continue
                executed += 1
            except Exception as exc:
                errors += 1
                step["status"] = "error"
                step["error"] = str(exc)
                record(f"autonomous.execute.{tool or 'unknown'}", error=exc)
        summary = {"executed": executed, "verified": verified, "errors": errors}
        plan["summary"] = summary
        return summary

    @staticmethod
    def _should_create_autonomous_skill(text: str) -> bool:
        normalized = text.lower()
        return any(
            term in normalized
            for term in (
                "complex",
                "multi-step",
                "workflow",
                "pipeline",
                "复杂",
                "多步",
                "流程",
                "工作流",
                "任务",
            )
        )

    @staticmethod
    def _default_config_path(root: Path) -> Path | None:
        for name in ("config.yaml", "config.yml", "agent_config.json"):
            candidate = (root / name).resolve()
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _autonomous_skill_name(text: str) -> str:
        normalized = text.lower()
        if "csv" in normalized:
            return "completed_complex_csv_task_skill"
        return "completed_complex_task_skill"

    async def handle_complete_slash(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", params.get("query", "")))
        if text and not text.startswith("/"):
            text = "/" + text.lstrip("/")
        matches = [
            item
            for item in SLASH_COMMANDS
            if item["text"].startswith(text.lower() or "/")
        ][:30]
        replace_from = text.rfind(" ") + 1 if " " in text else 1
        return {"items": matches, "replace_from": replace_from}

    async def handle_complete_path(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", params.get("query", "")))
        token = text.split()[-1] if text.split() else text
        prefix = token[1:] if token.startswith("@") else token
        prefix = prefix or "."
        base = (project_root / prefix).resolve() if not Path(prefix).is_absolute() else Path(prefix)
        parent = base if base.is_dir() else base.parent
        stem = "" if base.is_dir() else base.name
        items: list[dict[str, str]] = []
        try:
            for path in sorted(parent.glob(f"{stem}*"))[:30]:
                try:
                    rel = path.resolve().relative_to(project_root.resolve())
                    display_path = rel.as_posix()
                except ValueError:
                    display_path = str(path)
                items.append(
                    {
                        "text": f"@{display_path}" if token.startswith("@") else display_path,
                        "display": display_path + ("/" if path.is_dir() else ""),
                        "meta": "dir" if path.is_dir() else "file",
                    }
                )
        except OSError:
                items = []
        return {"items": items, "replace_from": max(0, text.rfind(token))}

    @staticmethod
    def _method_for_reserved_slash(command: str) -> str:
        return {
            "/help": "natural.capabilities",
            "/new": "session.create",
            "/model": "model.options",
        }.get(command, "")

    async def handle_natural_capabilities(self, params: dict[str, Any]) -> dict[str, Any]:
        slash_by_text = {item["text"]: item for item in SLASH_COMMANDS}
        commands = []
        for method, aliases in NATURAL_DIRECT_ALIASES.items():
            if method in AUTONOMOUS_SYSTEM_METHODS:
                continue
            visible_command = next(
                (
                    item["text"]
                    for item in SLASH_COMMANDS
                    if method == self._method_for_reserved_slash(item["text"])
                ),
                method,
            )
            commands.append(
                {
                    "command": visible_command,
                    "method": method,
                    "description": slash_by_text.get(visible_command, {}).get("meta", ""),
                    "aliases": aliases,
                    "input_modes": ["text", "voice"],
                }
            )
        commands.extend(
            [
                {
                    "command": "!shell",
                    "method": "shell.exec",
                    "description": "通过文本或语音运行 shell 命令。",
                    "aliases": SHELL_INTENT_PREFIXES,
                    "input_modes": ["text", "voice"],
                },
                {
                    "command": "prompt.submit",
                    "method": "prompt.submit",
                    "description": "回退到智能体对话提示。",
                    "aliases": ["chat", "ask", "对话", "询问"],
                    "input_modes": ["text", "voice"],
                },
            ]
        )
        commands.extend(
            {**item, "input_modes": ["text", "voice"]}
            for item in NATURAL_BACKEND_ACTIONS
            if str(item.get("method", "")) not in AUTONOMOUS_SYSTEM_METHODS
        )
        existing_methods = {
            item.get("method")
            for item in commands
            if item.get("method")
        }
        catalog = await self.handle_commands_catalog({})
        for category in catalog["categories"]:
            for command in category["commands"]:
                name = command["name"]
                if name.startswith("/") or name in existing_methods or name in AUTONOMOUS_SYSTEM_METHODS:
                    continue
                commands.append(
                    {
                        "command": name,
                        "method": name,
                        "description": command.get("description", ""),
                        "aliases": [name, name.replace(".", " "), name.replace("_", " ")],
                        "input_modes": ["text", "voice"],
                        **self._tool_policy(name),
                    }
                )
        for item in commands:
            method = item.get("method")
            if method and "input_schema" not in item:
                item.update(self._tool_policy(str(method)))
        return {"commands": commands, "default_input_modes": ["text", "voice"]}

    async def handle_natural_resolve(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", "")).strip()
        source = str(params.get("source", "text") or "text")
        return self._resolve_natural_command(text, source=source)

    async def handle_natural_invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", "")).strip()
        source = str(params.get("source", "text") or "text")
        resolved = self._resolve_natural_command(text, source=source)
        if not resolved["matched"]:
            return resolved
        if resolved.get("method") == "shell.exec" and "command_text" in resolved:
            result = await self._execute_agent_tool(
                "shell.exec",
                {"command": resolved["command_text"]},
                auth_scopes=params.get("auth_scopes"),
            )
            if result.get("ok") is False:
                return {**resolved, **result, "result": result}
            return {**resolved, "ok": True, "result": result}
        if resolved.get("method") == "prompt.submit":
            prompt_text = str(resolved.get("prompt_text") or text).strip()
            result = await self.handle_prompt_submit({"text": prompt_text})
            return {**resolved, "ok": True, "result": result}
        if resolved.get("method") and resolved.get("method") != "slash.exec":
            result = await self._execute_agent_tool(
                str(resolved["method"]),
                dict(resolved.get("params") or {}),
                auth_scopes=params.get("auth_scopes"),
            )
            if result.get("ok") is False:
                return {**resolved, **result, "result": result}
            if resolved.get("method") == "agent.parallel":
                return {**resolved, **result, "result": result}
            return {**resolved, "ok": True, "result": result}
        command = str(resolved.get("command", ""))
        result = await self.handle_slash_exec({"text": command})
        return {**resolved, "result": result}

    async def handle_voice_invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        params = dict(params)
        params["source"] = "voice"
        return await self.handle_natural_invoke(params)

    async def handle_slash_exec(self, params: dict[str, Any]) -> dict[str, Any]:
        text, redirect = self._split_terminal_redirect(str(params.get("text", "")).strip())
        command = text.split()[0].lower() if text else "/help"
        async def with_redirect(result: dict[str, Any]) -> dict[str, Any]:
            output = str(result.get("output") or result.get("warning") or "")
            if not redirect or not output:
                return result
            return {**result, "redirect": await self._apply_terminal_redirect_with_policy(output, redirect)}

        if command not in {"/help", "/new", "/model"}:
            return await with_redirect({"type": "exec", "warning": f"未知命令：{command}"})
        if command == "/new":
            parts = text.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip():
                return await with_redirect(await self.handle_session_resume({"session_id": parts[1].strip()}))
            self.history.clear()
            self.session_id = uuid.uuid4().hex[:8]
            self.session_started_at = time.time()
            await self.send_event("session.info", self._session_info())
            return await with_redirect({"type": "exec", "output": f"新会话已开启：{self.session_id}"})

        if command == "/model":
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                configured = await self.handle_model_configure(self._parse_model_spec(parts[1]))
                return await with_redirect({"type": "exec", "output": f"模型已配置：{configured['provider']}:{configured['model']}"})
            return await with_redirect({"type": "exec", "output": self._format_model_status()})
        if command == "/help":
            return await with_redirect({"type": "exec", "output": self._help_text()})
        return await with_redirect({"type": "exec", "warning": f"未知命令：{command}"})

    async def handle_shell_exec(self, params: dict[str, Any]) -> dict[str, Any]:
        command, redirect = self._split_terminal_redirect(str(params.get("command", "")).strip())
        if not command:
            return {"code": 1, "stdout": "", "stderr": "命令为空"}
        argv = shlex.split(command, posix=False)
        completed = subprocess.run(
            argv,
            cwd=project_root,
            capture_output=True,
            shell=False,
            text=True,
            timeout=float(params.get("timeout", 30) or 30),
        )
        result = {
            "code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        if redirect:
            result["redirect"] = await self._apply_terminal_redirect_with_policy(
                completed.stdout or completed.stderr or f"exit {completed.returncode}",
                redirect,
            )
        return result

    async def handle_input_interpolate(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", ""))

        def replace(match: re.Match[str]) -> str:
            command = match.group(1).strip()
            return f"[disabled shell interpolation: {command}]"

        return {"text": re.sub(r"\{!([^}]+)\}", replace, text)}

    async def handle_commands_catalog(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "categories": [
                {
                    "name": "core",
                    "commands": [
                        {"name": item["text"], "description": item["meta"]}
                        for item in SLASH_COMMANDS
                    ],
                },
                {
                    "name": "runtime",
                    "commands": [
                        self._catalog_command("runtime.health", "返回运行时健康报告"),
                        self._catalog_command("runtime.preflight", "返回就绪检查"),
                        self._catalog_command("runtime.host_probe", "探测宿主机集成"),
                        self._catalog_command("runtime.messaging_status", "返回通讯网关状态"),
                        self._catalog_command("runtime.blueprints", "列出智能体蓝图"),
                        self._catalog_command("runtime.skills", "列出已发布技能"),
                        self._catalog_command("runtime.algorithms", "列出算法资产"),
                        self._catalog_command("runtime.audits", "读取后端审计记录"),
                        self._catalog_command("runtime.avatar", "返回最新形象事件"),
                        self._catalog_command("runtime.terminal_ui", "检查终端界面就绪状态"),
                        self._catalog_command("runtime.events", "返回最近运行事件"),
                        self._catalog_command("runtime.write_preflight", "写入就绪报告 JSON"),
                        self._catalog_command("runtime.write_host_probe", "写入宿主机集成探测 JSON"),
                        self._catalog_command("runtime.operational_smoke", "运行冒烟检查"),
                        self._catalog_command("runtime.interaction_stress", "运行交互压力检查"),
                        self._catalog_command("runtime.final_acceptance", "运行并写入最终验收报告"),
                        self._catalog_command("runtime.adapters", "返回适配器健康状态"),
                        self._catalog_command("runtime.status_snapshot", "返回底层运行时状态快照"),
                        self._catalog_command("runtime.start", "启动运行时服务"),
                        self._catalog_command("runtime.stop", "停止运行时服务"),
                        self._catalog_command("runtime.platform_message", "将一条平台消息路由到运行时"),
                        self._catalog_command("agent.parallel", "并发运行独立工具或提示"),
                        self._catalog_command("mcp.server.add", "注册 MCP 标准输入输出服务器"),
                        self._catalog_command("mcp.servers", "列出已配置 MCP 服务器"),
                        self._catalog_command("mcp.tools", "列出 MCP 服务器暴露的工具"),
                        self._catalog_command("mcp.call", "调用 MCP 服务器暴露的工具"),
                        self._catalog_command("cron.create", "创建持久化后端计划任务"),
                        self._catalog_command("cron.list", "列出持久化计划任务"),
                        self._catalog_command("cron.run_due", "运行已到期计划任务"),
                        self._catalog_command("context.attach", "将项目文件附加到提示上下文"),
                        self._catalog_command("context.files", "列出已附加上下文文件"),
                        self._catalog_command("shell.exec", "执行 shell 命令"),
                        self._catalog_command("prompt.submit", "提交智能体提示"),
                    ],
                },
                {
                    "name": "governance",
                    "commands": [
                        self._catalog_command("governance.requests", "列出审批请求"),
                        self._catalog_command("governance.decide", "同意或拒绝审批请求"),
                        self._catalog_command("approval.respond", "响应待处理的 TUI 审批"),
                    ],
                },
                {
                    "name": "learning",
                    "commands": [
                        self._catalog_command("experience.record", "记录可复用经验"),
                        self._catalog_command("experience.search", "搜索历史经验和对话"),
                        self._catalog_command("conversation.record", "将一轮对话记录到跨会话 FTS5 记忆"),
                        self._catalog_command("conversation.search", "搜索自动记录的历史对话"),
                        self._catalog_command("memory.periodic_tick", "运行周期性记忆规划"),
                        self._catalog_command("self_model.read", "读取持久自我模型"),
                        self._catalog_command("self_model.update", "更新持久自我模型"),
                        self._catalog_command("user_model.update", "更新辩证用户模型"),
                        self._catalog_command("user_model.query", "查询辩证用户模型"),
                        self._catalog_command("skill.draft_from_experience", "从经验生成技能提案"),
                        self._catalog_command("skill.autonomous_from_task", "复杂任务完成后生成技能草案"),
                        self._catalog_command("skill.improve_from_usage", "根据使用反馈改进技能草案"),
                        self._catalog_command("skill.merge_preview", "预览多个技能合并"),
                        self._catalog_command("skill.merge", "将多个技能合并为提案"),
                    ],
                },
                {
                    "name": "backend_actions",
                    "commands": [
                        self._catalog_command("skill.request_publish", "创建技能发布请求"),
                        self._catalog_command("skill.publish_approved", "发布已批准技能"),
                        self._catalog_command("algorithm.request_research", "创建算法研究请求"),
                        self._catalog_command("algorithm.run_experiment", "运行已批准算法实验"),
                        self._catalog_command("algorithm.request_promotion", "创建算法晋升请求"),
                        self._catalog_command("algorithm.apply_promotion", "应用已批准算法晋升"),
                        self._catalog_command("organization.request_change", "创建组织变更请求"),
                        self._catalog_command("organization.apply_change", "应用已批准组织变更"),
                        self._catalog_command("organization.rollback", "回滚组织蓝图"),
                        self._catalog_command("self_evolution.apply_core_source_change", "应用已批准核心源码补丁"),
                        self._catalog_command("self_evolution.run_model_finetune", "运行已批准离线微调作业"),
                        self._catalog_command("self_evolution.deploy_architecture_migration", "执行已批准架构迁移部署"),
                    ],
                },
            ],
            "pairs": [(item["text"], item["meta"]) for item in SLASH_COMMANDS],
            "skill_count": 0,
        }

    def _catalog_command(self, name: str, description: str) -> dict[str, Any]:
        policy = self._tool_policy(name)
        return {"name": name, "description": description, **policy}

    async def handle_toolsets_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "toolsets": ["runtime", "governance", "interaction", "shell", "mcp", "cron", "context"],
            "enabled_toolsets": ["runtime", "governance", "interaction", "shell", "mcp", "cron", "context"],
        }

    async def handle_clipboard_paste(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "attached": False,
            "count": 0,
            "message": "Clipboard image attachment is unavailable in this terminal build.",
        }

    async def handle_command_dispatch(self, params: dict[str, Any]) -> dict[str, Any]:
        method = str(params.get("method", "")).strip()
        if method:
            return await self._execute_agent_tool(
                method,
                dict(params.get("params", {})) if isinstance(params.get("params"), dict) else {},
                auth_scopes=params.get("auth_scopes"),
            )
        return await self.handle_slash_exec(params)

    async def _apply_terminal_redirect_with_policy(
        self,
        text: str,
        redirect: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._execute_agent_tool(
            "terminal.redirect",
            {
                "text": text,
                "path": str(redirect.get("path", "")),
                "mode": str(redirect.get("mode", "write") or "write"),
            },
            auth_scopes=["filesystem:write"],
            allow_clarification=False,
        )

    async def _dispatch_rpc_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        handler = getattr(self, f"handle_{method.replace('.', '_')}", None)
        if handler is None:
            raise ValueError(f"method is not available: {method}")
        result = await handler(params)
        return result if isinstance(result, dict) else {"result": result}

    def _split_terminal_redirect(self, text: str) -> tuple[str, dict[str, Any] | None]:
        match = re.search(r"(?<!\S)(?P<operator>>>|>)[ \t]*(?P<path>(?:\"[^\"]+\"|'[^']+'|[^\r\n]+?))[ \t]*$", text)
        if not match:
            return text, None
        target = match.group("path").strip().strip("\"'")
        if not target:
            return text, None
        return text[: match.start()].rstrip(), {
            "path": target,
            "mode": "append" if match.group("operator") == ">>" else "write",
        }

    def _resolve_terminal_redirect_path(self, target: str) -> Path:
        path = Path(target).expanduser()
        if not path.is_absolute():
            path = self.runtime.root_path / path
        resolved = path.resolve()
        runtime_root = self.runtime.root_path.resolve()
        if not self.runtime._is_relative_to(resolved, runtime_root):
            raise ValueError(f"path escapes runtime root: {resolved}")
        return resolved

    async def _apply_terminal_redirect(
        self,
        text: str,
        redirect: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            target = self._resolve_terminal_redirect_path(str(redirect.get("path", "")))
        except ValueError as exc:
            return self._tool_error("PATH_OUTSIDE_RUNTIME_ROOT", str(exc), retryable=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "append" if redirect.get("mode") == "append" else "write"
        payload = text if text.endswith("\n") else f"{text}\n"
        if mode == "append":
            with target.open("a", encoding="utf-8") as handle:
                handle.write(payload)
        else:
            target.write_text(payload, encoding="utf-8")
        result = {
            "ok": True,
            "path": str(target),
            "mode": mode,
            "bytes": len(payload.encode("utf-8")),
        }
        await self.send_event("terminal.redirect", result)
        return result

    async def _execute_agent_tool(
        self,
        method: str,
        params: dict[str, Any],
        auth_scopes: Any = None,
        allow_clarification: bool = True,
    ) -> dict[str, Any]:
        policy = self._tool_policy(method)
        validation_error = self._validate_tool_params(params, policy["input_schema"])
        if validation_error:
            if allow_clarification:
                missing = self._missing_required_tool_param(params, policy["input_schema"])
                if missing:
                    clarification = await self._request_tool_clarification(
                        method=method,
                        params=params,
                        field=missing,
                        auth_scopes=auth_scopes,
                    )
                    return {
                        "ok": False,
                        "requires_clarification": True,
                        "clarification_id": clarification["request_id"],
                        "missing": missing,
                        "question": clarification["question"],
                    }
            return self._tool_error("VALIDATION_ERROR", validation_error, retryable=False)

        allowed_scopes = set(auth_scopes or ["*"])
        required_scope = str(policy.get("auth_scope", ""))
        if "*" not in allowed_scopes and required_scope and required_scope not in allowed_scopes:
            return self._tool_error(
                "PERMISSION_DENIED",
                f"missing auth scope: {required_scope}",
                retryable=False,
            )

        if self._tool_requires_approval(method, policy):
            request = self.runtime.governance.create_request(
                request_type="agent_tool",
                title=f"Execute {method}",
                payload={"method": method, "params": params, "policy": policy},
                requested_by=str(params.get("requested_by", "natural_agent")),
                risk_level=str(policy.get("risk_level", "medium")),
            )
            await self._send_approval_queue()
            return {
                "ok": False,
                "requires_approval": True,
                "approval_id": request.request_id,
                "request": asdict(request),
            }

        retry = dict(policy.get("retry", DEFAULT_TOOL_POLICY["retry"]))
        attempts = max(1, int(retry.get("max_attempts", 1)))
        tool_id = self._tool_activity_id(method)
        await self._send_tool_start(
            tool_id,
            method,
            context=f"natural agent request | risk={policy.get('risk_level', 'low')}",
        )
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                result = await self._dispatch_rpc_method(method, params)
            except Exception as exc:
                last_error = str(exc)
                if attempt < attempts and retry.get("backoff_ms"):
                    await asyncio.sleep(float(retry["backoff_ms"]) / 1000)
                continue
            if isinstance(result, dict) and result.get("status") == "error":
                last_error = str(result.get("error", "backend error"))
                if attempt < attempts and retry.get("backoff_ms"):
                    await asyncio.sleep(float(retry["backoff_ms"]) / 1000)
                continue
            await self._send_tool_complete(tool_id, method, summary="completed")
            return {"ok": True, "attempts": attempt, **result}

        error = last_error or f"{method} failed"
        await self._send_tool_complete(tool_id, method, error=error)
        return self._tool_error(
            "BACKEND_ERROR",
            error,
            retryable=True,
            attempts=attempts,
        )

    @staticmethod
    def _tool_activity_id(method: str) -> str:
        safe_method = re.sub(r"[^a-zA-Z0-9_]+", "_", method).strip("_") or "tool"
        return f"{safe_method}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _tool_requires_approval(method: str, policy: dict[str, Any]) -> bool:
        if method in APPROVAL_POLICY_BYPASS_METHODS:
            return False
        return bool(policy.get("requires_approval")) or str(policy.get("risk_level", "low")) in {"high", "critical"}

    async def _send_tool_start(
        self,
        tool_id: str,
        method: str,
        context: str = "",
        parallel_group_id: str = "",
    ) -> None:
        payload = {
            "tool_id": tool_id,
            "name": method,
        }
        if context:
            payload["context"] = context
        if parallel_group_id:
            payload["parallel_group_id"] = parallel_group_id
        await self.send_event("tool.start", payload)

    async def _send_tool_complete(
        self,
        tool_id: str,
        method: str,
        summary: str = "",
        error: str = "",
    ) -> None:
        payload = {
            "tool_id": tool_id,
            "name": method,
        }
        if summary:
            payload["summary"] = summary
        if error:
            payload["error"] = error
        await self.send_event("tool.complete", payload)

    @staticmethod
    def _tool_policy(method: str) -> dict[str, Any]:
        policy = {**DEFAULT_TOOL_POLICY, **TOOL_POLICIES.get(method, {})}
        policy["retry"] = {**DEFAULT_TOOL_POLICY["retry"], **policy.get("retry", {})}
        return policy

    @staticmethod
    def _validate_tool_params(params: dict[str, Any], schema: dict[str, Any]) -> str:
        for key in schema.get("required", []):
            if key not in params:
                return f"missing required parameter: {key}"
        properties = schema.get("properties", {})
        for key, rule in properties.items():
            if key not in params:
                continue
            value = params[key]
            expected = rule.get("type")
            if expected == "string" and not isinstance(value, str):
                return f"parameter {key} must be string"
            if expected == "integer" and not isinstance(value, int):
                return f"parameter {key} must be integer"
            if expected == "array" and not isinstance(value, list):
                return f"parameter {key} must be array"
            if expected == "object" and not isinstance(value, dict):
                return f"parameter {key} must be object"
            if isinstance(value, int):
                if "minimum" in rule and value < int(rule["minimum"]):
                    return f"parameter {key} must be >= {rule['minimum']}"
                if "maximum" in rule and value > int(rule["maximum"]):
                    return f"parameter {key} must be <= {rule['maximum']}"
        return ""

    @staticmethod
    def _missing_required_tool_param(params: dict[str, Any], schema: dict[str, Any]) -> str:
        for key in schema.get("required", []):
            if key not in params:
                return str(key)
        return ""

    async def _request_tool_clarification(
        self,
        method: str,
        params: dict[str, Any],
        field: str,
        auth_scopes: Any = None,
    ) -> dict[str, Any]:
        request_id = f"clarify_{uuid.uuid4().hex[:8]}"
        payload = {
            "request_id": request_id,
            "question": f"Provide value for {field} to run {method}.",
            "choices": None,
            "method": method,
            "field": field,
        }
        self.pending_clarifications[request_id] = {
            **payload,
            "kind": "agent_tool_param",
            "params": dict(params),
            "auth_scopes": auth_scopes,
        }
        await self.send_event("clarify.request", payload)
        return payload

    @staticmethod
    def _tool_error(
        code: str,
        message: str,
        retryable: bool,
        attempts: int = 0,
    ) -> dict[str, Any]:
        payload = {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
            },
        }
        if attempts:
            payload["attempts"] = attempts
        return payload

    async def handle_approval_respond(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = str(params.get("request_id", ""))
        decision = str(params.get("decision", "deny")).lower()
        if not request_id:
            return {"ok": False}
        stored_decision = "approved" if decision in {"once", "session", "always", "approve", "approved"} else "rejected"
        try:
            self.runtime.governance.decide(
                request_id,
                stored_decision,
                decided_by="tui",
                comments=decision,
            )
        except ValueError as exc:
            return self._tool_error("APPROVAL_ALREADY_DECIDED", str(exc), retryable=False)
        executed = None
        request = self.runtime.governance.get_request(request_id)
        if stored_decision == "approved" and request.request_type == "agent_tool":
            executed = await self._execute_approved_agent_tool(request.payload)
        elif stored_decision == "approved":
            executed = await self._execute_approved_self_evolution_request(request)
        if executed is not None:
            self._mark_approval_execution(request_id, executed)
        await self._send_approval_queue()
        await self.send_event(
            "status.update",
            {"kind": "approval", "text": f"{request_id}: {stored_decision}"},
        )
        response = {"ok": True}
        if executed is not None:
            response["executed"] = executed
        return response

    def _mark_approval_execution(self, request_id: str, executed: dict[str, Any]) -> None:
        ok = bool(executed.get("ok"))
        error = executed.get("error") if isinstance(executed.get("error"), dict) else {}
        message = str(error.get("message", "")) if error else None
        try:
            self.runtime.governance.mark_execution(
                request_id,
                "executed" if ok else "failed",
                message,
            )
        except ValueError:
            logger.warning("approval execution state was not updated: %s", request_id)

    async def _execute_approved_agent_tool(self, payload: dict[str, Any]) -> dict[str, Any]:
        method = str(payload.get("method", ""))
        params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
        tool_id = self._tool_activity_id(method)
        await self._send_tool_start(
            tool_id,
            method,
            context="approved agent tool request",
        )
        try:
            result = await self._dispatch_rpc_method(method, params)
        except Exception as exc:
            await self._send_tool_complete(tool_id, method, error=str(exc))
            return self._tool_error("BACKEND_ERROR", str(exc), retryable=False)
        await self._send_tool_complete(tool_id, method, summary="completed")
        return {"ok": True, "method": method, "result": result}

    async def _execute_approved_self_evolution_request(self, request: Any) -> dict[str, Any] | None:
        method_by_type = {
            "core_source_change": "self_evolution.apply_core_source_change",
            "model_finetune": "self_evolution.run_model_finetune",
            "architecture_migration_deploy": "self_evolution.deploy_architecture_migration",
        }
        method = method_by_type.get(str(getattr(request, "request_type", "")))
        if not method:
            return None
        tool_id = self._tool_activity_id(method)
        await self._send_tool_start(
            tool_id,
            method,
            context="approved self-evolution request",
        )
        try:
            result = await self._dispatch_rpc_method(
                method,
                {
                    "request_id": request.request_id,
                    "approved_by": request.decided_by or "tui",
                },
            )
        except Exception as exc:
            await self._send_tool_complete(tool_id, method, error=str(exc))
            return self._tool_error("BACKEND_ERROR", str(exc), retryable=False)
        await self._send_tool_complete(tool_id, method, summary="completed")
        return {"ok": True, "method": method, "result": result}

    async def handle_clarify_respond(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = str(params.get("request_id", ""))
        if request_id in self.pending_clarifications:
            pending = self.pending_clarifications.pop(request_id)
            pending["answer"] = params.get("answer")
            if pending.get("kind") == "agent_tool_param":
                tool_params = dict(pending.get("params") or {})
                field = str(pending.get("field", ""))
                if field:
                    method = str(pending.get("method", ""))
                    tool_params[field] = self._coerce_clarified_value(
                        method,
                        field,
                        params.get("answer"),
                    )
                executed = await self._execute_agent_tool(
                    str(pending.get("method", "")),
                    tool_params,
                    auth_scopes=pending.get("auth_scopes"),
                    allow_clarification=True,
                )
                if executed.get("requires_clarification"):
                    return {
                        "ok": True,
                        "requires_clarification": True,
                        "clarification": executed,
                    }
                return {"ok": True, "executed": executed}
        return {"ok": True}

    def _coerce_clarified_value(self, method: str, field: str, answer: Any) -> Any:
        policy = self._tool_policy(method)
        rule = policy.get("input_schema", {}).get("properties", {}).get(field, {})
        if rule.get("type") == "object":
            if isinstance(answer, dict):
                return answer
            if isinstance(answer, str):
                stripped = answer.strip()
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    return {"text": stripped}
                return parsed if isinstance(parsed, dict) else {"text": stripped}
            return {"value": answer}
        if rule.get("type") == "integer":
            try:
                return int(answer)
            except (TypeError, ValueError):
                return answer
        return answer

    async def handle_sudo_respond(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = str(params.get("request_id", ""))
        if request_id in self.pending_sudo:
            self.pending_sudo[request_id]["value"] = params.get("value", "")
        return {"ok": True}

    async def handle_secret_respond(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = str(params.get("request_id", ""))
        if request_id in self.pending_secrets:
            self.pending_secrets[request_id]["value"] = params.get("value", "")
        return {"ok": True}

    async def handle_demo_clarify(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = f"clarify_{uuid.uuid4().hex[:8]}"
        payload = {
            "request_id": request_id,
            "question": str(params.get("question", "Clarification required")),
            "choices": params.get("choices"),
        }
        self.pending_clarifications[request_id] = payload
        await self.send_event("clarify.request", payload)
        return {"request_id": request_id}

    async def handle_demo_secret(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = f"secret_{uuid.uuid4().hex[:8]}"
        env_var = str(params.get("env_var", "SECRET"))
        payload = {
            "request_id": request_id,
            "env_var": env_var,
            "prompt": f"Enter value for {env_var}",
        }
        self.pending_secrets[request_id] = payload
        await self.send_event("secret.request", payload)
        return {"request_id": request_id}

    async def handle_demo_sudo(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = f"sudo_{uuid.uuid4().hex[:8]}"
        payload = {"request_id": request_id}
        self.pending_sudo[request_id] = payload
        await self.send_event("sudo.request", payload)
        return {"request_id": request_id}

    async def handle_tool_start(self, params: dict[str, Any]) -> dict[str, Any]:
        await self.send_event("tool.start", params)
        return {"status": "ok"}

    async def handle_tool_progress(self, params: dict[str, Any]) -> dict[str, Any]:
        await self.send_event("tool.progress", params)
        return {"status": "ok"}

    async def handle_tool_complete(self, params: dict[str, Any]) -> dict[str, Any]:
        await self.send_event("tool.complete", params)
        return {"status": "ok"}

    async def handle_terminal_redirect(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", ""))
        path = str(params.get("path", "")).strip()
        mode = str(params.get("mode", "write") or "write")
        if not path:
            parsed_text, redirect = self._split_terminal_redirect(text)
            text = parsed_text
        else:
            redirect = {"path": path, "mode": "append" if mode == "append" else "write"}
        if not redirect:
            return {"ok": False, "error": "missing redirect target"}
        return await self._apply_terminal_redirect(text, redirect)

    async def handle_model_options(self, params: dict[str, Any]) -> dict[str, Any]:
        current = self._model_name()
        remote = self.runtime.adapters.get("remote_llm")
        health = remote.probe() if remote is not None else {"status": "missing"}
        enabled = bool(getattr(remote, "enabled", False)) if remote is not None else False
        provider_slug = self._current_model_provider()
        providers = []
        current_base_url = str(getattr(remote, "base_url", "")) if remote is not None else ""
        current_api_key_env = str(getattr(remote, "api_key_env", "")) if remote is not None else ""
        for slug in VISIBLE_MODEL_PROVIDER_SLUGS:
            preset = MODEL_PROVIDER_PRESETS[slug]
            models = list(preset.get("models", []))
            if slug == provider_slug and current not in models:
                models.insert(0, current)
            providers.append(
                {
                    "name": str(preset.get("name", slug)),
                    "slug": slug,
                    "authenticated": (
                        health.get("status") in {"available", "dry_run"}
                        if slug == provider_slug
                        else bool(os.getenv(str(preset.get("api_key_env", ""))))
                    ),
                    "is_current": enabled and slug == provider_slug,
                    "models": models,
                    "total_models": len(models),
                    "status": health.get("status") if slug == provider_slug else "configured",
                    "base_url": current_base_url if slug == provider_slug and current_base_url else str(preset.get("base_url", "")),
                    "api_key_env": current_api_key_env if slug == provider_slug and current_api_key_env else str(preset.get("api_key_env", "")),
                    "dry_run": bool(getattr(remote, "dry_run", False)) if slug == provider_slug and remote is not None else False,
                    "reason": health.get("reason", "") if slug == provider_slug else "",
                }
            )
        providers.sort(key=lambda item: 0 if item["slug"] == provider_slug else 1)
        return {
            "model": current,
            "provider": provider_slug,
            "config_path": str(self.config_path) if self.config_path else "",
            "env_loaded": self.env_loaded,
            "providers": providers,
        }

    async def handle_model_configure(self, params: dict[str, Any]) -> dict[str, Any]:
        config_path = self.config_path or (self.runtime.root_path / "agent_config.json").resolve()
        config = self._read_or_default_config(config_path)
        requested_provider = str(
            params.get("provider") or params.get("slug") or self._current_model_provider() or CUSTOM_MODEL_PROVIDER_SLUG
        ).strip()
        requested_preset = dict(MODEL_PROVIDER_PRESETS.get(requested_provider, MODEL_PROVIDER_PRESETS[CUSTOM_MODEL_PROVIDER_SLUG]))
        provider = CUSTOM_MODEL_PROVIDER_SLUG
        preset = dict(MODEL_PROVIDER_PRESETS[CUSTOM_MODEL_PROVIDER_SLUG])
        provider_config = config.setdefault("providers", {}).setdefault(provider, {})
        provider_config.setdefault("base_url", requested_preset.get("base_url", preset.get("base_url")))
        provider_config.setdefault("api_key_env", requested_preset.get("api_key_env", preset.get("api_key_env")))
        remote = config.setdefault("adapters", {}).setdefault("remote_llm", {})
        remote.update(
            {
                "enabled": bool(params.get("enabled", True)),
                "dry_run": bool(params.get("dry_run", False)),
                "api_key_env": str(params.get("api_key_env", provider_config.get("api_key_env", remote.get("api_key_env", "OPENAI_API_KEY")))),
                "base_url": str(params.get("base_url", provider_config.get("base_url", remote.get("base_url", "https://api.openai.com/v1")))),
                "model": str(
                    params.get(
                        "model",
                        params.get("name", remote.get("model", (requested_preset.get("models") or preset.get("models") or ["custom-model"])[0])),
                    )
                ),
                "timeout": float(params.get("timeout", remote.get("timeout", 30.0))),
                "temperature": float(params.get("temperature", remote.get("temperature", 0.2))),
                "max_tokens": params.get("max_tokens", remote.get("max_tokens")),
            }
        )
        config["model"] = {"provider": provider, "name": remote["model"]}
        config["providers"][provider] = {"base_url": remote["base_url"], "api_key_env": remote["api_key_env"]}
        self._write_config_file(config_path, config)
        self.config_path = config_path
        self.env_loaded = self._load_env_file(config_path.parent / ".env")
        was_running = self.runtime.running
        if was_running:
            self.runtime.stop()
        self.runtime = LocalRuntime(self._runtime_config_from_mapping(self._read_config_file(config_path)))
        if was_running:
            self.runtime.start()
        health = self.runtime.adapter_health().get("remote_llm", {})
        await self.send_event("status.update", {"kind": "model", "text": f"模型已配置：{remote['model']}"})
        return {
            "ok": True,
            "config_path": str(config_path),
            "provider": provider,
            "model": remote["model"],
            "base_url": remote["base_url"],
            "api_key_env": remote["api_key_env"],
            "health": health,
        }

    async def handle_model_providers(self, params: dict[str, Any]) -> dict[str, Any]:
        providers = []
        for slug in VISIBLE_MODEL_PROVIDER_SLUGS:
            preset = MODEL_PROVIDER_PRESETS[slug]
            providers.append(
                {
                    "slug": slug,
                    "name": preset.get("name", slug),
                    "base_url": preset.get("base_url"),
                    "api_key_env": preset.get("api_key_env"),
                    "models": list(preset.get("models", [])),
                    "auth_types": list(preset.get("auth_types", ["api_key"])),
                }
            )
        return {"providers": providers}

    async def handle_model_setup(self, params: dict[str, Any]) -> dict[str, Any]:
        requested_provider = str(params.get("provider", CUSTOM_MODEL_PROVIDER_SLUG)).strip()
        requested_preset = dict(MODEL_PROVIDER_PRESETS.get(requested_provider, MODEL_PROVIDER_PRESETS[CUSTOM_MODEL_PROVIDER_SLUG]))
        provider = CUSTOM_MODEL_PROVIDER_SLUG
        preset = dict(MODEL_PROVIDER_PRESETS[CUSTOM_MODEL_PROVIDER_SLUG])
        auth_type = str(params.get("auth_type", "api_key")).strip() or "api_key"
        api_key_env = str(params.get("api_key_env", requested_preset.get("api_key_env", preset.get("api_key_env", "OPENAI_API_KEY"))))
        config_path = self.config_path or (self.runtime.root_path / "config.yaml").resolve()
        config = self._read_or_default_config(config_path)
        model = str(params.get("model", (requested_preset.get("models") or preset.get("models") or ["custom-model"])[0]))
        provider_config = config.setdefault("providers", {}).setdefault(provider, {})
        provider_config.update(
            {
                "base_url": str(params.get("base_url", requested_preset.get("base_url", preset.get("base_url", "https://api.openai.com/v1")))),
                "api_key_env": api_key_env,
                "auth_type": auth_type,
            }
        )
        if auth_type == "oauth":
            provider_config["oauth"] = {
                "client_id": str(params.get("client_id", "")),
                "auth_url": str(params.get("auth_url", "")),
                "token_url": str(params.get("token_url", "")),
                "status": "configured",
            }
        elif params.get("api_key"):
            self._write_env_value(config_path.parent / ".env", api_key_env, str(params["api_key"]))
        config["model"] = {"provider": provider, "name": model}
        config.setdefault("adapters", {}).setdefault("remote_llm", {}).update(
            {
                "enabled": True,
                "dry_run": bool(params.get("dry_run", False)),
                "api_key_env": api_key_env,
                "base_url": provider_config["base_url"],
                "model": model,
                "timeout": float(params.get("timeout", 30.0)),
                "temperature": float(params.get("temperature", 0.2)),
                "max_tokens": params.get("max_tokens"),
            }
        )
        self._write_config_file(config_path, config)
        self.config_path = config_path
        self.env_loaded = self._load_env_file(config_path.parent / ".env")
        was_running = self.runtime.running
        if was_running:
            self.runtime.stop()
        self.runtime = LocalRuntime(self._runtime_config_from_mapping(self._read_config_file(config_path)))
        if was_running:
            self.runtime.start()
        return {
            "ok": True,
            "provider": provider,
            "model": model,
            "auth_type": auth_type,
            "config_path": str(config_path),
            "env_path": str(config_path.parent / ".env") if auth_type != "oauth" else "",
        }

    @staticmethod
    def _write_env_value(env_path: Path, key: str, value: str) -> None:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        output = []
        replaced = False
        for line in lines:
            if line.strip().startswith(f"{key}="):
                output.append(f"{key}={value}")
                replaced = True
            else:
                output.append(line)
        if not replaced:
            output.append(f"{key}={value}")
        env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")

    def _read_or_default_config(self, config_path: Path) -> dict[str, Any]:
        if config_path.exists():
            try:
                payload = self._read_config_file(config_path)
            except (json.JSONDecodeError, yaml.YAMLError):
                payload = {}
        else:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("root_path", str(self.runtime.root_path))
        payload.setdefault("enable_agents", False)
        payload.setdefault("managed_paths", {})
        payload.setdefault(
            "security_defaults",
            {
                "network": True,
                "shell": True,
                "filesystem": {"read": ["*"], "write": ["*"]},
                "environment": {"allow": ["*"], "request": ["OPENAI_API_KEY"]},
            },
        )
        return payload

    def _current_model_provider(self) -> str:
        if self.config_path and self.config_path.exists():
            try:
                config = self._read_config_file(self.config_path)
                model = config.get("model") if isinstance(config.get("model"), dict) else {}
                provider = str(model.get("provider", "")).strip()
                if provider:
                    return CUSTOM_MODEL_PROVIDER_SLUG
            except Exception:
                pass
        return CUSTOM_MODEL_PROVIDER_SLUG

    def _read_mcp_servers(self) -> list[dict[str, Any]]:
        payload = self._read_json_file(self.mcp_config_path)
        servers = (payload.get("servers") if isinstance(payload, dict) else []) or []
        return [item for item in servers if isinstance(item, dict)]

    def _find_mcp_server(self, name: str) -> dict[str, Any] | None:
        for server in self._read_mcp_servers():
            if str(server.get("name", "")) == name:
                return server
        return None

    async def _mcp_request(
        self,
        server: dict[str, Any],
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex[:8]
        process = await asyncio.create_subprocess_exec(
            str(server["command"]),
            *(str(arg) for arg in server.get("args", [])),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_root),
            env={**os.environ, **{str(k): str(v) for k, v in dict(server.get("env", {})).items()}},
        )
        try:
            initialize = {
                "jsonrpc": "2.0",
                "id": f"init_{request_id}",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "local-agent-tui", "version": "0.1.0"},
                },
            }
            await self._mcp_write(process, initialize)
            await self._mcp_read_result(process, initialize["id"])
            await self._mcp_write(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
            await self._mcp_write(process, request)
            return await self._mcp_read_result(process, request_id)
        finally:
            if process.stdin:
                process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    @staticmethod
    async def _mcp_write(process: asyncio.subprocess.Process, payload: dict[str, Any]) -> None:
        if process.stdin is None:
            raise RuntimeError("MCP server stdin is unavailable")
        process.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        await process.stdin.drain()

    @staticmethod
    async def _mcp_read_result(process: asyncio.subprocess.Process, request_id: str) -> dict[str, Any]:
        if process.stdout is None:
            raise RuntimeError("MCP server stdout is unavailable")
        while True:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
            if not line:
                stderr = b""
                if process.stderr:
                    stderr = await process.stderr.read()
                raise RuntimeError((stderr.decode("utf-8", errors="replace") or "MCP server closed stdout").strip())
            response = json.loads(line.decode("utf-8"))
            if response.get("id") != request_id:
                continue
            if "error" in response:
                error = response["error"]
                raise RuntimeError(str(error.get("message", error)))
            result = response.get("result", {})
            return result if isinstance(result, dict) else {"result": result}

    def _read_cron_jobs(self) -> list[dict[str, Any]]:
        if not self.cron_jobs_path.exists():
            return []
        try:
            payload = json.loads(self.cron_jobs_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        jobs = payload if isinstance(payload, list) else (payload.get("jobs") if isinstance(payload, dict) else []) or []
        return [item for item in jobs if isinstance(item, dict)]

    def _write_cron_jobs(self, jobs: list[dict[str, Any]]) -> None:
        self._write_json_file(self.cron_jobs_path, {"jobs": jobs})

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _normalize_run_at(self, value: Any) -> str:
        parsed = self._parse_datetime(value)
        return parsed.isoformat() if parsed else ""

    @staticmethod
    def _read_json_file(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _resolve_context_path(self, target: str) -> Path:
        path = Path(target.strip().strip("\"'")).expanduser()
        if not path.is_absolute():
            path = project_root / path
        return path.resolve()

    async def _attach_context_refs(self, text: str) -> str:
        refs = self._extract_context_refs(text)
        for ref in refs:
            path = self._resolve_context_path(ref)
            if str(path) in self.context_files:
                continue
            if path.exists() and path.is_file():
                await self.handle_context_attach({"path": str(path)})
        if not self.context_files:
            return text
        blocks = []
        for item in self.context_files.values():
            blocks.append(
                (
                    f"## {item['path']}\n"
                    f"{item['text']}"
                    f"{'\\n[truncated]' if item.get('truncated') else ''}"
                )
            )
        return f"{text}\n\n[Project Context Files]\n" + "\n\n".join(blocks)

    @staticmethod
    def _extract_context_refs(text: str) -> list[str]:
        refs: list[str] = []
        for match in re.finditer(r"@(\"[^\"]+\"|'[^']+'|[^\s]+)", text):
            raw = match.group(1).strip().strip("\"'")
            if raw:
                refs.append(raw)
        return refs

    @staticmethod
    def _public_context_file(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "path": item.get("path", ""),
            "bytes": item.get("bytes", 0),
            "truncated": bool(item.get("truncated", False)),
            "attached_at": item.get("attached_at", ""),
        }

    @staticmethod
    def _parse_model_spec(spec: str) -> dict[str, Any]:
        text = spec.strip()
        if ":" in text:
            provider, model = text.split(":", maxsplit=1)
        else:
            provider, model = "openai", text
        return {"provider": provider.strip(), "model": model.strip()}

    def _format_model_status(self) -> str:
        options = {
            "provider": self._current_model_provider(),
            "model": self._model_name(),
        }
        remote = self.runtime.adapters.get("remote_llm")
        if remote is not None:
            health = remote.probe()
            options.update(
                {
                    "status": health.get("status"),
                    "base_url": getattr(remote, "base_url", ""),
                    "api_key_env": getattr(remote, "api_key_env", ""),
                    "reason": health.get("reason", ""),
                }
            )
        return json.dumps(options, ensure_ascii=False, indent=2)

    async def handle_tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"output": self._format_tools()}

    async def handle_terminal_resize(self, params: dict[str, Any]) -> dict[str, Any]:
        self.cols = int(params.get("cols", self.cols) or self.cols)
        return {"ok": True}

    async def handle_voice_toggle(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "available": True,
            "enabled": True,
            "details": "Voice text is routed through the same natural-language command gateway as typed text.",
        }

    async def handle_voice_record(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path = params.get("audio_path")
        text = str(params.get("text", "")).strip()
        transcription: dict[str, Any] | None = None
        if not text and audio_path:
            transcription = self.runtime.adapters["whisper"].transcribe(audio_path)
            text = self._extract_transcribed_text(transcription)
        if not text:
            return {
                "status": "stopped",
                "source": "voice",
                "matched": False,
                "text": "",
                "transcription": transcription,
            }
        invoked = await self.handle_voice_invoke({"text": text})
        return {"status": "completed", "text": text, **invoked, "transcription": transcription}

    async def _maybe_auto_compact_context(self) -> None:
        usage = self._usage()
        if len(self.history) <= 20 and usage["context_percent"] < 70:
            return
        await self.handle_session_compress({"trigger": "auto"})

    async def _send_context_compaction(
        self,
        trigger: str,
        before_usage: dict[str, Any],
        after_usage: dict[str, Any],
        removed_messages: int,
        summary: dict[str, Any],
    ) -> None:
        await self.send_event(
            "context.compaction",
            {
                "trigger": trigger,
                "before_messages": removed_messages + len(self.history),
                "after_messages": len(self.history),
                "removed_messages": removed_messages,
                "before_tokens": before_usage["total"],
                "after_tokens": after_usage["total"],
                "context_percent": after_usage["context_percent"],
                "summary": summary,
            },
        )

    def _assess_runtime_risk(self, text: str) -> dict[str, Any]:
        normalized = text.lower()
        signals: list[str] = []
        level = "low"
        approval_policy = "无需审批"
        high_terms = [
            "delete",
            "remove",
            "write",
            "modify",
            "shell",
            "command",
            "execute",
            "approval",
            "organization",
            "publish",
            "promote",
            "权限",
            "审批",
            "删除",
            "执行",
            "修改",
        ]
        critical_terms = [
            "default allow",
            "all permissions",
            "production",
            "critical",
            "constitutional",
            "rollback",
            "默认放开",
            "所有权限",
            "组织",
        ]
        if any(term in normalized for term in high_terms):
            level = "medium"
            approval_policy = "执行前显示审批队列"
            signals.append("操作可能影响工具、文件或治理状态")
        if any(term in normalized for term in critical_terms):
            level = "high"
            approval_policy = "状态变更类后端操作需要人工审批"
            signals.append("请求包含高影响运行时或组织变更")
        pending = [
            request.request_id
            for request in self.runtime.governance.list_requests("pending")
        ]
        if pending:
            signals.append(f"{len(pending)} 个待审批请求")
        return {
            "level": level,
            "signals": signals or ["只读或对话请求"],
            "approval_policy": approval_policy,
            "pending_approvals": pending,
        }

    def _reasoning_summary(self, text: str, risk: dict[str, Any]) -> str:
        words = text.split()
        preview = " ".join(words[:16])
        if len(words) > 16:
            preview += "..."
        return (
            f"意图：{preview or '空请求'} | "
            f"风险：{self._zh_risk_level(risk['level'])} | "
            f"策略：{risk['approval_policy']}"
        )

    @staticmethod
    def _zh_risk_level(level: str) -> str:
        return {
            "low": "低",
            "medium": "中",
            "high": "高",
            "critical": "严重",
        }.get(str(level), str(level))

    def _resolve_natural_command(self, text: str, source: str = "text") -> dict[str, Any]:
        normalized = self._normalize_natural_text(text)
        if not normalized:
            return {"matched": False, "source": source, "text": text}
        if text.strip().startswith("/"):
            command = text.strip().split()[0].lower()
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": command,
                "method": "slash.exec",
                "confidence": 1.0,
                "intent": "ui.slash_command",
                "slots": {"command": command},
            }
        shell_command = self._extract_shell_command(text, normalized)
        if shell_command:
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": "!shell",
                "method": "shell.exec",
                "command_text": shell_command,
                "confidence": 0.95,
                "intent": self._intent_for_method("shell.exec"),
                "params": {"command": shell_command},
                "slots": {"command": shell_command},
            }
        prompt_text = self._extract_prompt_text(text, normalized)
        if prompt_text:
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": "prompt.submit",
                "method": "prompt.submit",
                "prompt_text": prompt_text,
                "confidence": 0.9,
                "intent": self._intent_for_method("prompt.submit"),
                "params": {"text": prompt_text},
                "slots": {"text": prompt_text},
            }
        parallel_params = self._extract_parallel_params(text, normalized)
        if parallel_params:
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": "agent.parallel",
                "method": "agent.parallel",
                "params": parallel_params,
                "confidence": 0.94,
                "intent": self._intent_for_method("agent.parallel"),
                "slots": parallel_params,
            }
        backend_method = self._extract_backend_method(text, normalized)
        if backend_method:
            method, parsed_params = backend_method
            parsed_params = self._infer_backend_params(method, text, parsed_params)
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": method,
                "method": method,
                "params": parsed_params,
                "confidence": 0.95,
                "intent": self._intent_for_method(method),
                "slots": parsed_params,
            }
        common_intent = self._extract_common_natural_intent(text, normalized)
        if common_intent:
            method, parsed_params, confidence = common_intent
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": method,
                "method": method,
                "params": parsed_params,
                "confidence": confidence,
                "intent": self._intent_for_method(method),
                "slots": parsed_params,
            }
        approval_intent = self._extract_approval_response(text, normalized)
        if approval_intent:
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": "approval.respond",
                "method": "approval.respond",
                "params": approval_intent,
                "confidence": 0.9,
                "intent": self._intent_for_method("approval.respond"),
                "slots": approval_intent,
            }
        backend_alias = self._match_backend_alias(text, normalized)
        if backend_alias:
            method, alias = backend_alias
            parsed_params = self._infer_backend_params(
                method,
                text,
                self._extract_natural_params(text),
            )
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": method,
                "method": method,
                "params": parsed_params,
                "confidence": 0.86,
                "intent": self._intent_for_method(method),
                "slots": parsed_params,
                "matched_alias": alias,
            }
        direct_alias_matches: list[tuple[str, str, str]] = []
        for method, aliases in NATURAL_DIRECT_ALIASES.items():
            if method in AUTONOMOUS_SYSTEM_METHODS:
                continue
            for alias in aliases:
                normalized_alias = self._normalize_natural_text(alias)
                if normalized_alias and normalized_alias in normalized:
                    direct_alias_matches.append((method, alias, normalized_alias))
        if direct_alias_matches:
            method, alias, _ = sorted(direct_alias_matches, key=lambda item: len(item[2]), reverse=True)[0]
            parsed_params = self._infer_backend_params(
                method,
                text,
                self._extract_natural_params(text),
            )
            return {
                "matched": True,
                "source": source,
                "text": text,
                "command": method,
                "method": method,
                "params": parsed_params,
                "confidence": 0.82,
                "intent": self._intent_for_method(method),
                "slots": parsed_params,
                "matched_alias": alias,
            }
        return {"matched": False, "source": source, "text": text}

    @staticmethod
    def _intent_for_method(method: str) -> str:
        return INTENT_BY_METHOD.get(method, method.replace(".", "_"))

    def _extract_plain_platform_message_intent(
        self,
        text: str,
        normalized: str,
    ) -> dict[str, Any] | None:
        platform = ""
        for canonical, aliases in PLATFORM_ALIASES.items():
            if any(alias in normalized for alias in aliases):
                platform = canonical
                break
        if not platform:
            return None
        match = re.search(
            r"(?:给|向|往)\s*(?:飞书|钉钉|微信|企业微信)\s*(?:发|发送|推送)?\s*(?:消息|通知|文本)?\s*[：:\s]*(?P<message>.+)$",
            text.strip(),
        )
        if not match:
            return None
        message = match.group("message").strip(" ：:")
        if not message:
            return None
        return {"platform": platform, "payload": {"text": message}}

    @staticmethod
    def _extract_plain_model_name(text: str, normalized: str) -> str:
        if "模型" not in normalized and "model" not in normalized:
            return ""
        match = re.search(
            r"(?:切换|设置|使用|配置|换成|切到|改成)\s*(?:到|为|成)?\s*(?:模型)?\s*(?P<model>[a-zA-Z0-9_./:-]+)",
            text.strip(),
            re.IGNORECASE,
        )
        return match.group("model").strip() if match else ""

    @staticmethod
    def _extract_plain_conversation_search_query(
        text: str,
        normalized: str,
    ) -> str:
        if not any(term in normalized for term in ("搜索", "查找", "回忆", "找一下", "想一下")):
            return ""
        if not any(term in normalized for term in ("对话", "会话", "历史", "之前", "过去", "以前")):
            return ""
        match = re.search(
            r"(?:搜索|查找|回忆(?:一下)?|找一下|想一下)(?:之前|过去|历史|以前)?(?:的)?(?:对话|会话)?(?:里|中)?(?:关于|有关)?\s*(?P<query>.+?)(?:的)?(?:对话|会话|内容|记录)?$",
            text.strip(),
        )
        if not match:
            return ""
        query = match.group("query").strip(" ：:，。, .")
        return query

    @staticmethod
    def _extract_plain_experience_record_text(
        text: str,
        normalized: str,
    ) -> str:
        if not any(term in normalized for term in ("记住", "记下", "记录", "保存经验", "存为经验", "经验存起来")):
            return ""
        patterns = [
            r"^\s*(?:请)?(?:记住|记下|记录|保存经验|保存为经验|存为经验)\s*[：:\s]*(?P<body>.+)$",
            r"^\s*把(?:这个|这条)?经验存起来\s*[：:\s]*(?P<body>.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                body = match.group("body").strip(" ：:")
                if body:
                    return body
        return ""

    def _extract_common_natural_intent(
        self,
        text: str,
        normalized: str,
    ) -> tuple[str, dict[str, Any], float] | None:
        approval = self._extract_approval_response(text, normalized)
        if approval:
            return "approval.respond", approval, 0.9
        reserved = self._extract_reserved_tui_intent(text, normalized)
        if reserved:
            method, params = reserved
            return method, params, 0.9
        plain_model = self._extract_plain_model_name(text, normalized)
        if plain_model:
            return "model.configure", {"model": plain_model}, 0.91
        platform_message = self._extract_platform_message_intent(text, normalized)
        if platform_message:
            return "runtime.platform_message", platform_message, 0.9
        plain_query = self._extract_plain_conversation_search_query(text, normalized)
        if plain_query:
            return "conversation.search", {"query": plain_query}, 0.9
        conversation_search = self._extract_conversation_search_intent(text, normalized)
        if conversation_search:
            return "conversation.search", conversation_search, 0.88
        plain_experience = self._extract_plain_experience_record_text(text, normalized)
        if plain_experience:
            return "experience.record", {"text": plain_experience, "source": "natural_intent"}, 0.9
        experience_record = self._extract_experience_record_intent(text, normalized)
        if experience_record:
            return "experience.record", experience_record, 0.88
        final_acceptance = self._extract_final_acceptance_intent(text, normalized)
        if final_acceptance:
            return "runtime.final_acceptance", final_acceptance, 0.86
        development_task = self._extract_development_task_intent(text, normalized)
        if development_task:
            return "development.task.start", development_task, 0.92
        return None

    @staticmethod
    def _extract_development_task_intent(
        text: str,
        normalized: str,
    ) -> dict[str, Any] | None:
        triggers = (
            "development task",
            "autonomous development",
            "plan and execute",
            "复杂开发任务",
            "自主规划与执行",
            "自主开发",
            "完成复杂开发任务",
        )
        if not any(trigger in normalized for trigger in triggers):
            return None
        goal = text.strip()
        for separator in ("：", ":", "-", "—"):
            if separator in goal:
                tail = goal.split(separator, 1)[1].strip()
                if tail:
                    goal = tail
                    break
        return {
            "goal": goal,
            "context": {"source": "natural_language"},
            "auto_execute": True,
        }

    def _match_backend_alias(self, text: str, normalized: str) -> tuple[str, str] | None:
        candidates: list[tuple[str, str]] = []
        for item in NATURAL_BACKEND_ACTIONS:
            method = str(item.get("method", ""))
            if method in AUTONOMOUS_SYSTEM_METHODS:
                continue
            aliases = [method, method.replace(".", " "), method.replace("_", " ")]
            aliases.extend(str(alias) for alias in item.get("aliases", []))
            for alias in aliases:
                normalized_alias = self._normalize_natural_text(alias)
                if normalized_alias and normalized_alias in normalized:
                    candidates.append((method, alias))
        if not candidates:
            for method in TOOL_POLICIES:
                if method in AUTONOMOUS_SYSTEM_METHODS:
                    continue
                aliases = [method, method.replace(".", " "), method.replace("_", " ")]
                for alias in aliases:
                    normalized_alias = self._normalize_natural_text(alias)
                    if normalized_alias and normalized_alias in normalized:
                        candidates.append((method, alias))
        if not candidates:
            return None
        candidates.sort(key=lambda item: len(self._normalize_natural_text(item[1])), reverse=True)
        return candidates[0]

    def _extract_approval_response(
        self,
        text: str,
        normalized: str,
    ) -> dict[str, Any] | None:
        approve_terms = ("approve", "allow", "yes", "once", "同意", "批准", "通过", "允许")
        deny_terms = ("deny", "reject", "no", "拒绝", "否", "不同意", "驳回")
        if not any(term in normalized for term in approve_terms + deny_terms):
            return None
        if (
            "request" not in normalized
            and "approval" not in normalized
            and "审批" not in normalized
            and "审核" not in normalized
            and "请求" not in normalized
        ):
            return None
        decision = "once" if any(term in normalized for term in approve_terms) else "deny"
        request_id = self._extract_request_id(text)
        if not request_id and (
            "latest" in normalized
            or "last" in normalized
            or "request" in normalized
            or "最新" in normalized
            or "最近" in normalized
            or "审批" in normalized
            or "审核" in normalized
        ):
            request_id = self._latest_pending_request_id()
        if not request_id:
            return None
        return {"request_id": request_id, "decision": decision}

    def _extract_platform_message_intent(
        self,
        text: str,
        normalized: str,
    ) -> dict[str, Any] | None:
        plain = self._extract_plain_platform_message_intent(text, normalized)
        if plain:
            return plain
        platform_aliases = {
            "feishu": ("feishu", "lark", "飞书"),
            "dingtalk": ("dingtalk", "dingding", "钉钉"),
            "wechat": ("wechat", "weixin", "微信"),
        }
        platform = ""
        for canonical, aliases in platform_aliases.items():
            if any(alias in normalized for alias in aliases):
                platform = canonical
                break
        if not platform:
            return None
        english = re.search(
            r"\b(?:send|post|deliver)\s+(?:to\s+)?(?:feishu|lark|dingtalk|dingding|wechat|weixin)\s+(?:message|text)\s+(.+)$",
            text.strip(),
            re.IGNORECASE,
        )
        chinese = re.search(
            r"(?:给|向)?(?:飞书|钉钉|微信)(?:发|发送|推送)(?:消息|通知)?[：:\s]*(.+)$",
            text.strip(),
        )
        message = ""
        if english:
            message = english.group(1).strip()
        elif chinese:
            message = chinese.group(1).strip()
        if not message:
            return None
        return {"platform": platform, "payload": {"text": message}}

    def _extract_reserved_tui_intent(
        self,
        text: str,
        normalized: str,
    ) -> tuple[str, dict[str, Any]] | None:
        if any(term in normalized for term in ("help", "commands", "显示可用命令", "可用命令", "帮助", "命令列表")):
            return "natural.capabilities", {}
        if any(term in normalized for term in ("new session", "start new session", "开启新会话", "新会话", "创建新会话")):
            return "session.create", {}
        resume_match = re.search(
            r"(?:resume|continue|restore|继续|恢复)\s*(?:session|conversation|会话)?\s*(?P<session_id>[a-zA-Z0-9_-]{4,})",
            text.strip(),
            re.IGNORECASE,
        )
        if resume_match:
            return "session.resume", {"session_id": resume_match.group("session_id")}
        if any(term in normalized for term in ("model picker", "choose model", "select model", "打开模型选择器", "选择模型")):
            return "model.options", {}
        model_match = re.search(
            r"(?:switch|change|set|use|configure|切换|设置|使用|配置|切到)\s*(?:model|模型)?\s*(?:to|为|成|到)?\s*(?P<model>[a-zA-Z0-9_./:-]+)",
            text.strip(),
            re.IGNORECASE,
        )
        if model_match and any(term in normalized for term in ("model", "模型")):
            return "model.configure", {"model": model_match.group("model")}
        return None

    def _extract_conversation_search_intent(
        self,
        text: str,
        normalized: str,
    ) -> dict[str, Any] | None:
        has_search = any(term in normalized for term in ("search", "find", "recall", "look up", "搜索", "查找", "回忆", "查一下"))
        has_memory_scope = any(
            term in normalized
            for term in (
                "conversation",
                "conversations",
                "chat history",
                "previous",
                "past",
                "history",
                "对话",
                "会话",
                "过去",
                "历史",
                "以前",
            )
        )
        if not has_search or not has_memory_scope:
            return None
        query = self._extract_search_query(text)
        if not query:
            return None
        return {"query": query}

    def _extract_experience_record_intent(
        self,
        text: str,
        normalized: str,
    ) -> dict[str, Any] | None:
        patterns = [
            r"^\s*(?:remember|memorize|record|store)\s+(?:that\s+)?(?P<body>.+)$",
            r"^\s*(?:请)?(?:记住|记录|保存经验|记忆)[：:\s]*(?P<body>.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text.strip(), re.IGNORECASE)
            if match:
                body = match.group("body").strip(" ：:")
                if body:
                    return {"text": body, "source": "natural_intent"}
        if "记住" in normalized or "remember" in normalized:
            body = re.sub(r"^\s*(?:请)?(?:记住|remember)(?:that)?[：:\s]*", "", text.strip(), flags=re.IGNORECASE).strip()
            if body and body != text.strip():
                return {"text": body, "source": "natural_intent"}
        return None

    def _extract_final_acceptance_intent(
        self,
        text: str,
        normalized: str,
    ) -> dict[str, Any] | None:
        if not (
            ("final" in normalized and "acceptance" in normalized)
            or "最终验收" in normalized
            or "验收报告" in normalized
        ):
            return None
        return self._infer_stress_cycle_params(text, {})

    @staticmethod
    def _extract_search_query(text: str) -> str:
        patterns = [
            r"\b(?:search|find|recall|look up)\s+(?:previous\s+|past\s+)?(?:conversations?|chat history|history)?\s*(?:for|about)?\s*(?P<query>.+)$",
            r"(?:搜索|查找|回忆|查一下)(?:过去|历史|以前)?(?:对话|会话)?(?:里|中)?(?:关于|有关)?\s*(?P<query>.+?)(?:的内容|内容|记录)?$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text.strip(), re.IGNORECASE)
            if match:
                query = match.group("query").strip(" ：:，。,.")
                if query:
                    return query
        return ""

    @staticmethod
    def _extract_request_id(text: str) -> str:
        match = re.search(r"\b(approval_[a-zA-Z0-9]+|clarify_[a-zA-Z0-9]+)\b", text)
        return match.group(1) if match else ""

    def _latest_pending_request_id(self) -> str:
        pending = self.runtime.governance.list_requests("pending")
        if not pending:
            return ""
        return pending[-1].request_id

    def _infer_backend_params(
        self,
        method: str,
        text: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if method == "runtime.platform_message":
            return self._infer_platform_message_params(text, params)
        if method == "runtime.final_acceptance":
            return self._infer_stress_cycle_params(text, params)
        if method == "mcp.call":
            return self._infer_mcp_call_params(text, params)
        if method == "context.attach":
            return self._infer_context_attach_params(text, params)
        if method == "development.task.start":
            return self._infer_development_task_start_params(text, params)
        if method == "model.configure":
            return self._infer_model_configure_params(text, params)
        if method == "session.resume":
            return self._infer_session_resume_params(text, params)
        if method == "session.steer":
            return self._infer_session_steer_params(text, params)
        return params

    @staticmethod
    def _infer_development_task_start_params(
        text: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if params.get("goal"):
            return params
        goal = text.strip()
        for separator in ("：", ":", "-", "—"):
            if separator in goal:
                tail = goal.split(separator, 1)[1].strip()
                if tail:
                    goal = tail
                    break
        return {
            **params,
            "goal": goal,
            "context": params.get("context") if isinstance(params.get("context"), dict) else {"source": "natural_language"},
            "auto_execute": bool(params.get("auto_execute", True)),
        }

    def _infer_platform_message_params(
        self,
        text: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if params.get("platform") and isinstance(params.get("payload"), dict):
            return params
        inferred = dict(params)
        match = re.search(
            r"\bto\s+(?P<platform>[a-zA-Z0-9_-]+)\s+(?:text|message)\s+(?P<message>.+)$",
            text.strip(),
            re.IGNORECASE,
        )
        if not match:
            return inferred
        inferred.setdefault("platform", match.group("platform"))
        inferred.setdefault("payload", {"text": match.group("message").strip()})
        return inferred

    @staticmethod
    def _infer_stress_cycle_params(
        text: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if "stress_cycles" in params:
            return params
        match = re.search(r"\b(\d+)\s+(?:stress\s+)?cycles?\b", text, re.IGNORECASE)
        if not match:
            match = re.search(r"(\d+)\s*(?:轮|次|遍|个)?", text)
        if not match:
            return params
        return {**params, "stress_cycles": int(match.group(1))}

    @staticmethod
    def _infer_mcp_call_params(text: str, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("server") and params.get("tool"):
            return params
        match = re.search(
            r"\bmcp(?:\.call)?\s+(?P<server>[a-zA-Z0-9_-]+)\s+(?P<tool>[a-zA-Z0-9_.-]+)",
            text,
            re.IGNORECASE,
        )
        if not match:
            return params
        return {**params, "server": match.group("server"), "tool": match.group("tool")}

    def _infer_context_attach_params(self, text: str, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("path"):
            return params
        refs = self._extract_context_refs(text)
        if not refs:
            return params
        return {**params, "path": refs[0]}

    @staticmethod
    def _infer_model_configure_params(text: str, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("model"):
            return params
        match = re.search(
            r"(?:switch|change|set|use|configure|切换|设置|使用|配置|切到)\s*(?:model|模型)?\s*(?:to|为|成|到)?\s*(?P<model>[a-zA-Z0-9_./:-]+)",
            text.strip(),
            re.IGNORECASE,
        )
        if not match:
            return params
        return {**params, "model": match.group("model")}

    @staticmethod
    def _infer_session_resume_params(text: str, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("session_id"):
            return params
        match = re.search(
            r"(?:resume|continue|restore|继续|恢复)\s*(?:session|conversation|会话)?\s*(?P<session_id>[a-zA-Z0-9_-]{4,})",
            text.strip(),
            re.IGNORECASE,
        )
        if not match:
            return params
        return {**params, "session_id": match.group("session_id")}

    @staticmethod
    def _infer_session_steer_params(text: str, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("text"):
            return params
        match = re.search(
            r"(?:personality|persona|style|个性|人格|风格)(?:设置|设为|切换为|调整为)?[：:\s]*(?P<text>.+)$",
            text.strip(),
            re.IGNORECASE,
        )
        if not match:
            return params
        value = match.group("text").strip()
        return {**params, "text": value} if value else params

    def _extract_parallel_params(self, text: str, normalized: str) -> dict[str, Any]:
        has_parallel_intent = any(
            term in normalized
            for term in (
                "parallel agents",
                "parallel tools",
                "parallel tasks",
                "run tasks in parallel",
                "concurrent agents",
                "concurrent tools",
                "代理并行化",
                "并行代理",
                "并行执行",
                "并行工具",
            )
        )
        if not has_parallel_intent:
            return {}
        params = self._extract_natural_params(text)
        tasks = params.get("tasks")
        if isinstance(tasks, list):
            normalized_tasks = self._normalize_parallel_tasks(tasks)
        else:
            normalized_tasks = self._extract_parallel_task_specs(text)
        if not normalized_tasks:
            return {}
        result: dict[str, Any] = {"tasks": normalized_tasks}
        if isinstance(params.get("max_concurrency"), int):
            result["max_concurrency"] = params["max_concurrency"]
        return result

    @staticmethod
    def _normalize_parallel_tasks(tasks: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(tasks, start=1):
            if isinstance(item, str):
                text = item.strip()
                if text:
                    normalized.append({"id": f"task_{index}", "prompt": text})
                continue
            if not isinstance(item, dict):
                continue
            task = dict(item)
            method = str(task.get("method", "")).strip()
            prompt = str(task.get("prompt", task.get("text", ""))).strip()
            params = task.get("params") if isinstance(task.get("params"), dict) else {}
            if method:
                normalized.append(
                    {
                        "id": str(task.get("id") or f"task_{index}"),
                        "method": method,
                        "params": params,
                    }
                )
            elif prompt:
                normalized.append({"id": str(task.get("id") or f"task_{index}"), "prompt": prompt})
        return normalized

    def _extract_parallel_task_specs(self, text: str) -> list[dict[str, Any]]:
        methods = re.findall(r"\b([a-z][a-z0-9_]*\.[a-z][a-z0-9_\.]*)\b", text, re.IGNORECASE)
        tasks: list[dict[str, Any]] = []
        for method in methods:
            normalized = method.lower()
            if normalized == "agent.parallel":
                continue
            tasks.append({"id": f"task_{len(tasks) + 1}", "method": normalized, "params": {}})
        return tasks

    @staticmethod
    def _normalize_natural_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    def _extract_shell_command(self, text: str, normalized: str) -> str:
        stripped = text.strip()
        if stripped.startswith("!"):
            return stripped[1:].strip()
        for prefix in SHELL_INTENT_PREFIXES:
            normalized_prefix = self._normalize_natural_text(prefix)
            if normalized.startswith(normalized_prefix):
                return stripped[len(prefix) :].strip(" ：:")
        return ""

    def _extract_prompt_text(self, text: str, normalized: str) -> str:
        stripped = text.strip()
        for prefix in ("chat", "ask"):
            normalized_prefix = self._normalize_natural_text(prefix)
            if normalized.startswith(f"{normalized_prefix} "):
                return stripped[len(prefix) :].strip(" :")
        return ""

    def _extract_backend_method(self, text: str, normalized: str) -> tuple[str, dict[str, Any]] | None:
        if not (
            normalized.startswith("run backend ")
            or normalized.startswith("execute backend ")
            or normalized.startswith("call backend ")
            or normalized.startswith("invoke backend ")
            or normalized.startswith("backend ")
        ):
            return None
        match = re.search(r"\b([a-z][a-z0-9_]*\.[a-z][a-z0-9_\.]*)\b", text, re.IGNORECASE)
        if not match:
            return None
        method = match.group(1).lower()
        params = self._extract_natural_params(text[match.end() :])
        return method, params

    @staticmethod
    def _extract_natural_params(text: str) -> dict[str, Any]:
        marker = "params="
        if marker in text:
            raw = text.split(marker, 1)[1].strip()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            return payload if isinstance(payload, dict) else {}
        params: dict[str, Any] = {}
        for key in ("tasks", "args", "env", "params", "arguments"):
            match = re.search(rf"{key}=([\s\S]+?)(?=\s+[a-zA-Z_][\w]*=|$)", text)
            if not match:
                continue
            raw = match.group(1).strip()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            params[key] = payload
        for key, value in re.findall(r"([a-zA-Z_][\w]*)=([^\s]+)", text):
            if key in params:
                continue
            if value.isdigit():
                params[key] = int(value)
                continue
            try:
                params[key] = float(value)
                continue
            except ValueError:
                params[key] = value.strip("\"'")
        return params

    @staticmethod
    def _extract_transcribed_text(transcription: dict[str, Any] | None) -> str:
        if not transcription:
            return ""
        if isinstance(transcription.get("text"), str):
            return str(transcription["text"]).strip()
        stdout = str(transcription.get("stdout", "") or "").strip()
        if not stdout:
            return ""
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout
        return str(payload.get("text", "")).strip()

    def _session_info(self, usage: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = self.runtime.status_snapshot()
        return {
            "id": self.session_id,
            "model": self._model_name(),
            "personality": self.personality,
            "reasoning_effort": "local",
            "service_tier": "local",
            "fast": True,
            "tools": {"runtime": list(snapshot["services"].keys())},
            "skills": {},
            "cwd": str(project_root),
            "version": "0.4.7",
            "release_date": "",
            "usage": usage or self._usage(),
        }

    @staticmethod
    def _bounded_cycles(value: Any, maximum: int) -> int:
        return max(1, min(int(value or 1), maximum))

    def _command_cycles(self, text: str, default: int, maximum: int) -> int:
        parts = text.split()
        if len(parts) < 2:
            return default
        try:
            return self._bounded_cycles(parts[1], maximum=maximum)
        except ValueError:
            return default

    def _model_name(self) -> str:
        remote = self.runtime.adapters.get("remote_llm")
        return str(getattr(remote, "model", "local-runtime"))

    def _usage(self) -> dict[str, Any]:
        text = "\n".join(str(item.get("text", "")) for item in self.history)
        total = max(1, len(text) // 4)
        return {
            "input": total,
            "output": 0,
            "total": total,
            "cost_usd": 0.0,
            "context_used": total,
            "context_max": 128000,
            "context_percent": round(total / 128000 * 100, 2),
        }

    def _estimate_usage(self, prompt: str, response: str) -> dict[str, Any]:
        input_tokens = max(1, len(prompt) // 4)
        output_tokens = max(1, len(response) // 4)
        return {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
            "cost_usd": 0.0,
            "context_used": input_tokens + output_tokens,
            "context_max": 128000,
            "context_percent": round((input_tokens + output_tokens) / 128000 * 100, 2),
        }

    def _format_status(self) -> str:
        snapshot = self.runtime.status_snapshot()
        services = ", ".join(f"{name}={status}" for name, status in snapshot["services"].items())
        return (
            f"会话：{self.session_id}\n"
            f"模型：{self._model_name()}\n"
            f"工作目录：{project_root}\n"
            f"服务：{services}"
        )

    def _format_runtime_health(self) -> str:
        report = self.runtime.health_report()
        adapters = ", ".join(
            f"{name}={details.get('status', 'unknown')}"
            for name, details in report["adapters"].items()
        )
        services = ", ".join(
            f"{name}={status}"
            for name, status in report["runtime"]["services"].items()
        )
        return f"运行时\n服务：{services}\n适配器：{adapters}"

    def _format_preflight(self) -> str:
        report = self.runtime.preflight_report()
        summary = report["summary"]
        attention = ", ".join(summary.get("attention", [])) or "无"
        return (
            "预检\n"
            f"状态：{summary['status']}\n"
            f"蓝图：{summary['blueprint_count']}\n"
            f"关注项：{attention}"
        )

    def _format_host_probe(self) -> str:
        report = self.runtime.host_integration_probe()
        lines = [f"宿主机：{report['summary']['status']}"]
        for name, details in report["tools"].items():
            lines.append(f"- {name}: {details.get('status')}")
        return "\n".join(lines)

    def _format_messaging(self) -> str:
        status = self.runtime.messaging_gateway_status()
        platforms = ", ".join(status.get("platforms", [])) or "无"
        return f"通讯：{status['status']}\n平台：{platforms}"

    def _format_blueprints(self) -> str:
        blueprints = self.runtime.list_agent_blueprints()
        if not blueprints:
            return "智能体蓝图\n暂无智能体蓝图。"
        return "智能体蓝图\n" + "\n".join(
            f"- {item.get('role_name', 'unknown')} v{item.get('version', '')}"
            for item in blueprints
        )

    def _format_skills(self) -> str:
        skills = self.runtime.list_published_skills()
        if not skills:
            return "技能\n暂无已发布技能。"
        return "技能\n" + "\n".join(
            f"- {item.get('metadata', {}).get('name', item.get('path', 'unknown'))}"
            for item in skills
        )

    def _format_algorithms(self) -> str:
        algorithms = self.runtime.list_algorithms()
        experiments = self.runtime.list_algorithm_experiment_reports()
        reviews = self.runtime.list_algorithm_reviews()
        return (
            "算法\n"
            f"注册表：{len(algorithms)}\n"
            f"实验：{len(experiments)}\n"
            f"评审：{len(reviews)}"
        )

    def _format_audits(self) -> str:
        skill = self.runtime.read_skill_lifecycle_audit()
        algorithm = self.runtime.read_algorithm_evolution_audit()
        return (
            "审计\n"
            f"skill_lifecycle：{len(skill)} 条记录\n"
            f"algorithm_evolution：{len(algorithm)} 条记录"
        )

    def _format_avatar(self) -> str:
        event = self.runtime.get_latest_avatar_event()
        return (
            "形象\n"
            f"情绪：{event.get('emotion', 'unknown')}\n"
            f"动画：{event.get('animation', 'unknown')}\n"
            f"文本：{event.get('text', '')}"
        )

    def _format_events(self) -> str:
        events = self.runtime.event_bus.list_events()[-10:]
        if not events:
            return "事件\n暂无运行事件。"
        lines = ["事件"]
        for event in events:
            lines.append(f"- {event.event_type} from {event.source_agent}")
        return "\n".join(lines)

    def _format_terminal_ui(self) -> str:
        status = self.runtime.terminal_ui_status()
        missing = ", ".join(status.get("missing", [])) or "无"
        return f"终端界面：{status['status']}\n缺失：{missing}"

    @staticmethod
    def _format_smoke(report: dict[str, Any]) -> str:
        summary = report["summary"]
        failures = ", ".join(summary.get("failures", [])) or "无"
        return (
            "运行冒烟检查\n"
            f"状态：{summary['status']}\n"
            f"轮次：{summary['cycles']}\n"
            f"失败：{failures}\n"
            f"路径：{report.get('path', '')}"
        )

    @staticmethod
    def _format_stress(report: dict[str, Any]) -> str:
        failures = ", ".join(report.get("failures", [])) or "无"
        return (
            "交互压力检查\n"
            f"状态：{report['status']}\n"
            f"轮次：{report['cycles']}\n"
            f"失败：{failures}"
        )

    def _format_approvals(self) -> str:
        requests = self.runtime.governance.list_requests()
        if not requests:
            return "暂无审批请求。"
        lines = []
        for request in requests:
            lines.append(
                f"{request.request_id} [{request.status}] {request.title} "
                f"({request.request_type}, risk={request.risk_level})"
            )
        return "\n".join(lines)

    def _format_tools(self) -> str:
        services = self.runtime.status_snapshot()["services"]
        lines = ["运行时服务"]
        lines.extend(f"- {name}: {status}" for name, status in services.items())
        lines.append("")
        lines.append("自然语言后端工具")
        for method in sorted(TOOL_POLICIES):
            policy = self._tool_policy(method)
            required = policy.get("input_schema", {}).get("required", [])
            required_text = ", ".join(required) if required else "无"
            approval = "是" if self._tool_requires_approval(method, policy) else "否"
            retry = policy.get("retry", {})
            lines.append(
                f"- {method} | 鉴权={policy.get('auth_scope')} | "
                f"风险={policy.get('risk_level')} | 审批={approval} | "
                f"重试={retry.get('max_attempts', 1)}"
            )
            lines.append(f"  必填参数：{required_text}")
        lines.append("")
        lines.append("可用自然语言调用：")
        lines.append('run backend shell.exec params={"command":"python --version"}')
        lines.append('run backend runtime.final_acceptance params={"stress_cycles":1}')
        lines.append("show adapter health")
        lines.append("批准最新请求")
        lines.append("")
        lines.append("缺少必填参数时会触发补充信息提示。")
        lines.append("语音输入使用同一个自然语言工具网关。")
        return "\n".join(lines)

    def _help_text(self) -> str:
        commands = "\n".join(f"{item['text']} - {item['meta']}" for item in SLASH_COMMANDS)
        return (
            "终端界面命令\n"
            f"{commands}\n\n"
            "快捷键：Enter 提交，Shift/Alt+Enter 换行，Tab 补全，"
            "上下方向键切换历史或补全项，Ctrl+C 中断/清空/退出。"
        )

    @staticmethod
    def _chunks(text: str, size: int) -> list[str]:
        if not text:
            return [""]
        return [text[index : index + size] for index in range(0, len(text), size)]


async def main() -> None:
    server = JSONRPCServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
