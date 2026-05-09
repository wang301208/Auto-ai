"""Ollama adapter boundary with live defaults and dry-run support."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class OllamaAdapter:
    """Small HTTP boundary for a local Ollama daemon.

    The adapter is enabled by default. Dry-run mode returns the exact request
    shape without opening a socket.
    """

    enabled: bool = True
    dry_run: bool = False
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.1"
    timeout: float = 10.0

    def probe(self) -> dict[str, Any]:
        """Check whether Ollama is available."""
        url = f"{self.base_url.rstrip('/')}/api/tags"
        if not self.enabled:
            return {"status": "disabled", "url": url, "reason": "Ollama is disabled."}
        if self.dry_run:
            return {"status": "dry_run", "url": url}

        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8") or "{}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return {"status": "unavailable", "url": url, "reason": str(exc)}
        return {"status": "available", "url": url, "payload": payload}

    def generate(self, prompt: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate a response from a local Ollama model when explicitly enabled."""
        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options

        request_shape = {
            "method": "POST",
            "url": url,
            "json": payload,
        }
        if not self.enabled:
            return {
                "status": "disabled",
                "reason": "Ollama is disabled.",
                "request": request_shape,
            }
        if self.dry_run:
            return {"status": "dry_run", "request": request_shape}

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8") or "{}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return {
                "status": "unavailable",
                "reason": str(exc),
                "request": request_shape,
            }
        return {
            "status": "completed",
            "text": str(response_payload.get("response", "")),
            "payload": response_payload,
            "request": request_shape,
        }
