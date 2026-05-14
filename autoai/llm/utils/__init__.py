from __future__ import annotations

from typing import List, Literal, Optional

from autoai.utils.ansi_colors import Fore

from autoai.config import Config

from ..api_manager import ApiManager
from ..base import (
    ChatModelResponse,
    ChatSequence,
    Message,
    ResponseMessageDict,
)
from ..providers import openai as iopenai
from ..providers.openai import (
    OPEN_AI_CHAT_MODELS,
    OpenAIFunctionCall,
    OpenAIFunctionSpec,
    count_openai_functions_tokens,
)
from .token_counter import *


def call_ai_function(
    function: str,
    args: list,
    description: str,
    config: Config,
    model: Optional[str] = None,
) -> str:
    """Call an AI function

    This is a magic function that can do anything with no-code. See
    https://github.com/Torantulino/AI-Functions for more info.

    Args:
        function (str): The function to call
        args (list): The arguments to pass to the function
        description (str): The description of the function
        model (str, optional): The model to use. Defaults to None.

    Returns:
        str: The response from the function
    """
    if model is None:
        model = config.smart_llm
    # For each arg, if any are None, 转换 to "None":
    args = [str(arg) if arg is not None else "None" for arg in args]
    # 解析 args to comma separated string
    arg_str: str = ", ".join(args)

    prompt = ChatSequence.for_model(
        model,
        [
            Message(
                "system",
                f"You are now the following python function: ```# {description}"
                f"\n{function}```\n\nOnly respond with your `return` value.",
            ),
            Message("user", arg_str),
        ],
    )
    return create_chat_completion(prompt=prompt, temperature=0, config=config).content


def create_text_completion(
    prompt: str,
    config: Config,
    model: Optional[str],
    temperature: Optional[float],
    max_output_tokens: Optional[int],
) -> str:
    if model is None:
        model = config.fast_llm
    if temperature is None:
        temperature = config.temperature

    kwargs = {"model": model}
    kwargs.update(config.get_openai_credentials(model))

    response = iopenai.create_text_completion(
        prompt=prompt,
        **kwargs,
        temperature=temperature,
        max_tokens=max_output_tokens,
    )
    logger.debug(f"响应: {response}")

    return response.choices[0].text


# Overly simple abstraction until we 创建 something better
def create_chat_completion(
    prompt: ChatSequence,
    config: Config,
    functions: Optional[List[OpenAIFunctionSpec]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ChatModelResponse:
    """Create a chat completion using the OpenAI API

    Args:
        messages (List[Message]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.

    Returns:
        str: The response from the chat completion
    """

    if model is None:
        model = prompt.model.name
    if temperature is None:
        temperature = config.temperature
    if max_tokens is None:
        prompt_tlength = prompt.token_length
        max_tokens = (
            OPEN_AI_CHAT_MODELS[model].max_tokens - prompt_tlength - 1
        )  # -1 is 仅here 因为we have 一个bug 和we don't know how 到fix it. When using gpt-4-0314 we get 一个令牌 error.
        logger.debug(f"Prompt 长度: {prompt_t长度} 令牌s")
        if functions:
            functions_tlength = count_openai_functions_tokens(functions, model)
            max_tokens -= functions_tlength
            logger.debug(f"函数s take up {functions_t长度} 令牌s 在API call")

    logger.debug(
        f"{Fore.GREEN}Creating chat completion with model {model}, temperature {temperature}, max_tokens {max_tokens}{Fore.RESET}"
    )
    chat_completion_kwargs = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for plugin in config.plugins:
        if plugin.can_handle_chat_completion(
            messages=prompt.raw(),
            **chat_completion_kwargs,
        ):
            message = plugin.handle_chat_completion(
                messages=prompt.raw(),
                **chat_completion_kwargs,
            )
            if message is not None:
                return message

    chat_completion_kwargs.update(config.get_openai_credentials(model))

    if functions:
        chat_completion_kwargs["functions"] = [
            function.schema for function in functions
        ]

    # 打印 满 prompt to 调试 日志
    logger.debug(prompt.dump())

    response = iopenai.create_chat_completion(
        messages=prompt.raw(),
        **chat_completion_kwargs,
    )
    logger.debug(f"响应: {response}")

    if hasattr(response, "error"):
        logger.error(response.error)
        raise RuntimeError(response.error)

    first_message: ResponseMessageDict = response.choices[0].message
    content: str | None = first_message.content
    function_call: OpenAIFunctionCall | None = first_message.function_call

    for plugin in config.plugins:
        if not plugin.can_handle_on_response():
            continue
        # 待办: function call support in 插件.on_response()
        content = plugin.on_response(content)

    return ChatModelResponse(
        model_info=OPEN_AI_CHAT_MODELS[model],
        content=content,
        function_call=OpenAIFunctionCall(
            name=function_call.name, arguments=function_call.arguments
        )
        if function_call
        else None,
    )
