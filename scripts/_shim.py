"""Legacy script shims for backward compatibility.

Each shim prints a deprecation warning and forwards to the
corresponding `aai` subcommand. These allow existing CI pipelines
and shell scripts to continue working during migration.

Remove after deprecation period (e.g. 2 minor releases).
"""

import os
import subprocess
import sys
import warnings

_LEGACY_MAP = {
    "run_orchestrator.py": ["orchestrate", "start"],
    "run_blueprint_orchestrator.py": ["orchestrate", "blueprint"],
    "run_executor.py": ["orchestrate", "execute"],
    "librarian_cli.py": ["skill"],
    "skill_cli.py": ["skill"],
    "launch_tui.py": ["tui"],
    "test_tui.py": ["doctor"],
    "approve_fix.py": ["governance", "approve"],
    "data_ingestion.py": ["ingest"],
    "auto_evolve.py": ["evolve", "run"],
    "simple_evolution.py": ["evolve", "run"],
    "seed_population.py": ["evolve", "seed"],
}


def run_shim(legacy_name: str) -> None:
    """Execute a legacy script by forwarding to the unified CLI."""
    if legacy_name not in _LEGACY_MAP:
        print(f"Unknown legacy script: {legacy_name}", file=sys.stderr)
        sys.exit(1)

    target = _LEGACY_MAP[legacy_name]
    warnings.warn(
        f"scripts/{legacy_name} is deprecated. "
        f"Use 'aai {' '.join(target)}' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    aai_args = target + sys.argv[1:]
    result = subprocess.run(
        [sys.executable, "-m", "autoai"] + aai_args,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    script_name = os.path.basename(sys.argv[0])
    run_shim(script_name)
