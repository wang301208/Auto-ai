from __future__ import annotations

"""Agent wrapper around :class:`SkillLibrary` for managing skills."""

import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from autogpt.config import Config
from autogpt.logs import logger
from autogpt.plugins.loader import PluginMetaValidationError, load_plugin_meta
from autogpt.plugins.models import SourceCodeAccessPolicy
from autogpt.plugins.library import PluginLibrary
from autogpt.telemetry import telemetry
from autogpt.telemetry.audit import log_denied_access

from .library import SkillLibrary, SkillMetadata


class LibrarianAgent:
    """High level interface for managing the skill library."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.skill_library = SkillLibrary(self.config)
        storage = self.skill_library.storage_path
        self.plugin_library = PluginLibrary(self.config, Path(self.config.plugins_dir))
        if not any(storage.rglob("skill.json")):
            logger.warn(
                "No existing skill index found at %s; starting with empty library",
                storage,
            )
        # Cache search results to avoid redundant library queries for repeated
        # requests. This keeps ``find_skill`` simple and synchronous while
        # still improving performance for common lookups.
        self._search_cache: Dict[Tuple[str, int], List[dict]] = {}
        self._plugin_cache: Dict[Tuple[str, int], List[str]] = {}

    # ------------------------------------------------------------------
    def find_skill(self, query: str, top_k: int = 3) -> List[dict]:
        """Search for skills matching ``query`` and return their metadata.

        Results are cached by ``query``/``top_k`` combination so repeated
        invocations avoid hitting the underlying :class:`SkillLibrary`.
        """

        cache_key = (query, top_k)
        if cache_key in self._search_cache:
            cached_results = self._search_cache[cache_key]
            telemetry.increment(
                "find_skill.success" if cached_results else "find_skill.failure"
            )
            return cached_results

        skills = self.skill_library.search(query, top_k=top_k)
        top_metadata = asdict(skills[0].metadata) if skills else None
        logger.debug(f"Skill search query: {query}, top result: {top_metadata}")

        required_fields = ("skill_name", "version", "parameters")
        results: List[dict] = []
        for skill in skills:
            metadata = getattr(skill, "metadata", None)
            if metadata is None:
                logger.warn("Skipping skill with missing metadata: %s", skill)
                continue

            if isinstance(metadata, dict):
                meta_dict = metadata
            else:
                try:
                    meta_dict = asdict(metadata)
                except Exception:
                    logger.warn("Skipping skill with invalid metadata: %s", metadata)
                    continue

            if not all(meta_dict.get(field) for field in required_fields):
                logger.warn(
                    "Skipping skill with missing required fields %s: %s",
                    required_fields,
                    meta_dict,
                )
                continue

            results.append(meta_dict)

        self._search_cache[cache_key] = results
        telemetry.increment("find_skill.success" if results else "find_skill.failure")
        return results

    # ------------------------------------------------------------------
    def find_plugin(self, query: str, top_k: int = 3) -> List[str]:
        """Search for plugins matching ``query`` and return their identifiers."""

        cache_key = (query, top_k)
        if cache_key in self._plugin_cache:
            cached = self._plugin_cache[cache_key]
            telemetry.increment(
                "find_plugin.success" if cached else "find_plugin.failure"
            )
            return cached

        plugin_ids = self.plugin_library.search(query, top_k=top_k)
        self._plugin_cache[cache_key] = plugin_ids
        telemetry.increment("find_plugin.success" if plugin_ids else "find_plugin.failure")
        return plugin_ids

    # ------------------------------------------------------------------
    def add_skill(self, skill_metadata: dict, skill_code_path: str) -> bool:
        """Add a new skill to the library.

        Parameters
        ----------
        skill_metadata: dict
            Metadata describing the skill. Must conform to :class:`SkillMetadata`.
        skill_code_path: str
            Path to the Python file containing the skill's code.
        """

        try:
            metadata = SkillMetadata(**skill_metadata)
        except TypeError as err:
            logger.error(f"Invalid skill metadata: {err}")
            raise ValueError("Invalid skill metadata") from err

        source = Path(skill_code_path)
        if not source.is_file():
            logger.error(f"Skill code path is not a file: {source}")
            raise FileNotFoundError(f"Skill code path is not a file: {source}")

        # Copy the code into the skill library directory
        dest_dir = (
            self.skill_library.storage_path
            / f"{metadata.skill_name}_{metadata.version}"
        )
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / "main.py"
            shutil.copy2(source, dest_file)
            code = dest_file.read_text(encoding="utf-8")
        except OSError as err:
            logger.error(
                f"Failed to copy skill code from {source} to {dest_dir}: {err}"
            )
            raise

        try:
            self.skill_library.add_skill(
                name=metadata.skill_name,
                version=metadata.version,
                code=code,
                parameters=metadata.parameters,
                description=metadata.description,
                tags=metadata.tags,
                dependencies_file=metadata.dependencies_file,
                entry_point=metadata.entry_point,
                return_type=metadata.return_type,
                author_agent=metadata.author_agent,
                creation_timestamp=metadata.creation_timestamp,
                approved_by=metadata.approved_by,
                approval_timestamp=metadata.approval_timestamp,
            )
            return True
        except Exception as err:
            logger.error(f"Failed to register skill {metadata.skill_name}: {err}")
            raise RuntimeError(
                f"Failed to register skill {metadata.skill_name}"
            ) from err

    # ------------------------------------------------------------------
    def get_source_code_path(
        self, plugin_name: str, requester: str | None = None
    ) -> str | None:
        """Return the local source path for a plugin if access is allowed.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin whose source path is requested.
        requester: str | None
            Name of the agent requesting access, used for audit logging.
        """

        plugins_dir = Path(self.skill_library.config.plugins_dir)
        for meta_file in plugins_dir.rglob("*.json"):
            try:
                meta = load_plugin_meta(meta_file)
            except PluginMetaValidationError:
                logger.warn("Skipping invalid plugin metadata: %s", meta_file)
                continue

            if meta.name != plugin_name:
                continue

            policy = meta.source_code_access_policy
            if policy == SourceCodeAccessPolicy.ALLOWED_FOR_READ_ONLY:
                return meta.underlying_library.local_source_path

            log_denied_access(plugin_name, requester or self.__class__.__name__)
            telemetry.increment("get_source_code_path.denied")
            return None

        logger.warn("Plugin '%s' not found", plugin_name)
        return None
