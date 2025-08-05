"""Commands for managing the skill library."""

COMMAND_CATEGORY = "skill_library"
COMMAND_CATEGORY_TITLE = "Skill Library"

from autogpt.agents.agent import Agent
from autogpt.command_decorator import command
from autogpt.skills import reindex as reindex_skills_library


@command(
    "reindex_skills",
    "Rebuild the skill library index",
    {},
)
def reindex_skills(agent: Agent) -> str:
    """Reload skills from disk and reindex them."""

    reindex_skills_library()
    return "Skill library reindexed"
