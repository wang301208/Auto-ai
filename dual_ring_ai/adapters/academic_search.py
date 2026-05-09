"""Academic search adapter boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AcademicSearchResults:
    provider: str
    query: str
    items: list[dict[str, Any]]
    message: str


class AcademicSearchAdapter:
    """Optional academic search integration.

    The adapter returns a clear disabled status until a provider is configured.
    """

    def __init__(
        self,
        provider: str | None = None,
        fixture_path: str | Path | None = None,
    ) -> None:
        self.provider = provider
        self.fixture_path = Path(fixture_path) if fixture_path else None

    def search(self, query: str, limit: int = 5) -> AcademicSearchResults:
        if not self.provider:
            return AcademicSearchResults(
                provider="disabled",
                query=query,
                items=[],
                message="Academic search provider not configured.",
            )
        if self.provider == "local":
            items: list[dict[str, Any]] = []
            if self.fixture_path is not None and self.fixture_path.exists():
                items = json.loads(self.fixture_path.read_text(encoding="utf-8"))
            return AcademicSearchResults(
                provider="local",
                query=query,
                items=items[:limit],
                message="Loaded local academic search fixture.",
            )
        return AcademicSearchResults(
            provider=self.provider,
            query=query,
            items=[],
            message=f"Provider {self.provider} adapter is configured but not implemented.",
        )
