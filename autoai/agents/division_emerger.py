"""Division Emerger: Automatic role division and task allocation via emergence.

Phase 19.2: Agents self-organize into roles based on:
  - Capability profiles (what each agent can do)
  - Current workload (load balancing)
  - Task requirements (skill matching)
  - Emergent role discovery (unsupervised clustering of capabilities)

No central planner — roles emerge from local interactions and capability signals.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from autoai.logs import logger


class RoleStability(Enum):
    FORMING = "forming"
    STABLE = "stable"
    ADAPTING = "adapting"


@dataclass
class CapabilityProfile:
    agent_id: str
    skills: dict[str, float] = field(default_factory=dict)
    capacity: float = 1.0
    current_load: float = 0.0
    preferred_roles: list[str] = field(default_factory=list)
    history_score: float = 0.5

    @property
    def available_capacity(self) -> float:
        return max(0.0, self.capacity - self.current_load)

    @property
    def skill_vector(self) -> list[float]:
        if not self.skills:
            return []
        return [v for v in self.skills.values()]


@dataclass
class EmergentRole:
    role_id: str
    name: str
    required_skills: dict[str, float] = field(default_factory=dict)
    assigned_agents: list[str] = field(default_factory=list)
    max_agents: int = 5
    min_agents: int = 1
    priority: float = 1.0
    stability: RoleStability = RoleStability.FORMING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def coverage(self) -> float:
        return min(1.0, len(self.assigned_agents) / self.min_agents) if self.min_agents > 0 else 1.0


@dataclass
class TaskRequirement:
    task_id: str
    required_skills: dict[str, float] = field(default_factory=dict)
    estimated_load: float = 0.5
    priority: float = 1.0
    deadline: str = ""


@dataclass
class Assignment:
    task_id: str
    agent_id: str
    role_id: str
    fitness: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DivisionEmerger:
    """Emergent role division and task allocation.

    Usage:
        emerger = DivisionEmerger()
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9, "review": 0.7}))
        emerger.register_agent(CapabilityProfile("a2", skills={"coding": 0.5, "testing": 0.9}))
        emerger.discover_roles()
        assignment = emerger.assign_task(TaskRequirement("t1", required_skills={"coding": 0.7}))
    """

    def __init__(
        self,
        skill_similarity_threshold: float = 0.7,
        load_balance_weight: float = 0.3,
        skill_match_weight: float = 0.5,
        history_weight: float = 0.2,
    ) -> None:
        self._skill_threshold = skill_similarity_threshold
        self._load_weight = load_balance_weight
        self._skill_weight = skill_match_weight
        self._history_weight = history_weight
        self._agents: dict[str, CapabilityProfile] = {}
        self._roles: dict[str, EmergentRole] = {}
        self._assignments: list[Assignment] = []
        self._all_skills: set[str] = set()
        self._role_counter = 0

    def register_agent(self, profile: CapabilityProfile) -> None:
        self._agents[profile.agent_id] = profile
        self._all_skills.update(profile.skills.keys())

    def update_load(self, agent_id: str, load: float) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].current_load = load

    def unregister_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        for role in self._roles.values():
            if agent_id in role.assigned_agents:
                role.assigned_agents.remove(agent_id)

    def discover_roles(self) -> list[EmergentRole]:
        if not self._agents:
            return []

        clusters = self._cluster_by_skills()
        new_roles = []

        for cluster_skills, agent_ids in clusters.items():
            role_name = self._infer_role_name(cluster_skills)
            existing = self._find_role_by_skills(cluster_skills)

            if existing:
                existing.assigned_agents = [aid for aid in existing.assigned_agents if aid in self._agents]
                for aid in agent_ids:
                    if aid not in existing.assigned_agents and len(existing.assigned_agents) < existing.max_agents:
                        existing.assigned_agents.append(aid)
                if existing.coverage >= 1.0:
                    existing.stability = RoleStability.STABLE
                else:
                    existing.stability = RoleStability.ADAPTING
            else:
                self._role_counter += 1
                skill_dict = {s: 1.0 for s in cluster_skills}
                role = EmergentRole(
                    role_id=f"role_{self._role_counter}",
                    name=role_name,
                    required_skills=skill_dict,
                    assigned_agents=list(agent_ids),
                    max_agents=max(3, len(agent_ids) * 2),
                    min_agents=1,
                )
                self._roles[role.role_id] = role
                new_roles.append(role)

        return new_roles

    def assign_task(self, requirement: TaskRequirement) -> Assignment | None:
        best_agent = None
        best_fitness = -1.0
        best_role = None

        for agent_id, profile in self._agents.items():
            if profile.available_capacity < requirement.estimated_load:
                continue

            skill_score = self._compute_skill_match(profile.skills, requirement.required_skills)
            load_score = profile.available_capacity / profile.capacity if profile.capacity > 0 else 0
            fitness = (
                self._skill_weight * skill_score
                + self._load_weight * load_score
                + self._history_weight * profile.history_score
            ) * requirement.priority

            if fitness > best_fitness:
                best_fitness = fitness
                best_agent = agent_id

        if best_agent is None:
            return None

        best_role = self._find_best_role_for_agent(best_agent)

        assignment = Assignment(
            task_id=requirement.task_id,
            agent_id=best_agent,
            role_id=best_role or "unassigned",
            fitness=best_fitness,
        )
        self._assignments.append(assignment)

        if best_agent in self._agents:
            self._agents[best_agent].current_load += requirement.estimated_load

        return assignment

    def rebalance(self) -> list[Assignment]:
        if not self._assignments:
            return []

        overloaded = [
            (aid, p) for aid, p in self._agents.items()
            if p.current_load > p.capacity * 0.9
        ]
        underloaded = [
            (aid, p) for aid, p in self._agents.items()
            if p.available_capacity > p.capacity * 0.3
        ]

        if not overloaded or not underloaded:
            return []

        reassigned = []
        for over_id, over_profile in overloaded:
            for assignment in reversed(self._assignments):
                if assignment.agent_id != over_id:
                    continue
                for under_id, under_profile in underloaded:
                    if under_profile.available_capacity > 0.3:
                        assignment.agent_id = under_id
                        over_profile.current_load -= 0.3
                        under_profile.current_load += 0.3
                        reassigned.append(assignment)
                        break
                if over_profile.current_load <= over_profile.capacity * 0.8:
                    break

        return reassigned

    def _cluster_by_skills(self) -> dict[frozenset, list[str]]:
        clusters: dict[frozenset, list[str]] = defaultdict(list)
        for agent_id, profile in self._agents.items():
            top_skill_names = {
                k for k, v in profile.skills.items()
                if v >= self._skill_threshold
            }
            if not top_skill_names:
                top_skill_names = set(list(profile.skills.keys())[:3])
            key = frozenset(top_skill_names)
            clusters[key].append(agent_id)
        return dict(clusters)

    @staticmethod
    def _infer_role_name(skills: frozenset) -> str:
        skill_list = sorted(skills)
        if "coding" in skill_list and "review" in skill_list:
            return "developer"
        if "coding" in skill_list:
            return "coder"
        if "testing" in skill_list:
            return "tester"
        if "review" in skill_list:
            return "reviewer"
        if "planning" in skill_list:
            return "planner"
        if "deployment" in skill_list or "devops" in skill_list:
            return "operator"
        if len(skill_list) <= 2:
            return f"{'_'.join(skill_list)}_specialist"
        return "generalist"

    def _find_role_by_skills(self, skills: frozenset) -> EmergentRole | None:
        for role in self._roles.values():
            if frozenset(role.required_skills.keys()) == skills:
                return role
        return None

    def _find_best_role_for_agent(self, agent_id: str) -> str | None:
        profile = self._agents.get(agent_id)
        if profile is None:
            return None
        best_role = None
        best_match = -1.0
        for role_id, role in self._roles.items():
            match = self._compute_skill_match(profile.skills, role.required_skills)
            if match > best_match:
                best_match = match
                best_role = role_id
        return best_role

    @staticmethod
    def _compute_skill_match(
        agent_skills: dict[str, float],
        required_skills: dict[str, float],
    ) -> float:
        if not required_skills:
            return 0.0
        total = 0.0
        for skill, req_level in required_skills.items():
            agent_level = agent_skills.get(skill, 0.0)
            total += min(1.0, agent_level / req_level) if req_level > 0 else 0.0
        return total / len(required_skills)

    @property
    def roles(self) -> dict[str, EmergentRole]:
        return dict(self._roles)

    @property
    def assignment_count(self) -> int:
        return len(self._assignments)

    def get_status(self) -> dict[str, Any]:
        return {
            "agents": len(self._agents),
            "roles": len(self._roles),
            "assignments": len(self._assignments),
            "all_skills": sorted(self._all_skills),
            "role_details": {
                rid: {"name": r.name, "agents": len(r.assigned_agents), "stability": r.stability.value}
                for rid, r in self._roles.items()
            },
        }


__all__ = [
    "DivisionEmerger",
    "CapabilityProfile",
    "EmergentRole",
    "RoleStability",
    "TaskRequirement",
    "Assignment",
]
