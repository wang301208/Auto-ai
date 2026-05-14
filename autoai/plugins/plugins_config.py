from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml
from pydantic import BaseModel

from autoai.logs import logger
from autoai.plugins.plugin_config import PluginConfig


class PluginsConfig(BaseModel):
    """保存所有插件配置的类"""

    plugins: dict[str, PluginConfig]

    def __repr__(self):
        return f"PluginsConfig({self.plugins})"

    def get(self, name: str) -> Union[PluginConfig, None]:
        return self.plugins.get(name)

    def is_enabled(self, name) -> bool:
        plugin_config = self.plugins.get(name)
        return plugin_config is not None and plugin_config.enabled

    @classmethod
    def load_config(
        cls,
        plugins_config_file: Path,
        plugins_denylist: list[str],
        plugins_allowlist: list[str],
    ) -> "PluginsConfig":
        empty_config = cls(plugins={})

        try:
            config_data = cls.deserialize_config_file(
                plugins_config_file,
                plugins_denylist,
                plugins_allowlist,
            )
            if type(config_data) != dict:
                logger.error(
                    f"Expected plugins config to be a dict, got {type(config_data)}, continuing without plugins"
                )
                return empty_config
            return cls(plugins=config_data)

        except BaseException as e:
            logger.error(
                f"Plugin config is invalid, continuing without plugins. Error: {e}"
            )
            return empty_config

    @classmethod
    def deserialize_config_file(
        cls,
        plugins_config_file: Path,
        plugins_denylist: list[str],
        plugins_allowlist: list[str],
    ) -> dict[str, PluginConfig]:
        if not plugins_config_file.is_file():
            logger.warn("plugins_config.yaml does not exist, creating base config.")
            cls.create_empty_plugins_config(
                plugins_config_file,
                plugins_denylist,
                plugins_allowlist,
            )

        with open(plugins_config_file, "r") as f:
            plugins_config = yaml.load(f, Loader=yaml.FullLoader)

        plugins = {}
        for name, plugin in plugins_config.items():
            if type(plugin) == dict:
                plugins[name] = PluginConfig(
                    name=name,
                    enabled=plugin.get("enabled", False),
                    config=plugin.get("config", {}),
                )
            elif type(plugin) == PluginConfig:
                plugins[name] = plugin
            else:
                raise ValueError(f"Invalid plugin config data type: {type(plugin)}")
        return plugins

    @staticmethod
    def create_empty_plugins_config(
        plugins_config_file: Path,
        plugins_denylist: list[str],
        plugins_allowlist: list[str],
    ):
        """创建空的plugins_config.yaml文件。用旧环境变量值填充。"""
        base_config = {}

        logger.debug(f"Legacy plug在deny列表: {plugins_deny列表}")
        logger.debug(f"Legacy plug在allow列表: {plugins_allow列表}")

        # 后端wards-compatibility shim
        for plugin_name in plugins_denylist:
            base_config[plugin_name] = {"enabled": False, "config": {}}

        for plugin_name in plugins_allowlist:
            base_config[plugin_name] = {"enabled": True, "config": {}}

        logger.debug(f"已构建基础插件配置: {base_config}")

        logger.debug(f"正在创建插件配置文件 {plugins_config_file}")
        with open(plugins_config_file, "w+") as f:
            f.write(yaml.dump(base_config))
            return base_config
