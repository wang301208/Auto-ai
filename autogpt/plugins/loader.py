from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from autogpt.plugins.models import (
    PluginMeta,
    PluginMetaValidationError,
)


def load_plugin_meta(path: str | Path) -> PluginMeta:
    """Load and validate plugin metadata from ``path``.

    Args:
        path: Path to a JSON metadata file.

    Returns:
        Parsed :class:`PluginMeta` instance.

    Raises:
        PluginMetaValidationError: If the metadata is missing required
            fields, has invalid values, or references a non-existent
            ``local_source_path``.
    """

    metadata_path = Path(path)
    try:
        raw = metadata_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise PluginMetaValidationError(f"Metadata file '{path}' not found") from e

    try:
        data: dict[str, Any] = json.loads(raw)
        meta = PluginMeta.parse_obj(data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise PluginMetaValidationError(f"Invalid plugin metadata: {e}") from e

    source_path = Path(meta.underlying_library.local_source_path).expanduser()
    if not source_path.exists():
        raise PluginMetaValidationError(
            f"local_source_path '{meta.underlying_library.local_source_path}' does not exist"
        )

    return meta
