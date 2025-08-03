"""Main script for the autogpt package."""
import importlib.util
import sys
from pathlib import Path
from typing import Optional

import click


def _check_python_version() -> None:
    """Ensure the running Python version is supported."""
    if sys.version_info < (3, 10):
        raise click.ClickException("Python 3.10 or higher is required to run AutoGPT.")


def _require_packages(packages: tuple[str, ...]) -> None:
    """Verify that required packages are installed."""
    missing = [p for p in packages if importlib.util.find_spec(p) is None]
    if missing:
        raise click.ClickException("Required packages missing: " + ", ".join(missing))


@click.group(invoke_without_command=True)
@click.option("-c", "--continuous", is_flag=True, help="Enable Continuous Mode")
@click.option(
    "--skip-reprompt",
    "-y",
    is_flag=True,
    help="Skips the re-prompting messages at the beginning of the script",
)
@click.option(
    "--ai-settings",
    "-C",
    help=(
        "Specifies which ai_settings.yaml file to use, relative to the Auto-GPT"
        " root directory. Will also automatically skip the re-prompt."
    ),
)
@click.option(
    "--prompt-settings",
    "-P",
    help="Specifies which prompt_settings.yaml file to use.",
)
@click.option(
    "-l",
    "--continuous-limit",
    type=int,
    help="Defines the number of times to run in continuous mode",
)
@click.option("--speak", is_flag=True, help="Enable Speak Mode")
@click.option("--debug", is_flag=True, help="Enable Debug Mode")
@click.option("--gpt3only", is_flag=True, help="Enable GPT3.5 Only Mode")
@click.option("--gpt4only", is_flag=True, help="Enable GPT4 Only Mode")
@click.option(
    "--use-memory",
    "-m",
    "memory_type",
    type=str,
    help="Defines which Memory backend to use",
)
@click.option(
    "-b",
    "--browser-name",
    help="Specifies which web-browser to use when using selenium to scrape the web.",
)
@click.option(
    "--allow-downloads",
    is_flag=True,
    help="Dangerous: Allows Auto-GPT to download files natively.",
)
@click.option(
    "--skip-news",
    is_flag=True,
    help="Specifies whether to suppress the output of latest news on startup.",
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
    help="Sets the working directory for Auto-GPT.",
)
@click.option(
    "--workspace-directory",
    "-w",
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    help=(
        "Path to the workspace directory. Defaults to 'auto_gpt_workspace' inside the "
        "working directory."
    ),
)
@click.option(
    "--install-plugin-deps",
    is_flag=True,
    help="Installs external dependencies for 3rd party plugins.",
)
@click.option(
    "--ai-name",
    type=str,
    help="AI name override",
)
@click.option(
    "--ai-role",
    type=str,
    help="AI role override",
)
@click.option(
    "--ai-goal",
    type=str,
    multiple=True,
    help="AI goal override; may be used multiple times to pass multiple goals",
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
) -> None:
    """
    Welcome to AutoGPT an experimental open-source application showcasing the capabilities of the GPT-4 pushing the boundaries of AI.

    Start an Auto-GPT assistant.
    """
    _check_python_version()
    _require_packages(("openai",))

    # Put imports inside function to avoid importing everything when starting the CLI
    from autogpt.app.main import run_auto_gpt

    if ctx.invoked_subcommand is None:
        run_auto_gpt(
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
        )


@main.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
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
