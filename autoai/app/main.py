"""应用入口点。可通过CLI或任何其他前端应用调用。"""

import enum
import logging
import math
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Optional

from autoai.utils.ansi_colors import Fore, Style

from autoai.agents import (
    Agent,
    AgentThoughts,
    CommandArgs,
    CommandName,
    CommandRepetitionError,
)
from autoai.app.configurator import create_config
from autoai.app.setup import prompt_user
from autoai.app.spinner import Spinner
from autoai.app.utils import (
    clean_input,
    get_latest_bulletin,
    get_legal_warning,
    markdown_to_ansi_style,
)
from autoai.commands import COMMAND_CATEGORIES
from autoai.config import AIConfig, Config, ConfigBuilder, check_openai_api_key
from autoai.config_injector import apply_strategy
from autoai.event_bus import EventBus, MessageQueue
from autoai.llm.api_manager import ApiManager
from autoai.logs import logger
from autoai.memory.vector import get_memory
from autoai.models.command_registry import CommandRegistry
from autoai.plugins import load_plugin_commands, plugin_registry, scan_plugins
from autoai.prompts.prompt import DEFAULT_TRIGGERING_PROMPT
from autoai.self_improve import (
    DatabaseManager,
    PatchAgent,
    PluginTodoQueue,
    Profiler,
    SelfDevelopManager,
    install_exception_logger,
    start_plugin_queue_processor,
)
from autoai.speech import say_text
from autoai.workspace import Workspace
from scripts.install_plugin_deps import install_plugin_dependencies

from .i18n import _


def run_auto_ai(
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
    ai_name: Optional[str] = None,
    ai_role: Optional[str] = None,
    ai_goals: tuple[str, ...] = tuple(),
    async_mode: bool = False,
    autonomous: bool = False,
    multi_agent: bool = False,
) -> None:
    # 配置 logging before we do anything else.
    logger.set_level(logging.DEBUG if debug else logging.INFO)

    # 解析 路径s early 到prevent surprises 稍后on.
    working_directory = working_directory.resolve()
    workspace_directory = workspace_directory.resolve() if workspace_directory else None

    config = ConfigBuilder.build_config_from_env(workdir=working_directory)
    config.async_mode = async_mode

    # 临时方案: This is a 临时方案 to 允许 the config into the logger without having to pass it around everywhere
    # or 导入 it directly.
    logger.config = config

    # 待办: fill in llm values here
    check_openai_api_key(config)

    create_config(
        config,
        continuous,
        continuous_limit,
        ai_settings,
        prompt_settings,
        skip_reprompt,
        speak,
        debug,
        gpt3only,
        gpt4only,
        memory_type,
        browser_name,
        allow_downloads,
        skip_news,
    )

    if config.continuous_mode:
        for line in get_legal_warning().split("\n"):
            logger.warn(markdown_to_ansi_style(line), "LEGAL:", Fore.RED)

    if not config.skip_news:
        motd, is_new_motd = get_latest_bulletin()
        if motd:
            motd = markdown_to_ansi_style(motd)
            for motd_line in motd.split("\n"):
                logger.info(motd_line, "NEWS:", Fore.GREEN)
            if is_new_motd and not config.chat_messages_enabled:
                input(
                    Fore.MAGENTA
                    + Style.BRIGHT
                    + _("NEWS: Bulletin was updated! Press Enter to continue...")
                    + Style.RESET_ALL
                )

        if sys.version_info < (3, 12):
            logger.typewriter_log(
                "WARNING: ",
                Fore.RED,
                _(
                    "You are running on an older version of Python. Some people have observed problems with certain parts of Auto-AI with this version. Please consider upgrading to Python 3.10 or higher."
                ),
            )

    if install_plugin_deps:
        install_plugin_dependencies()

    # 待办: have this directory live outside the repository (e.g. in a user's
    #   home directory) and have it come in as a command line 参数 or part of
    # env 文件.
    config.workspace_path = Workspace.init_workspace_directory(
        config, workspace_directory
    )

    # 临时方案: doing this here to collect some globals that depend on the workspace.
    config.file_logger_path = Workspace.build_file_logger_path(config.workspace_path)

    # 集合 up self-改进 infrastructure
    event_bus = EventBus(config.workspace_path / "events.db")
    message_queue = MessageQueue(event_bus)
    db = DatabaseManager(config.workspace_path / "improvement.db", message_queue)
    install_exception_logger(db, config.workspace_path / "self_improve.log")
    plugin_queue = PluginTodoQueue(
        config.workspace_path / "todo_queue.json", message_queue
    )
    _patch_agent = PatchAgent(
        db=db, pause_file=config.workspace_path / "self_improve.pause"
    )
    self_develop_thread = None
    self_develop_stop = None
    plugin_thread = None
    plugin_thread_stop = None
    if config.self_develop_enabled:
        manager = SelfDevelopManager(
            plugin_queue=plugin_queue,
            patch_agent=_patch_agent,
            db=db,
            message_queue=message_queue,
            workspace=config.workspace_path,
            interval=config.self_develop_interval,
        )
        self_develop_thread, self_develop_stop = manager.start()
    else:
        plugin_thread, plugin_thread_stop = start_plugin_queue_processor(
            plugin_queue, _patch_agent, db, config.workspace_path
        )

    scan_plugins(config, config.debug_mode)
    config.plugins = list(plugin_registry.values())

    # 创建 a CommandRegistry instance and scan default folder
    command_registry = CommandRegistry.with_command_modules(COMMAND_CATEGORIES, config)
    load_plugin_commands(command_registry)

    ai_config = construct_main_ai_config(
        config,
        name=ai_name,
        role=ai_role,
        goals=ai_goals,
    )
    ai_config.command_registry = command_registry
    # 打印(prompt)

    # add chat plugins capable of 报告 to logger
    if config.chat_messages_enabled:
        for plugin in config.plugins:
            if hasattr(plugin, "can_handle_report") and plugin.can_handle_report():
                logger.info(f"加载ed plug在到logger: {plugin.__class__.__名称__}")
                logger.chat_plugins.append(plugin)

    # 初始化 内存 and make sure it is 空.
    # this is particularly important for indexing and referencing pinecone 内存
    memory = get_memory(config)
    memory.clear()
    logger.typewriter_log(
        "Using memory of type:", Fore.GREEN, f"{memory.__class__.__name__}"
    )
    logger.typewriter_log("Using Browser:", Fore.GREEN, config.selenium_web_browser)

    agent = Agent(
        memory=memory,
        command_registry=command_registry,
        triggering_prompt=DEFAULT_TRIGGERING_PROMPT,
        ai_config=ai_config,
        config=config,
        plugin_queue=plugin_queue,
        message_queue=message_queue,
        db=db,
    )

    try:
        if getattr(config, "async_mode", False):
            from autoai.agents.async_agent import AsyncAgent
            from autoai.agents.subsystem_injection import inject_v1_subsystems
            from autoai.app.async_loop import run_sync_interaction_loop

            async_agent = AsyncAgent(
                memory=memory,
                command_registry=command_registry,
                triggering_prompt=DEFAULT_TRIGGERING_PROMPT,
                ai_config=ai_config,
                config=config,
                plugin_queue=plugin_queue,
                message_queue=message_queue,
                db=db,
            )

            if async_agent._ability_registry is not None:
                sdm = None
                if config.self_develop_enabled:
                    sdm = SelfDevelopManager(
                        plugin_queue=plugin_queue,
                        patch_agent=_patch_agent,
                        db=db,
                        message_queue=message_queue,
                        workspace=config.workspace_path,
                        interval=config.self_develop_interval,
                    )
                inject_v1_subsystems(
                    async_agent._ability_registry,
                    self_develop_manager=sdm,
                    message_queue=message_queue,
                )

            if autonomous:
                async_agent.enable_autonomous_mode()

            ma_system = None

            if multi_agent:
                from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
                ma_config = SystemConfig(
                    autonomous=autonomous,
                    enable_tui=True,
                    enable_health_monitor=True,
                    enable_agent_pool=True,
                    enable_policy_evolver=autonomous,
                    enable_checkpoint=True,
                )
                ma_system = MultiAgentSystem(
                    workspace_path=config.workspace_path,
                    config=ma_config,
                    message_queue=message_queue,
                )
                ma_system.setup()
                ma_system.attach_to_agent(async_agent)
                ma_system.start()
                logger.typewriter_log(
                    "Multi-Agent",
                    Fore.GREEN,
                    f"协调模式已启动: {len(ma_system.agent_factory.created_agents)} agents, "
                    f"autonomous={autonomous}",
                )

            comm_bus = ma_system.comm_bus if ma_system else None
            multi_tui = ma_system.multi_tui if ma_system else None

            cycle_budget = _get_cycle_budget(
                config.continuous_mode, config.continuous_limit
            )
            try:
                run_sync_interaction_loop(
                    async_agent,
                    config,
                    cycle_budget,
                    comm_bus=comm_bus,
                    multi_tui=multi_tui,
                )
            finally:
                if ma_system is not None:
                    ma_system.stop()
        else:
            run_interaction_loop(agent)
    finally:
        if self_develop_stop is not None and self_develop_thread is not None:
            self_develop_stop.set()
            self_develop_thread.join()
        if plugin_thread_stop is not None and plugin_thread is not None:
            plugin_thread_stop.set()
            plugin_thread.join()


def _get_cycle_budget(continuous_mode: bool, continuous_limit: int | None) -> float:
    # Translate 从continuous_mode/continuous_限制 config
    # to a cycle_budget (maximum number of cycles to 运行 without checking in with the
    # user) and a count of cycles_remaining before we 检查 in..
    if continuous_mode:
        return float(continuous_limit) if continuous_limit else math.inf
    return 1.0


class UserFeedback(str, enum.Enum):
    """用户反馈的枚举。"""

    AUTHORIZE = "GENERATE NEXT COMMAND JSON"
    EXIT = "EXIT"
    TEXT = "TEXT"


def run_interaction_loop(
    agent: Agent,
) -> None:
    """Run the main interaction loop for the agent.

    Args:
        agent: The agent to run the interaction loop for.

    Returns:
        None
    """
    # These contain both application config and 代理 config, so grab them here.
    config = agent.config
    ai_config = agent.ai_config
    logger.debug(f"{ai_config.ai_名称} System Prompt: {代理.system_prompt}")

    cycle_budget = cycles_remaining = _get_cycle_budget(
        config.continuous_mode, config.continuous_limit
    )
    spinner = Spinner(_("Thinking..."), plain_output=config.plain_output)

    def graceful_agent_interrupt(signum: int, frame: Optional[FrameType]) -> None:
        nonlocal cycle_budget, cycles_remaining, spinner
        if cycles_remaining in [0, 1, math.inf]:
            logger.typewriter_log(
                _(
                    "Interrupt signal received. Stopping continuous command execution immediately."
                ),
                Fore.RED,
            )
            sys.exit()
        else:
            restart_spinner = spinner.running
            if spinner.running:
                spinner.stop()

            logger.typewriter_log(
                _("Interrupt signal received. Stopping continuous command execution."),
                Fore.RED,
            )
            cycles_remaining = 1
            if restart_spinner:
                spinner.start()

    # 集合 up an interrupt 信号 for the 代理.
    signal.signal(signal.SIGINT, graceful_agent_interrupt)

    #########################
    # Application Main 循环 #
    #########################

    while cycles_remaining > 0:
        logger.debug(f"周期预算: {cycle_budget}; 剩余: {cycles_剩余}")

        ########
        # 计划 #
        ########
        # Have the 代理 determine the next action to take.
        with spinner:
            if agent.db:
                with Profiler(agent.db, "think"):
                    command_name, command_args, assistant_reply_dict = agent.think()
            else:
                command_name, command_args, assistant_reply_dict = agent.think()

        ###############
        # 更新 User #
        ###############
        # 打印 the assistant's thoughts and the next command to the user.
        update_user(config, ai_config, command_name, command_args, assistant_reply_dict)

        ##################
        # 获取 user 输入 #
        ##################
        if cycles_remaining == 1:  # 最后一个 周期
            user_feedback, user_input, new_cycles_remaining = get_user_feedback(
                config,
                ai_config,
            )

            if user_feedback == UserFeedback.AUTHORIZE:
                if new_cycles_remaining is not None:
                    if cycle_budget > 1:
                        cycle_budget = new_cycles_remaining
                    cycles_remaining = new_cycles_remaining
                else:
                    if cycle_budget > 1:
                        logger.typewriter_log(
                            _("RESUMING CONTINUOUS EXECUTION: "),
                            Fore.MAGENTA,
                            _("The cycle budget is {cycle_budget}.").format(
                                cycle_budget=cycle_budget
                            ),
                        )
                    cycles_remaining = cycle_budget
                logger.typewriter_log(
                    _("-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-="),
                    Fore.MAGENTA,
                    "",
                )
            elif user_feedback == UserFeedback.EXIT:
                logger.typewriter_log(_("Exiting..."), Fore.YELLOW)
                exit()
            else:  # user_费用dback == UserFeedback.TEXT
                command_name = "human_feedback"
        else:
            user_input = None
            # First 日志 new-line so user can differentiate sections better in console
            logger.typewriter_log("\n")
            if cycles_remaining != math.inf:
                # 打印 authorized commands left 值
                authorized_commands_left = cycles_remaining
                logger.typewriter_log(
                    _("AUTHORISED COMMANDS LEFT: "),
                    Fore.CYAN,
                    f"{authorized_commands_left}",
                )

        ###################
        # 执行 Command #
        ###################
        # Decrement the 循环 counter first to reduce the likelihood of a SIGINT
        # happening 期间命令 execution, 集合ting 周期s remaining 到1,
        # and then having the decrement 集合 it to 0, exiting the application.
        if command_name != "human_feedback":
            cycles_remaining -= 1
        try:
            result = agent.execute_step(command_name, command_args, user_input)
        except CommandRepetitionError as e:
            result = str(e)
            cycles_remaining = 1

        if result is not None:
            logger.typewriter_log(_("SYSTEM: "), Fore.YELLOW, result)
        else:
            logger.typewriter_log(
                _("SYSTEM: "), Fore.YELLOW, _("Unable to execute command")
            )


def update_user(
    config: Config,
    ai_config: AIConfig,
    command_name: CommandName | None,
    command_args: CommandArgs | None,
    assistant_reply_dict: AgentThoughts,
) -> None:
    """Prints the assistant's thoughts and the next command to the user.

    Args:
        config: The program's configuration.
        ai_config: The AI's configuration.
        command_name: The name of the command to execute.
        command_args: The arguments for the command.
        assistant_reply_dict: The assistant's reply.
    """

    print_assistant_thoughts(ai_config.ai_name, assistant_reply_dict, config)

    if command_name is not None:
        if command_name.lower().startswith("error"):
            logger.typewriter_log(
                _("ERROR: "),
                Fore.RED,
                _(
                    "The Agent failed to select an action. Error message: {command_name}"
                ).format(command_name=command_name),
            )
        else:
            if config.speak_mode:
                say_text(f"I want to execute {command_name}", config)

            # First 日志 new-line so user can differentiate sections better in console
            logger.typewriter_log("\n")
            logger.typewriter_log(
                "NEXT ACTION: ",
                Fore.CYAN,
                f"COMMAND = {Fore.CYAN}{remove_ansi_escape(command_name)}{Style.RESET_ALL}  "
                f"ARGUMENTS = {Fore.CYAN}{command_args}{Style.RESET_ALL}",
            )
    else:
        logger.typewriter_log(
            _("NO ACTION SELECTED: "),
            Fore.RED,
            _("The Agent failed to select an action."),
        )


def get_user_feedback(
    config: Config,
    ai_config: AIConfig,
) -> tuple[UserFeedback, str, int | None]:
    """Gets the user's feedback on the assistant's reply.

    Args:
        config: The program's configuration.
        ai_config: The AI's configuration.

    Returns:
        A tuple of the user's feedback, the user's input, and the number of
        cycles remaining if the user has initiated a continuous cycle.
    """
    # ### 获取 USER AUTHORIZATION TO 执行 COMMAND ###
    # 获取 键 press: Prompt the user to press enter to continue or escape
    # 到exit
    logger.info(
        _(
            "Enter '{authorise}' to authorise command, '{authorise} -N' to run N continuous commands, '{exit}' to exit program, or enter feedback for {name}..."
        ).format(
            authorise=config.authorise_key,
            exit=config.exit_key,
            name=ai_config.ai_name,
        )
    )

    user_feedback = None
    user_input = ""
    new_cycles_remaining = None

    while user_feedback is None:
        # 获取 输入 from user
        if config.chat_messages_enabled:
            console_input = clean_input(config, _("Waiting for your response..."))
        else:
            console_input = clean_input(
                config, Fore.MAGENTA + _("Input:") + Style.RESET_ALL
            )

        # 解析 user 输入
        if console_input.lower().strip() == config.authorise_key:
            user_feedback = UserFeedback.AUTHORIZE
        elif console_input.lower().strip() == "":
            logger.warn(_("Invalid input format."))
        elif console_input.lower().startswith(f"{config.authorise_key} -"):
            try:
                user_feedback = UserFeedback.AUTHORIZE
                new_cycles_remaining = abs(int(console_input.split(" ")[1]))
            except ValueError:
                logger.warn(
                    _(
                        "Invalid input format. Please enter '{authorise} -N' where N is the number of continuous tasks."
                    ).format(authorise=config.authorise_key)
                )
        elif console_input.lower() in [config.exit_key, "exit"]:
            user_feedback = UserFeedback.EXIT
        else:
            user_feedback = UserFeedback.TEXT
            user_input = console_input

    return user_feedback, user_input, new_cycles_remaining


def construct_main_ai_config(
    config: Config,
    name: Optional[str] = None,
    role: Optional[str] = None,
    goals: tuple[str, ...] | None = None,
) -> AIConfig:
    """Construct the prompt for the AI to respond to

    Returns:
        str: The prompt string
    """
    strategy_path = config.workdir / "configs" / "default_strategy.yaml"
    if strategy_path.is_file():
        ai_config = apply_strategy(str(strategy_path))
        ai_config.save(config.workdir / config.ai_settings_file)
    else:
        ai_config = AIConfig.load(config.workdir / config.ai_settings_file)

    # 应用 overrides
    if name:
        ai_config.ai_name = name
    if role:
        ai_config.ai_role = role
    if goals is None:
        goals = ()
    if goals:
        ai_config.ai_goals = list(goals)

    if all([name, role, goals]) or (
        config.skip_reprompt
        and all([ai_config.ai_name, ai_config.ai_role, ai_config.ai_goals])
    ):
        logger.typewriter_log("Name :", Fore.GREEN, ai_config.ai_name)
        logger.typewriter_log("Role :", Fore.GREEN, ai_config.ai_role)
        logger.typewriter_log("Goals:", Fore.GREEN, f"{ai_config.ai_goals}")
        logger.typewriter_log(
            "API Budget:",
            Fore.GREEN,
            "infinite" if ai_config.api_budget <= 0 else f"${ai_config.api_budget}",
        )
    elif all([ai_config.ai_name, ai_config.ai_role, ai_config.ai_goals]):
        logger.typewriter_log(
            "欢迎回来！",
            Fore.GREEN,
            f"你希望我继续作为{ai_config.ai_name}吗？",
            speak_text=True,
        )
        should_continue = clean_input(
            config,
            _(
                """Continue with the last settings?
Name:  {ai_config.ai_name}
Role:  {ai_config.ai_role}
Goals: {ai_config.ai_goals}
API Budget: {budget}
Continue ({authorise}/{exit}): """
            ).format(
                ai_config=ai_config,
                budget="infinite"
                if ai_config.api_budget <= 0
                else f"${ai_config.api_budget}",
                authorise=config.authorise_key,
                exit=config.exit_key,
            ),
        )
        if should_continue.lower() == config.exit_key:
            ai_config = AIConfig()

    if any([not ai_config.ai_name, not ai_config.ai_role, not ai_config.ai_goals]):
        ai_config = prompt_user(config)
        ai_config.save(config.workdir / config.ai_settings_file)

    if config.restrict_to_workspace:
        logger.typewriter_log(
            "注意：该代理创建的所有文件/目录都位于其工作区：",
            Fore.YELLOW,
            f"{config.workspace_path}",
        )
    # 集合 the total api 预算
    api_manager = ApiManager()
    api_manager.set_total_budget(ai_config.api_budget)

    # 代理 Created, 打印 消息
    logger.typewriter_log(
        ai_config.ai_name,
        Fore.LIGHTBLUE_EX,
        "has been created with the following details:",
        speak_text=True,
    )

    # 打印 the ai_config details
    # Name
    logger.typewriter_log("Name:", Fore.GREEN, ai_config.ai_name, speak_text=False)
    # Role
    logger.typewriter_log("Role:", Fore.GREEN, ai_config.ai_role, speak_text=False)
    # 目标
    logger.typewriter_log("Goals:", Fore.GREEN, "", speak_text=False)
    for goal in ai_config.ai_goals:
        logger.typewriter_log("-", Fore.GREEN, goal, speak_text=False)

    return ai_config


def print_assistant_thoughts(
    ai_name: str,
    assistant_reply_json_valid: dict,
    config: Config,
) -> None:
    from autoai.speech import say_text

    assistant_thoughts_reasoning = None
    assistant_thoughts_plan = None
    assistant_thoughts_speak = None
    assistant_thoughts_criticism = None

    assistant_thoughts = assistant_reply_json_valid.get("thoughts", {})
    assistant_thoughts_text = remove_ansi_escape(assistant_thoughts.get("text", ""))
    if assistant_thoughts:
        assistant_thoughts_reasoning = remove_ansi_escape(
            assistant_thoughts.get("reasoning", "")
        )
        assistant_thoughts_plan = remove_ansi_escape(assistant_thoughts.get("plan", ""))
        assistant_thoughts_criticism = remove_ansi_escape(
            assistant_thoughts.get("criticism", "")
        )
        assistant_thoughts_speak = remove_ansi_escape(
            assistant_thoughts.get("speak", "")
        )
    logger.typewriter_log(
        f"{ai_name.upper()} THOUGHTS:", Fore.YELLOW, assistant_thoughts_text
    )
    logger.typewriter_log("REASONING:", Fore.YELLOW, str(assistant_thoughts_reasoning))
    if assistant_thoughts_plan:
        logger.typewriter_log("PLAN:", Fore.YELLOW, "")
        # If it's a 列表, 连接 it into a string
        if isinstance(assistant_thoughts_plan, list):
            assistant_thoughts_plan = "\n".join(assistant_thoughts_plan)
        elif isinstance(assistant_thoughts_plan, dict):
            assistant_thoughts_plan = str(assistant_thoughts_plan)

        # 分割 the input_string using the newline character and dashes
        lines = assistant_thoughts_plan.split("\n")
        for line in lines:
            line = line.lstrip("- ")
            logger.typewriter_log("- ", Fore.GREEN, line.strip())
    logger.typewriter_log(
        "CRITICISM (Is this action similar to an earlier one?):",
        Fore.YELLOW,
        f"{assistant_thoughts_criticism}",
    )
    # 朗读 assistant's thoughts
    if assistant_thoughts_speak:
        if config.speak_mode:
            say_text(assistant_thoughts_speak, config)
        else:
            logger.typewriter_log("SPEAK:", Fore.YELLOW, f"{assistant_thoughts_speak}")


def remove_ansi_escape(s: str) -> str:
    return s.replace("\x1b", "")
