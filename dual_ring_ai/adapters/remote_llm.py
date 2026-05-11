"""Remote OpenAI-compatible LLM adapter with live defaults and local fallback."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .local_llm import LocalLLMAdapter


@dataclass
class RemoteLLMAdapter:
    """Small HTTP boundary for remote OpenAI-compatible chat models."""

    enabled: bool = True
    dry_run: bool = False
    api_key: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout: float = 30.0
    temperature: float = 0.2
    max_tokens: int | None = None
    system_prompt: str = (
        "You are the remote reasoning engine for the local autonomous runtime. "
        "Answer concisely and preserve safety boundaries. "
        "Do not claim abilities that are not exposed in backend context. "
        "Do not say the system can perform advanced operations unless the backend context "
        "shows the exact tool is available and executable. "
        "If computer_control or software_management is false or absent, say that only "
        "shell-level command execution is available and native computer_control/software "
        "actions are not implemented."
    )

    @property
    def provider(self) -> str:
        return "remote_openai_compatible"

    def probe(self) -> dict[str, Any]:
        """Check remote LLM readiness without sending prompts."""
        url = self._url("models")
        if not self.enabled:
            return {
                "status": "disabled",
                "provider": self.provider,
                "url": url,
                "model": self.model,
                "reason": "Remote LLM is disabled.",
            }
        if self.dry_run:
            return {
                "status": "dry_run",
                "provider": self.provider,
                "url": url,
                "model": self.model,
            }
        if not self._resolved_api_key():
            return {
                "status": "unconfigured",
                "provider": self.provider,
                "url": url,
                "model": self.model,
                "reason": f"{self.api_key_env} is not configured.",
            }

        request = urllib.request.Request(url, headers=self._auth_headers())
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8") or "{}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return {
                "status": "unavailable",
                "provider": self.provider,
                "url": url,
                "model": self.model,
                "reason": str(exc),
            }
        return {
            "status": "available",
            "provider": self.provider,
            "url": url,
            "model": self.model,
            "model_count": len(payload.get("data", [])),
        }

    def generate_response(
        self,
        user_text: str,
        backend_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a persona-shaped response through a remote chat endpoint."""
        payload = {
            "model": self.model,
            "messages": self._messages(user_text, backend_payload or {}),
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        request_shape = {
            "method": "POST",
            "url": self._url("chat/completions"),
            "headers": self._masked_headers(),
            "json": payload,
        }
        if not self.enabled:
            return self._response(
                status="disabled",
                text="Remote LLM is disabled.",
                reason="Remote LLM is disabled.",
            )
        if self.dry_run:
            return self._response(
                status="dry_run",
                text="Remote LLM dry-run request prepared.",
                request=request_shape,
            )
        if not self._resolved_api_key():
            return self._response(
                status="unconfigured",
                text=f"Remote LLM is not configured: {self.api_key_env} is missing.",
                reason=f"{self.api_key_env} is not configured.",
            )

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            request_shape["url"],
            data=data,
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8") or "{}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return self._response(
                status="unavailable",
                text=f"Remote LLM request failed: {exc}",
                reason=str(exc),
                request=request_shape,
            )

        text = self._extract_text(response_payload)
        return self._response(
            status="completed",
            text=text,
            payload=response_payload,
            request=request_shape,
        )

    def _messages(self, user_text: str, backend_payload: dict[str, Any]) -> list[dict[str, str]]:
        context = json.dumps(
            backend_payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"Backend context: {context}"},
            {"role": "user", "content": user_text},
        ]

    def _response(self, status: str, text: str, **extra: Any) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": status,
            "text": text,
            "emotion": "focused",
            "action": "explain",
            **extra,
        }

    def _extract_text(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices", [])
        if not choices:
            return ""
        first = choices[0]
        message = first.get("message", {})
        content = message.get("content", "")
        return str(content or "")

    def _resolved_api_key(self) -> str | None:
        return self.api_key or os.getenv(self.api_key_env)

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._resolved_api_key()}"}

    def _masked_headers(self) -> dict[str, str]:
        token = "***" if self._resolved_api_key() else "<missing>"
        return {"Authorization": f"Bearer {token}"}

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"


class HybridLLMAdapter:
    """Use remote LLM when available; otherwise stay local."""

    def __init__(
        self,
        remote: RemoteLLMAdapter,
        local: LocalLLMAdapter | None = None,
    ) -> None:
        self.remote = remote
        self.local = local or LocalLLMAdapter()

    def generate_response(
        self,
        user_text: str,
        backend_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.remote.enabled:
            return self.local.generate_response(user_text, backend_payload)

        response = self.remote.generate_response(user_text, backend_payload)
        if response.get("status") in {"unconfigured", "unavailable", "disabled"}:
            fallback = self.local.generate_response(user_text, backend_payload)
            fallback["remote_llm_status"] = response
            return fallback
        return response
