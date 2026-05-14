"""设置AI及其目标"""
import re
from typing import Optional

from autoai.utils.ansi_colors import Fore, Style
from jinja2 import Template

from autoai.app import utils
from autoai.config import Config
from autoai.config.ai_config import AIConfig
from autoai.llm.base import ChatSequence, Message
from autoai.llm.utils import create_chat_completion
from autoai.logs import logger
from autoai.prompts.default_prompts import (
    DEFAULT_SYSTEM_PROMPT_AICONFIG_AUTOMATIC,
    DEFAULT_TASK_PROMPT_AICONFIG_AUTOMATIC,
    DEFAULT_USER_DESIRE_PROMPT,
)
from .i18n import _


def prompt_user(
    config: Config, ai_config_template: Optional[AIConfig] = None
) -> AIConfig:
    """Prompt the user for input

    Params:
        config (Config): The Config object
        ai_config_template (AIConfig): The AIConfig object to use as a template

    Returns:
        AIConfig: The AIConfig object tailored to the user's input
    """

    # Construct the prompt
    logger.typewriter_log(
        _("Welcome to Auto-AI! "),
        Fore.GREEN,
        _("run with '--help' for more information."),
        speak_text=True,
    )

    ai_config_template_provided = ai_config_template is not None and any(
        [
            ai_config_template.ai_goals,
            ai_config_template.ai_name,
            ai_config_template.ai_role,
        ]
    )

    user_desire = ""
    if not ai_config_template_provided:
        # 获取 user desire if command line overrides have not been passed in
        logger.typewriter_log(
            _("Create an AI-Assistant:"),
            Fore.GREEN,
            _("input '--manual' to enter manual mode."),
            speak_text=True,
        )

        user_desire = utils.clean_input(
            config, f"{Fore.LIGHTBLUE_EX}{_('I want Auto-AI to')}{Style.RESET_ALL}: "
        )

    if user_desire.strip() == "":
        user_desire = DEFAULT_USER_DESIRE_PROMPT  # Default prompt

    # If user desire contains "--manual" 或we have overridden 任意的AI configu比率n
    if "--manual" in user_desire or ai_config_template_provided:
        logger.typewriter_log(
            _("Manual Mode Selected"),
            Fore.GREEN,
            speak_text=True,
        )
        return generate_aiconfig_manual(config, ai_config_template)

    else:
        try:
            return generate_aiconfig_automatic(user_desire, config)
        except Exception as e:
            logger.typewriter_log(
                _(
                    "Unable to automatically generate AI Config based on user desire."
                ),
                Fore.RED,
                _("Falling back to manual mode."),
                speak_text=True,
            )
            logger.debug(f"错误 期间AIConfig gene比率n: {e}")

            return generate_aiconfig_manual(config)


def generate_aiconfig_manual(
    config: Config, ai_config_template: Optional[AIConfig] = None
) -> AIConfig:
    """
    Interactively create an AI configuration by prompting the user to provide the name, role, and goals of the AI.

    This function guides the user through a series of prompts to collect the necessary information to create
    an AIConfig object. The user will be asked to provide a name and role for the AI, as well as up to five
    goals. If the user does not provide a value for any of the fields, default values will be used.

    Params:
        config (Config): The Config object
        ai_config_template (AIConfig): The AIConfig object to use as a template

    Returns:
        AIConfig: An AIConfig object containing the user-defined or default AI name, role, and goals.
    """

    # Manual 设置up Intro
    logger.typewriter_log(
        "Create an AI-Assistant:",
        Fore.GREEN,
        "Enter the name of your AI and its role below. Entering nothing will load"
        " defaults.",
        speak_text=True,
    )

    if ai_config_template and ai_config_template.ai_name:
        ai_name = ai_config_template.ai_name
    else:
        ai_name = ""
        # 获取 AI Name from User
        logger.typewriter_log(
            "Name your AI: ", Fore.GREEN, "For example, 'Entrepreneur-GPT'"
        )
        ai_name = utils.clean_input(config, "AI Name: ")
    if ai_name == "":
        ai_name = "Entrepreneur-GPT"

    logger.typewriter_log(
        f"{ai_name} here!", Fore.LIGHTBLUE_EX, "I am at your service.", speak_text=True
    )

    if ai_config_template and ai_config_template.ai_role:
        ai_role = ai_config_template.ai_role
    else:
        # 获取 AI Role from User
        logger.typewriter_log(
            "Describe your AI's role: ",
            Fore.GREEN,
            "For example, 'an AI designed to autonomously develop and run businesses with"
            " the sole goal of increasing your net worth.'",
        )
        ai_role = utils.clean_input(config, f"{ai_name} is: ")
    if ai_role == "":
        ai_role = "an AI designed to autonomously develop and run businesses with the"
        " sole goal of increasing your net worth."

    if ai_config_template and ai_config_template.ai_goals:
        ai_goals = ai_config_template.ai_goals
    else:
        # Enter up 到5 goals 用于AI
        logger.typewriter_log(
            "Enter up to 5 goals for your AI: ",
            Fore.GREEN,
            "For example: \nIncrease net worth, Grow Twitter Account, Develop and manage"
            " multiple businesses autonomously'",
        )
        logger.info("Enter nothing 到load 默认s, enter nothing when finished.")
        ai_goals = []
        for i in range(5):
            ai_goal = utils.clean_input(
                config, f"{Fore.LIGHTBLUE_EX}Goal{Style.RESET_ALL} {i+1}: "
            )
            if ai_goal == "":
                break
            ai_goals.append(ai_goal)
    if not ai_goals:
        ai_goals = [
            "Increase net worth",
            "Grow Twitter Account",
            "Develop and manage multiple businesses autonomously",
        ]

    # 获取 API 预算 from User
    logger.typewriter_log(
        "Enter your budget for API calls: ",
        Fore.GREEN,
        "For example: $1.50",
    )
    logger.info("Enter nothing 到let AI run 无monetary 限制")
    api_budget_input = utils.clean_input(
        config, f"{Fore.LIGHTBLUE_EX}Budget{Style.RESET_ALL}: $"
    )
    if api_budget_input == "":
        api_budget = 0.0
    else:
        try:
            api_budget = float(api_budget_input.replace("$", ""))
        except ValueError:
            logger.typewriter_log(
                "Invalid budget input. Setting budget to unlimited.", Fore.RED
            )
            api_budget = 0.0

    return AIConfig(ai_name, ai_role, ai_goals, api_budget)


def generate_aiconfig_automatic(user_prompt: str, config: Config) -> AIConfig:
    """Generates an AIConfig object from the given string.

    Returns:
    AIConfig: The AIConfig object tailored to the user's input
    """

    system_prompt = DEFAULT_SYSTEM_PROMPT_AICONFIG_AUTOMATIC
    prompt_ai_config_automatic = Template(
        DEFAULT_TASK_PROMPT_AICONFIG_AUTOMATIC
    ).render(user_prompt=user_prompt)
    # Call LLM with the string as user 输入
    output = create_chat_completion(
        ChatSequence.for_model(
            config.fast_llm,
            [
                Message("system", system_prompt),
                Message("user", prompt_ai_config_automatic),
            ],
        ),
        config,
    ).content

    # 调试 LLM 输出
    logger.debug(f"AI Config Generat或Raw 输出: {output}")

    # 解析 the 输出
    ai_name = re.search(r"Name(?:\s*):(?:\s*)(.*)", output, re.IGNORECASE).group(1)
    ai_role = (
        re.search(
            r"Description(?:\s*):(?:\s*)(.*?)(?:(?:\n)|Goals)",
            output,
            re.IGNORECASE | re.DOTALL,
        )
        .group(1)
        .strip()
    )
    ai_goals = re.findall(r"(?<=\n)-\s*(.*)", output)
    api_budget = 0.0  # TODO: parse api 预算 using 一个常规 表达式

    return AIConfig(ai_name, ai_role, ai_goals, api_budget)
