"""本地智能体终端运行时命令入口。"""

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
        description="本地智能体终端运行时",
    )
    parser.add_argument("--config", help="config.yaml 或 agent_config.json 路径")
    parser.add_argument("--tui", action="store_true", help="启动终端界面")
    parser.add_argument("--continue", dest="resume", action="store_true", help="启动后打开会话选择器")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("tui", help="启动终端界面")

    setup = subparsers.add_parser("setup", help="创建 config.yaml 和可选 .env")
    setup.add_argument("--config", help="要写入的 config.yaml 路径")
    setup.add_argument("--provider", default="openai")
    setup.add_argument("--model", default="")
    setup.add_argument("--api-key", default="")
    setup.add_argument("--api-key-env", default="")
    setup.add_argument("--base-url", default="")
    setup.add_argument("--auth-type", default="api_key")
    setup.add_argument("--dry-run", action="store_true")

    model = subparsers.add_parser("model", help="显示或切换当前模型")
    model.add_argument("spec", nargs="?", help="provider:model，例如 openai:gpt-4o-mini")
    model.add_argument("--config", help="config.yaml 或 agent_config.json 路径")

    doctor = subparsers.add_parser("doctor", help="检查本地运行时就绪状态")
    doctor.add_argument("--config", help="config.yaml 或 agent_config.json 路径")

    providers = subparsers.add_parser("providers", help="列出模型提供商")
    providers.add_argument("--config", help="config.yaml 或 agent_config.json 路径")
    return parser


def run_tui(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    env.setdefault("LANG", "zh_CN.UTF-8")
    env.setdefault("LC_ALL", "zh_CN.UTF-8")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
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
    print(f"设置完成：{result['provider']}:{result['model']}")
    print(f"配置文件：{result['config_path']}")
    if result.get("env_path"):
        print(f"环境文件：{result['env_path']}")
    return 0


async def run_model(args: argparse.Namespace) -> int:
    server = JSONRPCServer(config_path=getattr(args, "config", None), writer=lambda _: None)
    if args.spec:
        spec_dict = server.parse_model_spec(args.spec)
        result = await server.handle_model_configure(spec_dict)
        print(f"模型已配置：{result['provider']}:{result['model']}")
        return 0
    print(server.format_model_status())
    return 0


async def run_doctor(args: argparse.Namespace) -> int:
    server = JSONRPCServer(config_path=getattr(args, "config", None), writer=lambda _: None)
    health = await server.handle_runtime_health({})
    preflight = await server.handle_runtime_preflight({})
    providers = await server.handle_model_options({})
    print("运行时检查")
    print(f"运行时：{health.get('runtime', {}).get('status', 'ready') if isinstance(health, dict) else 'ready'}")
    print(f"模型：{providers.get('provider')}:{providers.get('model')}")
    gates = preflight.get("gates", {}) if isinstance(preflight, dict) else {}
    print(f"检查门：{len(gates)}")
    return 0


async def run_providers(args: argparse.Namespace) -> int:
    server = JSONRPCServer(config_path=getattr(args, "config", None), writer=lambda _: None)
    result = await server.handle_model_providers({})
    for provider in result["providers"]:
        print(f"{provider['slug']}\t{provider['name']}\t{', '.join(provider.get('models', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
