"""Command line entrypoint for the local agent terminal runtime."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .entry import JSONRPCServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {None, "tui"}:
        return run_tui(args)
    if args.command == "setup":
        return asyncio.run(run_setup(args))
    if args.command == "model":
        return asyncio.run(run_model(args))
    if args.command == "doctor":
        return asyncio.run(run_doctor(args))
    if args.command == "providers":
        return asyncio.run(run_providers(args))
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-agent",
        description="Local Agent terminal runtime",
    )
    parser.add_argument("--config", help="Path to config.yaml or agent_config.json")
    parser.add_argument("--tui", action="store_true", help="Launch the terminal UI")
    parser.add_argument("--continue", dest="resume", action="store_true", help="Open the session picker after launch")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("tui", help="Launch the terminal UI")

    setup = subparsers.add_parser("setup", help="Create config.yaml and optional .env")
    setup.add_argument("--config", help="Path to write config.yaml")
    setup.add_argument("--provider", default="openai")
    setup.add_argument("--model", default="")
    setup.add_argument("--api-key", default="")
    setup.add_argument("--api-key-env", default="")
    setup.add_argument("--base-url", default="")
    setup.add_argument("--auth-type", default="api_key")
    setup.add_argument("--dry-run", action="store_true")

    model = subparsers.add_parser("model", help="Show or change the active model")
    model.add_argument("spec", nargs="?", help="provider:model, for example openai:gpt-4o-mini")
    model.add_argument("--config", help="Path to config.yaml or agent_config.json")

    doctor = subparsers.add_parser("doctor", help="Check local runtime readiness")
    doctor.add_argument("--config", help="Path to config.yaml or agent_config.json")

    providers = subparsers.add_parser("providers", help="List model providers")
    providers.add_argument("--config", help="Path to config.yaml or agent_config.json")
    return parser


def run_tui(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    if getattr(args, "config", None):
        env["LOCAL_AGENT_CONFIG_PATH"] = str(Path(args.config).resolve())
    ui_dir = PROJECT_ROOT / "ui-tui"
    entry = ui_dir / "dist" / "entry.js"
    if not entry.exists():
        subprocess.run(["npm", "install"], cwd=ui_dir, check=True)
        subprocess.run(["npm", "run", "build"], cwd=ui_dir, check=True)
    return subprocess.run(["node", str(entry)], cwd=ui_dir, env=env).returncode


async def run_setup(args: argparse.Namespace) -> int:
    server = JSONRPCServer(config_path=getattr(args, "config", None), writer=lambda _: None)
    payload: dict[str, Any] = {
        "provider": args.provider,
        "auth_type": args.auth_type,
        "dry_run": bool(args.dry_run),
    }
    if args.model:
        payload["model"] = args.model
    if args.api_key:
        payload["api_key"] = args.api_key
    if args.api_key_env:
        payload["api_key_env"] = args.api_key_env
    if args.base_url:
        payload["base_url"] = args.base_url
    result = await server.handle_model_setup(payload)
    print(f"Setup complete: {result['provider']}:{result['model']}")
    print(f"Config: {result['config_path']}")
    if result.get("env_path"):
        print(f"Env: {result['env_path']}")
    return 0


async def run_model(args: argparse.Namespace) -> int:
    server = JSONRPCServer(config_path=getattr(args, "config", None), writer=lambda _: None)
    if args.spec:
        result = await server.handle_model_configure(server._parse_model_spec(args.spec))
        print(f"Model configured: {result['provider']}:{result['model']}")
        return 0
    print(server._format_model_status())
    return 0


async def run_doctor(args: argparse.Namespace) -> int:
    server = JSONRPCServer(config_path=getattr(args, "config", None), writer=lambda _: None)
    health = await server.handle_runtime_health({})
    preflight = await server.handle_runtime_preflight({})
    providers = await server.handle_model_options({})
    print("Doctor checks")
    print(f"Runtime: {health.get('runtime', {}).get('status', 'ready') if isinstance(health, dict) else 'ready'}")
    print(f"Model: {providers.get('provider')}:{providers.get('model')}")
    gates = preflight.get("gates", {}) if isinstance(preflight, dict) else {}
    print(f"Gates: {len(gates)}")
    return 0


async def run_providers(args: argparse.Namespace) -> int:
    server = JSONRPCServer(config_path=getattr(args, "config", None), writer=lambda _: None)
    result = await server.handle_model_providers({})
    for provider in result["providers"]:
        print(f"{provider['slug']}\t{provider['name']}\t{', '.join(provider.get('models', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
