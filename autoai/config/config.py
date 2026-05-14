"""存储不同脚本访问布尔状态的配置类。"""

from __future__ import annotations

import contextlib
import json
import os
import re
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast

import yaml

try:
    from auto_ai_plugin_template import AutoAIPluginTemplate
except ImportError:
    warnings.warn(
        "Optional dependency 'auto-ai-plugin-template' is not installed."
        " Install it with 'pip install auto-ai-plugin-template' to enable"
        " plugin support."
    )

    class AutoAIPluginTemplate:  # type: ignore
        """模板不可用时的回退插件基类。"""

        pass


from autoai.utils.ansi_colors import Fore
from pydantic import Field, validator

from autoai.core.configuration.schema import Configurable, SystemSettings
from autoai.llm.providers.openai import OPEN_AI_CHAT_MODELS
from autoai.plugins.plugins_config import PluginsConfig

AI_SETTINGS_FILE = "ai_settings.yaml"
AZURE_CONFIG_FILE = "azure.yaml"
PLUGINS_CONFIG_FILE = "plugins_config.yaml"
PROMPT_SETTINGS_FILE = "prompt_settings.yaml"

DEFAULT_LANGUAGE = "zh"

GPT_4_MODEL = "gpt-4"
GPT_3_MODEL = "gpt-3.5-turbo"


class Config(SystemSettings, arbitrary_types_allowed=True):
    name: str = "Auto-AI configuration"
    description: str = "Default configuration for the Auto-AI application."
    ########################
    # Applicati在设置s #
    ########################
    skip_news: bool = False
    skip_reprompt: bool = False
    authorise_key: str = "y"
    exit_key: str = "n"
    debug_mode: bool = False
    plain_output: bool = False
    chat_messages_enabled: bool = True
    language: str = DEFAULT_LANGUAGE
    # TTS configu比率n
    speak_mode: bool = False
    text_to_speech_provider: str = "gtts"
    streamelements_voice: str = "Brian"
    elevenlabs_voice_id: Optional[str] = None

    ##########################
    # 代理 Control Settings #
    ##########################
    # Paths
    ai_settings_file: str = AI_SETTINGS_FILE
    prompt_settings_file: str = PROMPT_SETTINGS_FILE
    workdir: Path = None
    workspace_path: Optional[Path] = None
    file_logger_path: Optional[Path] = None
    # 模型 configuration
    fast_llm: str = "gpt-3.5-turbo"
    smart_llm: str = "gpt-4-0314"
    temperature: float = 0
    openai_functions: bool = False
    embedding_model: str = "text-embedding-ada-002"
    browse_spacy_language_model: str = f"{DEFAULT_LANGUAGE}_core_web_sm"
    # 运行 循环 configuration
    continuous_mode: bool = False
    continuous_limit: int = 0
    max_repeated_commands: int = 3
    repeat_window: float = 30.0
    # Self 开发 循环
    self_develop_enabled: bool = False
    self_develop_interval: float = 300.0

    ##########
    # 内存 #
    ##########
    memory_backend: str = "json_file"
    memory_index: str = "auto-ai-memory"
    use_long_term_memory: bool = False
    long_term_memory_threshold: int = 10
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    wipe_redis_on_start: bool = True

    ####################
    # 技能 库 DB #
    ####################
    skill_db_provider: str = "memory"
    use_librarian: bool = True

    ############
    # Commands #
    ############
    # General
    disabled_command_categories: list[str] = Field(default_factory=list)
    # File ops
    restrict_to_workspace: bool = True
    allow_downloads: bool = False
    # Shell 命令s
    shell_command_control: str = "denylist"
    execute_local_commands: bool = False
    shell_denylist: list[str] = Field(default_factory=lambda: ["sudo", "su"])
    shell_allowlist: list[str] = Field(default_factory=list)
    # Text 到image
    image_provider: Optional[str] = None
    huggingface_image_model: str = "CompVis/stable-diffusion-v1-4"
    sd_webui_url: Optional[str] = "http://localhost:7860"
    image_size: int = 256
    # Audio 到text
    audio_to_text_provider: str = "huggingface"
    huggingface_audio_to_text_model: str = "openai/whisper-large-v2"
    # Web b行sing
    selenium_web_browser: str = "chrome"
    selenium_headless: bool = True
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"

    ###################
    # 插件 Settings #
    ###################
    plugins_dir: str = "plugins"
    plugins_config_file: str = PLUGINS_CONFIG_FILE
    plugins_config: PluginsConfig = Field(
        default_factory=lambda: PluginsConfig(plugins={})
    )
    plugins: list[AutoAIPluginTemplate] = Field(default_factory=list, exclude=True)
    plugins_allowlist: list[str] = Field(default_factory=list)
    plugins_denylist: list[str] = Field(default_factory=list)
    plugins_openai: list[str] = Field(default_factory=list)

    ###############
    # Credentials #
    ###############
    # 打开AI
    openai_api_key: Optional[str] = None
    openai_api_type: Optional[str] = None
    openai_api_base: Optional[str] = None
    openai_api_version: Optional[str] = None
    openai_organization: Optional[str] = None
    use_azure: bool = False
    azure_config_file: Optional[str] = AZURE_CONFIG_FILE
    azure_model_to_deployment_id_map: Optional[Dict[str, str]] = None
    # Elevenlabs
    elevenlabs_api_key: Optional[str] = None
    # Github
    github_api_key: Optional[str] = None
    github_username: Optional[str] = None
    # Google
    google_api_key: Optional[str] = None
    google_custom_search_engine_id: Optional[str] = None
    # Huggingface
    huggingface_api_token: Optional[str] = None
    # S表 Diffusion
    sd_webui_auth: Optional[str] = None

    @validator("plugins", each_item=True)
    def validate_plugins(cls, p: AutoAIPluginTemplate | Any):
        assert issubclass(
            p.__class__, AutoAIPluginTemplate
        ), f"{p} does not subclass AutoAIPluginTemplate"
        assert (
            p.__class__.__name__ != "AutoAIPluginTemplate"
        ), f"Plugins must subclass AutoAIPluginTemplate; {p} is a template instance"
        return p

    @validator("openai_functions")
    def validate_openai_functions(cls, v: bool, values: dict[str, Any]):
        if v:
            smart_llm = values["smart_llm"]
            assert OPEN_AI_CHAT_MODELS[smart_llm].supports_functions, (
                f"Model {smart_llm} does not support OpenAI Functions. "
                "Please disable OPENAI_FUNCTIONS or choose a suitable model."
            )

    def get_openai_credentials(
        self, model: str, language: str = DEFAULT_LANGUAGE
    ) -> dict[str, str]:
        language = language or DEFAULT_LANGUAGE
        credentials = {
            "api_key": self.openai_api_key,
            "api_base": self.openai_api_base,
            "organization": self.openai_organization,
        }
        if self.use_azure:
            azure_credentials = self.get_azure_credentials(model, language)
            credentials.update(azure_credentials)
        return credentials

    def get_azure_credentials(
        self, model: str, language: str = DEFAULT_LANGUAGE
    ) -> dict[str, str]:
        language = language or DEFAULT_LANGUAGE
        """Get the kwargs for the Azure API."""

        # 修复 --gpt3only and --gpt4only in combination with Azure
        fast_llm = (
            self.fast_llm
            if not (
                self.fast_llm == self.smart_llm
                and self.fast_llm.startswith(GPT_4_MODEL)
            )
            else f"not_{self.fast_llm}"
        )
        smart_llm = (
            self.smart_llm
            if not (
                self.smart_llm == self.fast_llm
                and self.smart_llm.startswith(GPT_3_MODEL)
            )
            else f"not_{self.smart_llm}"
        )

        deployment_id = {
            fast_llm: self.azure_model_to_deployment_id_map.get(
                "fast_llm_deployment_id",
                self.azure_model_to_deployment_id_map.get(
                    "fast_llm_model_deployment_id"  # 向后兼容
                ),
            ),
            smart_llm: self.azure_model_to_deployment_id_map.get(
                "smart_llm_deployment_id",
                self.azure_model_to_deployment_id_map.get(
                    "smart_llm_model_deployment_id"  # 向后兼容
                ),
            ),
            self.embedding_model: self.azure_model_to_deployment_id_map.get(
                "embedding_model_deployment_id"
            ),
        }.get(model, None)

        kwargs = {
            "api_type": self.openai_api_type,
            "api_base": self.openai_api_base,
            "api_version": self.openai_api_version,
        }
        if model == self.embedding_model:
            kwargs["engine"] = deployment_id
        else:
            kwargs["deployment_id"] = deployment_id
        return kwargs

    def apply_overlay(self, file: Path | str) -> None:
        """应用JSON配置覆盖的覆盖值。"""
        overlay_path = Path(file)
        if not overlay_path.is_file():
            raise FileNotFoundError(file)
        with overlay_path.open() as f:
            data = json.load(f)
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


class ConfigBuilder(Configurable[Config]):
    default_settings = Config()

    @classmethod
    def build_config_from_env(cls, workdir: Path) -> Config:
        """初始化Config类"""
        config_dict: dict[str, Any] = {
            "workdir": workdir,
            "authorise_key": os.getenv("AUTHORISE_COMMAND_KEY"),
            "exit_key": os.getenv("EXIT_KEY"),
            "plain_output": os.getenv("PLAIN_OUTPUT", "False") == "True",
            "shell_command_control": os.getenv("SHELL_COMMAND_CONTROL"),
            "ai_settings_file": os.getenv("AI_SETTINGS_FILE", AI_SETTINGS_FILE),
            "prompt_settings_file": os.getenv(
                "PROMPT_SETTINGS_FILE", PROMPT_SETTINGS_FILE
            ),
            "fast_llm": os.getenv("FAST_LLM", os.getenv("FAST_LLM_MODEL")),
            "smart_llm": os.getenv("SMART_LLM", os.getenv("SMART_LLM_MODEL")),
            "embedding_model": os.getenv("EMBEDDING_MODEL"),
            "browse_spacy_language_model": os.getenv(
                "BROWSE_SPACY_LANGUAGE_MODEL", f"{DEFAULT_LANGUAGE}_core_web_sm"
            ),
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "use_azure": os.getenv("USE_AZURE") == "True",
            "azure_config_file": os.getenv("AZURE_CONFIG_FILE", AZURE_CONFIG_FILE),
            "execute_local_commands": os.getenv("EXECUTE_LOCAL_COMMANDS", "True")
            == "True",
            "restrict_to_workspace": os.getenv("RESTRICT_TO_WORKSPACE", "True")
            == "True",
            "openai_functions": os.getenv("OPENAI_FUNCTIONS", "False") == "True",
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
            "streamelements_voice": os.getenv("STREAMELEMENTS_VOICE"),
            "text_to_speech_provider": os.getenv("TEXT_TO_SPEECH_PROVIDER"),
            "github_api_key": os.getenv("GITHUB_API_KEY"),
            "github_username": os.getenv("GITHUB_USERNAME"),
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "image_provider": os.getenv("IMAGE_PROVIDER"),
            "huggingface_api_token": os.getenv("HUGGINGFACE_API_TOKEN"),
            "huggingface_image_model": os.getenv("HUGGINGFACE_IMAGE_MODEL"),
            "audio_to_text_provider": os.getenv("AUDIO_TO_TEXT_PROVIDER"),
            "huggingface_audio_to_text_model": os.getenv(
                "HUGGINGFACE_AUDIO_TO_TEXT_MODEL"
            ),
            "sd_webui_url": os.getenv("SD_WEBUI_URL"),
            "sd_webui_auth": os.getenv("SD_WEBUI_AUTH"),
            "selenium_web_browser": os.getenv("USE_WEB_BROWSER"),
            "selenium_headless": os.getenv("HEADLESS_BROWSER", "True") == "True",
            "user_agent": os.getenv("USER_AGENT"),
            "memory_backend": os.getenv("MEMORY_BACKEND"),
            "memory_index": os.getenv("MEMORY_INDEX"),
            "use_long_term_memory": os.getenv("USE_LONG_TERM_MEMORY", "False")
            == "True",
            "long_term_memory_threshold": os.getenv("LONG_TERM_MEMORY_THRESHOLD"),
            "redis_host": os.getenv("REDIS_HOST"),
            "redis_password": os.getenv("REDIS_PASSWORD"),
            "wipe_redis_on_start": os.getenv("WIPE_REDIS_ON_START", "True") == "True",
            "skill_db_provider": os.getenv("SKILL_DB_PROVIDER"),
            "use_librarian": os.getenv("USE_LIBRARIAN", "True") == "True",
            "plugins_dir": os.getenv("PLUGINS_DIR"),
            "plugins_config_file": os.getenv(
                "PLUGINS_CONFIG_FILE", PLUGINS_CONFIG_FILE
            ),
            "chat_messages_enabled": os.getenv("CHAT_MESSAGES_ENABLED") == "True",
            "self_develop_enabled": os.getenv("SELF_DEVELOP", "False") == "True",
        }

        config_dict["disabled_command_categories"] = _safe_split(
            os.getenv("DISABLED_COMMAND_CATEGORIES")
        )

        config_dict["shell_denylist"] = _safe_split(
            os.getenv("SHELL_DENYLIST", os.getenv("DENY_COMMANDS"))
        )
        config_dict["shell_allowlist"] = _safe_split(
            os.getenv("SHELL_ALLOWLIST", os.getenv("ALLOW_COMMANDS"))
        )

        config_dict["google_custom_search_engine_id"] = os.getenv(
            "GOOGLE_CUSTOM_SEARCH_ENGINE_ID", os.getenv("CUSTOM_SEARCH_ENGINE_ID")
        )

        config_dict["elevenlabs_voice_id"] = os.getenv(
            "ELEVENLABS_VOICE_ID", os.getenv("ELEVENLABS_VOICE_1_ID")
        )
        if not config_dict["text_to_speech_provider"]:
            if os.getenv("USE_MAC_OS_TTS"):
                default_tts_provider = "macos"
            elif config_dict["elevenlabs_api_key"]:
                default_tts_provider = "elevenlabs"
            elif os.getenv("USE_BRIAN_TTS"):
                default_tts_provider = "streamelements"
            else:
                default_tts_provider = "gtts"
            config_dict["text_to_speech_provider"] = default_tts_provider

        config_dict["plugins_allowlist"] = _safe_split(os.getenv("ALLOWLISTED_PLUGINS"))
        config_dict["plugins_denylist"] = _safe_split(os.getenv("DENYLISTED_PLUGINS"))

        with contextlib.suppress(TypeError):
            config_dict["image_size"] = int(cast(str, os.getenv("IMAGE_SIZE")))
        with contextlib.suppress(TypeError):
            config_dict["redis_port"] = int(cast(str, os.getenv("REDIS_PORT")))
        with contextlib.suppress(TypeError):
            config_dict["temperature"] = float(cast(str, os.getenv("TEMPERATURE")))
        with contextlib.suppress(TypeError):
            config_dict["long_term_memory_threshold"] = int(
                cast(str, config_dict["long_term_memory_threshold"])
            )
        with contextlib.suppress(TypeError):
            interval_val = os.getenv("SELF_DEVELOP_INTERVAL")
            if interval_val is not None:
                config_dict["self_develop_interval"] = float(interval_val)

        if config_dict["use_azure"]:
            azure_config = cls.load_azure_config(
                workdir / Path(cast(str, config_dict["azure_config_file"]))
            )
            config_dict.update(azure_config)

        elif os.getenv("OPENAI_API_BASE_URL"):
            config_dict["openai_api_base"] = os.getenv("OPENAI_API_BASE_URL")

        openai_organization = os.getenv("OPENAI_ORGANIZATION")
        if openai_organization is not None:
            config_dict["openai_organization"] = openai_organization

        config_dict_without_none_values = {
            k: v for k, v in config_dict.items() if v is not None
        }

        config = cls.build_agent_configuration(config_dict_without_none_values)

        # 集合 secondary config variables (that depend on other config variables)

        config.plugins_config = PluginsConfig.load_config(
            config.workdir / config.plugins_config_file,
            config.plugins_denylist,
            config.plugins_allowlist,
        )

        return config

    @classmethod
    def load_azure_config(cls, config_file: Path) -> Dict[str, str]:
        """
        Loads the configuration parameters for Azure hosting from the specified file
          path as a yaml file.

        Parameters:
            config_file (Path): The path to the config yaml file.

        Returns:
            Dict
        """
        with open(config_file) as file:
            config_params = yaml.load(file, Loader=yaml.FullLoader) or {}

        return {
            "openai_api_type": config_params.get("azure_api_type", "azure"),
            "openai_api_base": config_params.get("azure_api_base", ""),
            "openai_api_version": config_params.get(
                "azure_api_version", "2023-03-15-preview"
            ),
            "azure_model_to_deployment_id_map": config_params.get(
                "azure_model_map", {}
            ),
        }


def check_openai_api_key(config: Config) -> None:
    """检查OpenAI API密钥是否在config.py或环境变量中设置。"""
    if not config.openai_api_key:
        print(
            Fore.RED
            + "Please set your OpenAI API key in .env or as an environment variable."
            + Fore.RESET
        )
        print("You can get your key from https://platform.openai.com/account/api-keys")
        openai_api_key = input(
            "If you do have the key, please enter your OpenAI API key now:\n"
        )
        key_pattern = r"^sk-\w{48}"
        openai_api_key = openai_api_key.strip()
        if re.search(key_pattern, openai_api_key):
            os.environ["OPENAI_API_KEY"] = openai_api_key
            config.openai_api_key = openai_api_key
            print(
                Fore.GREEN
                + "OpenAI API key successfully set!\n"
                + Fore.YELLOW
                + "NOTE: The API key you've set is only temporary.\n"
                + "For longer sessions, please set it in .env file"
                + Fore.RESET
            )
        else:
            print("Invalid OpenAI API key!")
            exit(1)


def _safe_split(s: Union[str, None], sep: str = ",") -> list[str]:
    """按分隔符拆分字符串。如字符串为None则返回空列表。"""
    if s is None:
        return []
    return s.split(sep)
