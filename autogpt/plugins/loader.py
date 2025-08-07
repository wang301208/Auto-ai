from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from autogpt.plugins.models import PluginMeta, PluginMetaValidationError


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

    # Resolve the referenced source path. If a relative path is provided it is
    # interpreted relative to the metadata file's directory so that specs can be
    # relocated without breaking their source references.
    source_path = Path(meta.underlying_library.local_source_path).expanduser()
    if not source_path.is_absolute():
        source_path = (metadata_path.parent / source_path).resolve()

    if not source_path.exists():
        raise PluginMetaValidationError(
            f"local_source_path '{meta.underlying_library.local_source_path}' does not exist"
        )

    # Store the resolved absolute path so consumers always receive a concrete
    # filesystem location.
    meta.underlying_library.local_source_path = str(source_path)

    return meta
