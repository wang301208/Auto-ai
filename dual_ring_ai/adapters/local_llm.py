"""Local, network-free language adapter for interaction responses."""

from __future__ import annotations

from typing import Any


class LocalLLMAdapter:
    """Rule-based local fallback for persona-shaped responses."""

    def __init__(self, persona: str = "calm_architect") -> None:
        self.persona = persona

    def generate_response(
        self,
        user_text: str,
        backend_payload: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        payload = backend_payload or {}
        fragments: list[str] = []

        if "services" in payload:
            services = payload.get("services", {})
            if "governance" in services:
                fragments.append(f"治理服务状态为 {services['governance']}")
            fragments.append(f"共有 {len(services)} 个后端服务可用。")
        if "approvals" in payload:
            approvals = payload.get("approvals", [])
            statuses = ", ".join(
                str(item.get("status", "unknown")) for item in approvals
            )
            fragments.append(f"审批队列状态：{statuses or 'empty'}")
        if not fragments:
            fragments.append(f"已收到请求：{user_text}")

        return {
            "provider": "local_rule_based",
            "persona": self.persona,
            "text": "；".join(fragments),
            "emotion": "focused",
            "action": "explain",
        }
