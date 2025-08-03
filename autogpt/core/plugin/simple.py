from importlib import import_module, util as importlib_util
import sys
from pathlib import Path
import zipimport
from typing import TYPE_CHECKING

from autogpt.core.plugin.base import (
    PluginLocation,
    PluginService,
    PluginStorageFormat,
    PluginStorageRoute,
)

if TYPE_CHECKING:
    from autogpt.core.plugin.base import PluginType


class SimplePluginService(PluginService):
    @staticmethod
    def get_plugin(plugin_location: dict | PluginLocation) -> "PluginType":
        """Get a plugin from a plugin location."""
        if isinstance(plugin_location, dict):
            plugin_location = PluginLocation.parse_obj(plugin_location)
        if plugin_location.storage_format == PluginStorageFormat.WORKSPACE:
            return SimplePluginService.load_from_workspace(
                plugin_location.storage_route
            )
        elif plugin_location.storage_format == PluginStorageFormat.INSTALLED_PACKAGE:
            return SimplePluginService.load_from_installed_package(
                plugin_location.storage_route
            )
        else:
            raise NotImplementedError(
                f"Plugin storage format {plugin_location.storage_format} is not implemented."
            )

    ####################################
    # Low-level storage format loaders #
    ####################################
    @staticmethod
    def load_from_file_path(plugin_route: PluginStorageRoute) -> "PluginType":
        """Load a plugin from a file path."""
        path_str, _, target = plugin_route.partition(":")
        if not path_str:
            raise ValueError("Plugin route must include a path")
        plugin_path = Path(path_str).expanduser()
        if not plugin_path.exists():
            raise FileNotFoundError(f"Plugin path '{plugin_path}' does not exist")

        if plugin_path.suffix == ".zip":
            if not target:
                raise ValueError(
                    "Zip plugin routes must include module and class, e.g. 'file.zip:pkg.Mod'"
                )
            module_name, _, class_name = target.rpartition(".")
            if not module_name:
                raise ValueError(
                    "Zip plugin routes must include module and class, e.g. 'file.zip:pkg.Mod'"
                )
            importer = zipimport.zipimporter(str(plugin_path))
            module = importer.load_module(module_name)
            return getattr(module, class_name)

        if plugin_path.is_dir():
            if not target:
                raise ValueError(
                    "Directory plugin routes must include module and class, e.g. 'path:pkg.Mod'"
                )
            module_name, _, class_name = target.rpartition(".")
            sys.path.insert(0, str(plugin_path.parent))
            try:
                module = import_module(module_name)
            finally:
                sys.path.pop(0)
            return getattr(module, class_name)

        # Treat as a single Python file
        module_name = plugin_path.stem
        spec = importlib_util.spec_from_file_location(module_name, str(plugin_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot import plugin from '{plugin_path}'")
        module = importlib_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        class_name = target or module_name
        return getattr(module, class_name)

    @staticmethod
    def load_from_import_path(plugin_route: PluginStorageRoute) -> "PluginType":
        """Load a plugin from an import path."""
        module_path, _, class_name = plugin_route.rpartition(".")
        return getattr(import_module(module_path), class_name)

    @staticmethod
    def resolve_name_to_path(
        plugin_route: PluginStorageRoute, path_type: str
    ) -> PluginStorageRoute:
        """Resolve a plugin name to a plugin path."""
        if path_type == "file":
            plugin_name = plugin_route
            search_roots = [Path.cwd(), Path.cwd() / "plugins"]
            extensions = ["", ".py", ".zip"]
            for root in search_roots:
                for ext in extensions:
                    candidate = root / f"{plugin_name}{ext}"
                    if candidate.exists():
                        return str(candidate)
            raise FileNotFoundError(
                f"Plugin '{plugin_name}' not found in workspace paths"
            )

        if path_type == "import":
            plugin_name = plugin_route
            try:
                import_module(plugin_name)
                return plugin_name
            except ModuleNotFoundError:
                alt_name = f"autogpt_plugins.{plugin_name}"
                import_module(alt_name)
                return alt_name

        raise ValueError(f"Unknown path type: {path_type}")

    #####################################
    # High-level storage format loaders #
    #####################################

    @staticmethod
    def load_from_workspace(plugin_route: PluginStorageRoute) -> "PluginType":
        """Load a plugin from the workspace."""
        plugin = SimplePluginService.load_from_file_path(plugin_route)
        return plugin

    @staticmethod
    def load_from_installed_package(plugin_route: PluginStorageRoute) -> "PluginType":
        plugin = SimplePluginService.load_from_import_path(plugin_route)
        return plugin
