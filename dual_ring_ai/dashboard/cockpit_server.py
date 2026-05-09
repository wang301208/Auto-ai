"""Entrypoint used by the local Cockpit uvicorn script."""

from __future__ import annotations

import os
from pathlib import Path

from ..runtime.local_runtime import LocalRuntime, LocalRuntimeConfig
from .cockpit_api import create_cockpit_app


config_path = os.getenv("DUAL_RING_CONFIG_PATH")
if config_path:
    runtime = LocalRuntime.from_config_file(config_path)
else:
    runtime_root = Path(os.getenv("DUAL_RING_RUNTIME_ROOT", ".dual_ring_runtime"))
    runtime = LocalRuntime(LocalRuntimeConfig(root_path=runtime_root, enable_agents=False))
runtime.start()
app = create_cockpit_app(runtime)
