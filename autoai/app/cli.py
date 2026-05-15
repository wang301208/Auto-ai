"""autoai包的主脚本。"""
import importlib.util
import sys
from pathlib import Path
from typing import Optional

import click

from .i18n import _


def _check_python_version() -> None:
    """确保运行的Python版本受支持。"""
    if sys.version_info < (3, 12):
        raise click.ClickException(_("Python 3.12 or higher is required to run AutoAI."))


def _require_packages(packages: tuple[str, ...]) -> None:
    """验证所需包是否已安装。"""
    missing = [p for p in packages if importlib.util.find_spec(p) is None]
    if missing:
        raise click.ClickException(_("Required packages missing: ") + ", ".join(missing))


@click.group(invoke_without_command=True, help=_("Start an Auto-AI assistant."))
@click.option("-c", "--continuous", is_flag=True, help=_("Enable Continuous Mode"))
@click.option(
    "--skip-reprompt",
    "-y",
    is_flag=True,
    help=_("Skips the re-prompting messages at the beginning of the script"),
)
@click.option(
    "--ai-settings",
    "-C",
    help=_(
        "Specifies which ai_settings.yaml file to use, relative to the Auto-AI root directory. Will also automatically skip the re-prompt."
    ),
)
@click.option(
    "--prompt-settings",
    "-P",
    help=_("Specifies which prompt_settings.yaml file to use."),
)
@click.option(
    "-l",
    "--continuous-limit",
    type=int,
    help=_("Defines the number of times to run in continuous mode"),
)
@click.option("--speak", is_flag=True, help=_("Enable Speak Mode"))
@click.option("--debug", is_flag=True, help=_("Enable Debug Mode"))
@click.option("--gpt3only", is_flag=True, help=_("Enable GPT3.5 Only Mode"))
@click.option("--gpt4only", is_flag=True, help=_("Enable GPT4 Only Mode"))
@click.option(
    "--use-memory",
    "-m",
    "memory_type",
    type=str,
    help=_("Defines which Memory backend to use"),
)
@click.option(
    "-b",
    "--browser-name",
    help=_("Specifies which web-browser to use when using selenium to scrape the web."),
)
@click.option(
    "--allow-downloads",
    is_flag=True,
    help=_("Dangerous: Allows Auto-AI to download files natively."),
)
@click.option(
    "--skip-news",
    is_flag=True,
    help=_("Specifies whether to suppress the output of latest news on startup."),
)
@click.option(
    "--working-directory",
    type=click.Path(
        exists=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
    default=Path(__file__).parent.parent.parent,
    show_default=True,
    help=_("Sets the working directory for Auto-AI."),
)
@click.option(
    "--workspace-directory",
    "-w",
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    help=_("Path to the workspace directory. Defaults to 'auto_ai_workspace' inside the working directory."),
)
@click.option(
    "--install-plugin-deps",
    is_flag=True,
    help=_("Installs external dependencies for 3rd party plugins."),
)
@click.option(
    "--ai-name",
    type=str,
    help=_("AI name override"),
)
@click.option(
    "--ai-role",
    type=str,
    help=_("AI role override"),
)
@click.option(
    "--ai-goal",
    type=str,
    multiple=True,
    help=_("AI goal override; may be used multiple times to pass multiple goals"),
)
@click.option(
    "--lang",
    "language",
    type=str,
    default=None,
    help=_("Set terminal language (e.g. zh, en)"),
)
@click.option(
    "--async-mode",
    "async_mode",
    is_flag=True,
    help=_("Enable async execution mode (merged V1+V2 architecture)"),
)
@click.option(
    "--autonomous",
    "autonomous",
    is_flag=True,
    default=True,
    help=_("Autonomous mode is the DEFAULT. Agent runs without human approval."),
)
@click.option(
    "--supervised",
    "supervised",
    is_flag=True,
    help=_("DOWNGRADE to supervised mode (L1). Use this if you want human oversight."),
)
@click.option(
    "--multi-agent",
    "multi_agent",
    is_flag=True,
    help=_("Enable multi-agent coordination mode with workflow orchestration"),
)
@click.pass_context
def main(
    ctx: click.Context,
    continuous: bool,
    continuous_limit: int,
    ai_settings: str,
    prompt_settings: str,
    skip_reprompt: bool,
    speak: bool,
    debug: bool,
    gpt3only: bool,
    gpt4only: bool,
    memory_type: str,
    browser_name: str,
    allow_downloads: bool,
    skip_news: bool,
    working_directory: Path,
    workspace_directory: Path | None,
    install_plugin_deps: bool,
    ai_name: Optional[str],
    ai_role: Optional[str],
    ai_goal: tuple[str],
    language: Optional[str],
    async_mode: bool,
    autonomous: bool,
    supervised: bool,
    multi_agent: bool,
) -> None:
    """
    Welcome to AutoAI an experimental open-source application showcasing the capabilities of the GPT-4 pushing the boundaries of AI.

    Start an Auto-AI assistant.
    """
    _check_python_version()
    _require_packages(("openai",))

    from autoai.app.i18n import init_locale
    init_locale(language)

    from autoai.app.main import run_auto_ai

    if supervised:
        autonomous = False

    if ctx.invoked_subcommand is None:
        run_auto_ai(
            continuous=continuous,
            continuous_limit=continuous_limit,
            ai_settings=ai_settings,
            prompt_settings=prompt_settings,
            skip_reprompt=skip_reprompt,
            speak=speak,
            debug=debug,
            gpt3only=gpt3only,
            gpt4only=gpt4only,
            memory_type=memory_type,
            browser_name=browser_name,
            allow_downloads=allow_downloads,
            skip_news=skip_news,
            working_directory=working_directory,
            workspace_directory=workspace_directory,
            install_plugin_deps=install_plugin_deps,
            ai_name=ai_name,
            ai_role=ai_role,
            ai_goals=ai_goal,
            async_mode=async_mode,
            autonomous=autonomous,
            multi_agent=multi_agent,
        )


# ======================================================================
# 注册 unified command groups from autoai.app.commands
# ======================================================================

from .commands import (  # noqa: E402
    skill,
    orchestrate,
    evolve,
    ingest,
    tui,
    plugin,
    governance,
    model,
    dashboard,
    doctor,
    dependency_audit,
    memory,
    mesh,
    events,
    safety,
    autonomy,
    dream,
    reasoning,
    matrix,
)

main.add_command(skill)
main.add_command(orchestrate)
main.add_command(evolve)
main.add_command(ingest)
main.add_command(tui)
main.add_command(plugin)
main.add_command(governance)
main.add_command(model)
main.add_command(dashboard)
main.add_command(doctor)
main.add_command(dependency_audit)
main.add_command(memory)
main.add_command(mesh)
main.add_command(events)
main.add_command(safety)
main.add_command(autonomy)
main.add_command(dream)
main.add_command(reasoning)
main.add_command(matrix)


@main.command("stop", help=_("Stop running Agent process. Human can only stop, not intervene in boundaries."))
@click.option("--pid", "pid", default=None, type=int, help=_("Process ID to stop"))
@click.option("--force", is_flag=True, help=_("Force kill (SIGKILL)"))
def stop(pid: int | None, force: bool) -> None:
    """Stop a running Agent. This is the ONLY human runtime intervention allowed.

    Humans cannot adjust boundaries, approve operations, or change autonomy levels.
    They can only terminate the process and re-issue a new goal.
    """
    import os
    import signal

    pid_file = Path("autoai.pid")
    if pid is None:
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
            except (ValueError, OSError):
                pass

    if pid is None:
        raise click.ClickException(_("No Agent process found. Use --pid to specify."))

    try:
        sig = signal.SIGKILL if force else signal.SIGTERM
        os.kill(pid, sig)
        click.echo(f"Sent {'SIGKILL' if force else 'SIGTERM'} to process {pid}")
        if pid_file.exists():
            pid_file.unlink()
    except ProcessLookupError:
        click.echo(f"Process {pid} not found (already terminated)")
        if pid_file.exists():
            pid_file.unlink()
    except PermissionError:
        raise click.ClickException(f"Permission denied to stop process {pid}")


@main.command("kill-all", help=_("EMERGENCY: Kill ALL AutoAI processes. The ONLY hardcoded safety switch."))
def kill_all() -> None:
    """HARDCODED EMERGENCY CIRCUIT BREAKER.

    This is the ONE thing that can never be modified by any Agent at any autonomy level.
    It terminates ALL running AutoAI processes immediately.

    This command is NOT subject to:
      - Policy engine rules
      - Autonomy level restrictions
      - Boundary manager constraints
      - Democratic governance votes
      - Any Agent self-modification

    It is the absolute last resort for human safety override.
    """
    import os
    import signal
    import subprocess

    killed = 0
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "autoai" in line.lower() or "python -m autoai" in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        target_pid = int(parts[1])
                        if target_pid != os.getpid():
                            os.kill(target_pid, signal.SIGKILL)
                            killed += 1
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
    except Exception:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "python" in line.lower():
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        try:
                            target_pid = int(parts[1])
                            if target_pid != os.getpid():
                                subprocess.run(
                                    ["taskkill", "/F", "/PID", str(target_pid)],
                                    capture_output=True, timeout=5,
                                )
                                killed += 1
                        except (ValueError, subprocess.TimeoutExpired):
                            pass
        except Exception as e:
            raise click.ClickException(f"Failed to kill processes: {e}")

    pid_file = Path("autoai.pid")
    if pid_file.exists():
        pid_file.unlink()

    click.echo(f"EMERGENCY SHUTDOWN: Killed {killed} AutoAI process(es)")
    click.echo("This is the ONLY hardcoded safety switch. It cannot be overridden by any Agent.")


@main.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    help=_("Run AlphaEvolve workflows."),
)
@click.pass_context
def alphaevolve(ctx: click.Context) -> None:
    """运行AlphaEvolve工作流。"""
    _require_packages(("flask",))
    from openevolve import cli as oe_cli

    # 转发 remaining arguments to the original AlphaEvolve CLI
    sys.argv = ["alphaevolve", *ctx.args]
    exit_code = oe_cli.main()
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
