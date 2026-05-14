"""Main script for the autoai package."""
import importlib.util
import sys
from pathlib import Path
from typing import Optional

import click

from .i18n import _


def _check_python_version() -> None:
    """Ensure the running Python version is supported."""
    if sys.version_info < (3, 12):
        raise click.ClickException(_("Python 3.12 or higher is required to run AutoAI."))


def _require_packages(packages: tuple[str, ...]) -> None:
    """Verify that required packages are installed."""
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
    help=_("Enable fully autonomous self-improvement mode (no human approval needed)"),
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

    # Put imports inside function to avoid importing everything when starting the CLI
    from autoai.app.main import run_auto_ai

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
# Register unified command groups from autoai.app.commands
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


@main.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    help=_("Run AlphaEvolve workflows."),
)
@click.pass_context
def alphaevolve(ctx: click.Context) -> None:
    """Run AlphaEvolve workflows."""
    _require_packages(("flask",))
    from openevolve import cli as oe_cli

    # Forward remaining arguments to the original AlphaEvolve CLI
    sys.argv = ["alphaevolve", *ctx.args]
    exit_code = oe_cli.main()
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
