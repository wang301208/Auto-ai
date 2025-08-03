from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import yaml


def export_prompt_config(workspace: Path) -> None:
    """Serialize current prompt settings to YAML in the population directory.

    The export is best-effort; failures are logged but do not raise.
    """
    try:
        prompt_file = workspace / "prompt_settings.yaml"
        if not prompt_file.exists():
            return

        data = yaml.safe_load(prompt_file.read_text())

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        out_dir = workspace / "evolve_strategies" / "population" / "incoming"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"selfmod_{timestamp}.yaml"
        with out_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)
    except Exception as err:  # pragma: no cover - best effort
        logging.getLogger(__name__).error(
            "Failed to export prompt config: %s", err, exc_info=True
        )
