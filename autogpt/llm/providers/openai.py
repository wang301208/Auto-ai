from __future__ import annotations

import functools
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from openai import (
    APIError,
    AsyncAzureOpenAI,
    AsyncOpenAI,
    AzureOpenAI,
    OpenAI,
    RateLimitError,
    Timeout,
)

try:
    from openai import ServiceUnavailableError
except ImportError:  # openai>=1 does not expose this error
    from openai import InternalServerError as ServiceUnavailableError

from colorama import Fore, Style

from autogpt.app.i18n import _
from autogpt.llm.base import (
    ChatModelInfo,
    EmbeddingModelInfo,
    MessageDict,
    TextModelInfo,
    TText,
)
from autogpt.logs import logger
from autogpt.models.command_parameter import ParameterType
from autogpt.models.command_registry import CommandRegistry

OPEN_AI_CHAT_MODELS = {
    info.name: info
    for info in [
        ChatModelInfo(
            name="gpt-3.5-turbo-0301",
            prompt_token_cost=0.0015,
            completion_token_cost=0.002,
            max_tokens=4096,
        ),
        ChatModelInfo(
            name="gpt-3.5-turbo-0613",
            prompt_token_cost=0.0015,
            completion_token_cost=0.002,
            max_tokens=4096,
            supports_functions=True,
        ),
        ChatModelInfo(
            name="gpt-3.5-turbo-16k-0613",
            prompt_token_cost=0.003,
            completion_token_cost=0.004,
            max_tokens=16384,
            supports_functions=True,
        ),
        ChatModelInfo(
            name="gpt-4-0314",
            prompt_token_cost=0.03,
            completion_token_cost=0.06,
            max_tokens=8192,
        ),
        ChatModelInfo(
            name="gpt-4-0613",
            prompt_token_cost=0.03,
            completion_token_cost=0.06,
            max_tokens=8191,
            supports_functions=True,
        ),
        ChatModelInfo(
            name="gpt-4-32k-0314",
            prompt_token_cost=0.06,
            completion_token_cost=0.12,
            max_tokens=32768,
        ),
        ChatModelInfo(
            name="gpt-4-32k-0613",
            prompt_token_cost=0.06,
            completion_token_cost=0.12,
            max_tokens=32768,
            supports_functions=True,
        ),
    ]
}
# Set aliases for rolling model IDs
chat_model_mapping = {
    "gpt-3.5-turbo": "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
    "gpt-4": "gpt-4-0613",
    "gpt-4-32k": "gpt-4-32k-0613",
}
for alias, target in chat_model_mapping.items():
    alias_info = ChatModelInfo(**OPEN_AI_CHAT_MODELS[target].__dict__)
    alias_info.name = alias
    OPEN_AI_CHAT_MODELS[alias] = alias_info

OPEN_AI_TEXT_MODELS = {
    info.name: info
    for info in [
        TextModelInfo(
            name="text-davinci-003",
            prompt_token_cost=0.02,
            completion_token_cost=0.02,
            max_tokens=4097,
        ),
    ]
}

OPEN_AI_EMBEDDING_MODELS = {
    info.name: info
    for info in [
        EmbeddingModelInfo(
            name="text-embedding-ada-002",
            prompt_token_cost=0.0001,
            max_tokens=8191,
            embedding_dimensions=1536,
        ),
    ]
}

OPEN_AI_MODELS: dict[str, ChatModelInfo | EmbeddingModelInfo | TextModelInfo] = {
    **OPEN_AI_CHAT_MODELS,
    **OPEN_AI_TEXT_MODELS,
    **OPEN_AI_EMBEDDING_MODELS,
}


def _get_client(credentials: dict[str, str]) -> OpenAI | AzureOpenAI:
    """Return a synchronous OpenAI client initialized with the given credentials."""
    creds = credentials.copy()
    api_type = creds.pop("api_type", None)
    api_key = creds.pop("api_key", None)
    api_base = creds.pop("api_base", None)
    organization = creds.pop("organization", None)
    if api_type == "azure":
        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=api_base,
            api_version=creds.pop("api_version", None),
        )
    return OpenAI(api_key=api_key, base_url=api_base, organization=organization)


def _get_async_client(credentials: dict[str, str]) -> AsyncOpenAI | AsyncAzureOpenAI:
    """Return an asynchronous OpenAI client initialized with the given credentials."""
    creds = credentials.copy()
    api_type = creds.pop("api_type", None)
    api_key = creds.pop("api_key", None)
    api_base = creds.pop("api_base", None)
    organization = creds.pop("organization", None)
    if api_type == "azure":
        return AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=api_base,
            api_version=creds.pop("api_version", None),
        )
    return AsyncOpenAI(api_key=api_key, base_url=api_base, organization=organization)


def meter_api(func: Callable):
    """Adds ApiManager metering to functions which make OpenAI API calls"""
    from autogpt.llm.api_manager import ApiManager

    api_manager = ApiManager()

    def metered_func(*args, **kwargs):
        response = func(*args, **kwargs)
        try:
            usage = response.usage
            logger.debug(f"Reported usage from call to model {response.model}: {usage}")
            api_manager.update_cost(
                usage.prompt_tokens,
                getattr(usage, "completion_tokens", 0),
                response.model,
            )
        except Exception as err:
            logger.warn(
                _("Failed to update API costs: {err_class}: {err}").format(
                    err_class=err.__class__.__name__, err=err
                )
            )
        return response

    return metered_func


def retry_api(
    max_retries: int = 10,
    backoff_base: float = 2.0,
    warn_user: bool = True,
):
    """Retry an OpenAI API call.

    Args:
        num_retries int: Number of retries. Defaults to 10.
        backoff_base float: Base for exponential backoff. Defaults to 2.
        warn_user bool: Whether to warn the user. Defaults to True.
    """
    error_messages = {
        ServiceUnavailableError: f"{Fore.RED}Error: The OpenAI API engine is currently overloaded{Fore.RESET}",
        RateLimitError: f"{Fore.RED}Error: Reached rate limit{Fore.RESET}",
    }
    api_key_error_msg = (
        f"Please double check that you have setup a "
        f"{Fore.CYAN + Style.BRIGHT}PAID{Style.RESET_ALL} OpenAI API Account. You can "
        f"read more here: {Fore.CYAN}https://docs.agpt.co/setup/#getting-an-api-key{Fore.RESET}"
    )
    backoff_msg = f"{Fore.RED}Waiting {{backoff}} seconds...{Fore.RESET}"

    def _wrapper(func: Callable):
        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            user_warned = not warn_user
            max_attempts = max_retries + 1  # +1 for the first attempt
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except (RateLimitError, ServiceUnavailableError) as e:
                    if attempt >= max_attempts or (
                        # User's API quota exceeded
                        isinstance(e, RateLimitError)
                        and (err := getattr(e, "error", {}))
                        and err.get("code") == "insufficient_quota"
                    ):
                        raise

                    error_msg = error_messages[type(e)]
                    logger.warn(error_msg)
                    if not user_warned:
                        logger.double_check(api_key_error_msg)
                        logger.debug(f"Status: {e.http_status}")
                        logger.debug(f"Response body: {e.json_body}")
                        logger.debug(f"Response headers: {e.headers}")
                        user_warned = True

                except (APIError, Timeout) as e:
                    if (e.http_status not in [429, 502]) or (attempt == max_attempts):
                        raise

                backoff = backoff_base ** (attempt + 2)
                logger.warn(backoff_msg.format(backoff=backoff))
                time.sleep(backoff)

        return _wrapped

    return _wrapper


@meter_api
@retry_api()
def create_chat_completion(
    messages: List[MessageDict],
    *_,
    **kwargs,
) -> object:
    """Create a chat completion using the OpenAI API

    Args:
        messages: A list of messages to feed to the chatbot.
        kwargs: Other arguments to pass to the OpenAI API chat completion call.
    Returns:
        object: The ChatCompletion response from OpenAI

    """
    credentials_keys = [
        "api_key",
        "api_base",
        "organization",
        "api_type",
        "api_version",
    ]
    credentials = {k: kwargs.pop(k) for k in credentials_keys if k in kwargs}
    if "deployment_id" in kwargs or "engine" in kwargs:
        deployment = kwargs.pop("deployment_id", None) or kwargs.pop("engine", None)
        kwargs["model"] = deployment
    client = _get_client(credentials)
    completion = client.chat.completions.create(
        messages=messages,
        **kwargs,
    )
    if not hasattr(completion, "error"):
        logger.debug(f"Response: {completion}")
    return completion


@meter_api
@retry_api()
def create_text_completion(
    prompt: str,
    *_,
    **kwargs,
) -> object:
    """Create a text completion using the OpenAI API

    Args:
        prompt: A text prompt to feed to the LLM
        kwargs: Other arguments to pass to the OpenAI API text completion call.
    Returns:
        object: The Completion response from OpenAI

    """
    credentials_keys = [
        "api_key",
        "api_base",
        "organization",
        "api_type",
        "api_version",
    ]
    credentials = {k: kwargs.pop(k) for k in credentials_keys if k in kwargs}
    if "deployment_id" in kwargs:
        kwargs["model"] = kwargs.pop("deployment_id")
    client = _get_client(credentials)
    return client.completions.create(
        prompt=prompt,
        **kwargs,
    )


@meter_api
@retry_api()
def create_embedding(
    input: str | TText | List[str] | List[TText],
    *_,
    **kwargs,
) -> object:
    """Create an embedding using the OpenAI API

    Args:
        input: The text to embed.
        kwargs: Other arguments to pass to the OpenAI API embedding call.
    Returns:
        object: The Embedding response from OpenAI

    """
    credentials_keys = [
        "api_key",
        "api_base",
        "organization",
        "api_type",
        "api_version",
    ]
    credentials = {k: kwargs.pop(k) for k in credentials_keys if k in kwargs}
    if "engine" in kwargs:
        kwargs["model"] = kwargs.pop("engine")
    client = _get_client(credentials)
    return client.embeddings.create(
        input=input,
        **kwargs,
    )


@dataclass
class OpenAIFunctionCall:
    """Represents a function call as generated by an OpenAI model

    Attributes:
        name: the name of the function that the LLM wants to call
        arguments: a stringified JSON object (unverified) containing `arg: value` pairs
    """

    name: str
    arguments: str


@dataclass
class OpenAIFunctionSpec:
    """Represents a "function" in OpenAI, which is mapped to a Command in Auto-GPT"""

    name: str
    description: str
    parameters: dict[str, ParameterSpec]

    @dataclass
    class ParameterSpec:
        name: str
        type: ParameterType | str
        description: Optional[str]
        required: bool = False

        def __post_init__(self) -> None:
            if not isinstance(self.type, ParameterType):
                self.type = ParameterType(self.type)

    @property
    def schema(self) -> dict[str, str | dict | list]:
        """Returns an OpenAI-consumable function specification"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type.value,
                        "description": param.description,
                    }
                    for param in self.parameters.values()
                },
                "required": [
                    param.name for param in self.parameters.values() if param.required
                ],
            },
        }

    @property
    def prompt_format(self) -> str:
        """Returns the function formatted similarly to the way OpenAI does it internally:
        https://community.openai.com/t/how-to-calculate-the-tokens-when-using-function-call/266573/18

        Example:
        ```ts
        // Get the current weather in a given location
        type get_current_weather = (_: {
        // The city and state, e.g. San Francisco, CA
        location: string,
        unit?: "celsius" | "fahrenheit",
        }) => any;
        ```
        """

        def param_signature(p_spec: OpenAIFunctionSpec.ParameterSpec) -> str:
            return (f"// {p_spec.description}\n" if p_spec.description else "") + (
                f"{p_spec.name}{'' if p_spec.required else '?'}: {p_spec.type.value},"
            )

        return "\n".join(
            [
                f"// {self.description}",
                f"type {self.name} = (_ :{{",
                *[param_signature(p) for p in self.parameters.values()],
                "}) => any;",
            ]
        )


def get_openai_command_specs(
    command_registry: CommandRegistry,
) -> list[OpenAIFunctionSpec]:
    """Get OpenAI-consumable function specs for the agent's available commands.
    see https://platform.openai.com/docs/guides/gpt/function-calling
    """
    return [
        OpenAIFunctionSpec(
            name=command.name,
            description=command.description,
            parameters={
                param.name: OpenAIFunctionSpec.ParameterSpec(
                    name=param.name,
                    type=param.type,
                    required=param.required,
                    description=param.description,
                )
                for param in command.parameters
            },
        )
        for command in command_registry.commands.values()
    ]


def count_openai_functions_tokens(
    functions: list[OpenAIFunctionSpec], for_model: str
) -> int:
    """Returns the number of tokens taken up by a set of function definitions

    Reference: https://community.openai.com/t/how-to-calculate-the-tokens-when-using-function-call/266573/18
    """
    from autogpt.llm.utils import count_string_tokens

    return count_string_tokens(
        f"# Tools\n\n## functions\n\n{format_function_specs_as_typescript_ns(functions)}",
        for_model,
    )


def format_function_specs_as_typescript_ns(functions: list[OpenAIFunctionSpec]) -> str:
    """Returns a function signature block in the format used by OpenAI internally:
    https://community.openai.com/t/how-to-calculate-the-tokens-when-using-function-call/266573/18

    For use with `count_string_tokens` to determine token usage of provided functions.

    Example:
    ```ts
    namespace functions {

    // Get the current weather in a given location
    type get_current_weather = (_: {
    // The city and state, e.g. San Francisco, CA
    location: string,
    unit?: "celsius" | "fahrenheit",
    }) => any;

    } // namespace functions
    ```
    """

    return (
        "namespace functions {\n\n"
        + "\n\n".join(f.prompt_format for f in functions)
        + "\n\n} // namespace functions"
    )
