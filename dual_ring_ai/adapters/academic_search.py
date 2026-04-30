"""Academic search adapter boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AcademicSearchResults:
    provider: str
    query: str
    items: list[dict[str, Any]]
    message: str


class AcademicSearchAdapter:
    """Optional academic search integration.

    The default adapter is deliberately disabled so tests and local runs never
    perform unintended network access.
    """

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider

    def search(self, query: str, limit: int = 5) -> AcademicSearchResults:
        if not self.provider:
            return AcademicSearchResults(
                provider="disabled",
                query=query,
                items=[],
                message="Academic search provider not configured.",
            )
        return AcademicSearchResults(
            provider=self.provider,
            query=query,
            items=[],
            message=f"Provider {self.provider} adapter is configured but not implemented.",
        )
