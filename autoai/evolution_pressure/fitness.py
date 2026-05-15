from __future__ import annotations

import time
import random
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class FitnessDimension(Enum):
    EFFICIENCY = "efficiency"
    ROBUSTNESS = "robustness"
    INNOVATION = "innovation"
    COLLABORATION = "collaboration"
    SAFETY = "safety"


@dataclass
class FitnessReport:
    agent_id: str
    scores: dict[str, float] = field(default_factory=dict)
    overall: float = 0.0
    generation: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_viable(self) -> bool:
        return self.overall >= 0.3 and all(v >= 0.1 for v in self.scores.values())

    @property
    def strongest_dimension(self) -> str:
        if not self.scores:
            return "unknown"
        return max(self.scores, key=self.scores.get)


@dataclass
class NicheSpec:
    name: str
    required_dimensions: dict[str, float] = field(default_factory=dict)
    optimal_dimensions: dict[str, float] = field(default_factory=dict)
    population_cap: int = 5

    def compatibility(self, scores: dict[str, float]) -> float:
        if not self.required_dimensions:
            return 0.5
        compat_scores = []
        for dim, min_val in self.required_dimensions.items():
            actual = scores.get(dim, 0.0)
            compat_scores.append(min(1.0, actual / min_val) if min_val > 0 else 1.0)
        return sum(compat_scores) / len(compat_scores)


@dataclass
class AgentGenome:
    agent_id: str
    strategy_params: dict[str, Any] = field(default_factory=dict)
    fitness_history: list[float] = field(default_factory=list)
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    mutations: list[str] = field(default_factory=list)

    @property
    def adapted_fitness(self) -> float:
        if not self.fitness_history:
            return 0.5
        recent = self.fitness_history[-5:]
        weights = [0.5 ** i for i in range(len(recent))]
        weighted_sum = sum(f * w for f, w in zip(recent, reversed(weights)))
        return weighted_sum / sum(weights)

    def mutate(self, rate: float = 0.1) -> "AgentGenome":
        new_params = dict(self.strategy_params)
        mutations = []
        for key in new_params:
            if random.random() < rate:
                if isinstance(new_params[key], float):
                    delta = random.gauss(0, 0.1)
                    new_params[key] = max(0.0, min(1.0, new_params[key] + delta))
                    mutations.append(f"mutate:{key}")
        return AgentGenome(
            agent_id=hashlib.sha256(f"{self.agent_id}:mut:{time.time()}".encode()).hexdigest()[:12],
            strategy_params=new_params,
            fitness_history=[],
            generation=self.generation + 1,
            parent_ids=[self.agent_id],
            mutations=mutations,
        )

    @staticmethod
    def crossover(parent_a: "AgentGenome", parent_b: "AgentGenome") -> "AgentGenome":
        child_params = {}
        all_keys = set(parent_a.strategy_params) | set(parent_b.strategy_params)
        for key in all_keys:
            va = parent_a.strategy_params.get(key, 0.5)
            vb = parent_b.strategy_params.get(key, 0.5)
            child_params[key] = va if random.random() < 0.5 else vb
        return AgentGenome(
            agent_id=hashlib.sha256(f"xover:{parent_a.agent_id}:{parent_b.agent_id}:{time.time()}".encode()).hexdigest()[:12],
            strategy_params=child_params,
            fitness_history=[],
            generation=max(parent_a.generation, parent_b.generation) + 1,
            parent_ids=[parent_a.agent_id, parent_b.agent_id],
        )


class FitnessEvaluator:
    """多维度适应度评估器。"""

    def __init__(self, weights: dict[str, float] | None = None):
        self._weights = weights or {
            FitnessDimension.EFFICIENCY.value: 0.25,
            FitnessDimension.ROBUSTNESS.value: 0.25,
            FitnessDimension.INNOVATION.value: 0.2,
            FitnessDimension.COLLABORATION.value: 0.15,
            FitnessDimension.SAFETY.value: 0.15,
        }
        self._records: dict[str, dict[str, list[float]]] = {}

    def record(self, agent_id: str, dimension: str, value: float) -> None:
        self._records.setdefault(agent_id, {}).setdefault(dimension, []).append(value)

    def evaluate(self, agent_id: str, generation: int = 0) -> FitnessReport:
        agent_records = self._records.get(agent_id, {})
        scores = {}
        for dim in self._weights:
            values = agent_records.get(dim, [0.5])
            recent = values[-10:]
            scores[dim] = sum(recent) / len(recent) if recent else 0.5
        overall = sum(scores.get(dim, 0.5) * w for dim, w in self._weights.items())
        return FitnessReport(
            agent_id=agent_id,
            scores=scores,
            overall=overall,
            generation=generation,
        )


class EvolutionPressure:
    """进化压力系统: 自然选择作用于Agent群体。"""

    def __init__(self, selection_threshold: float = 0.3):
        self.selection_threshold = selection_threshold
        self._evaluator = FitnessEvaluator()
        self._genomes: dict[str, AgentGenome] = {}
        self._niches: list[NicheSpec] = []
        self._generation = 0
        self._selections: list[dict] = []

    def register_genome(self, genome: AgentGenome) -> None:
        self._genomes[genome.agent_id] = genome

    def add_niche(self, niche: NicheSpec) -> None:
        self._niches.append(niche)

    def record_fitness(self, agent_id: str, dimension: str, value: float) -> None:
        self._evaluator.record(agent_id, dimension, value)

    def select(self) -> dict[str, bool]:
        """自然选择: 基于适应度决定存活。"""
        results = {}
        for aid in self._genomes:
            report = self._evaluator.evaluate(aid, self._generation)
            self._genomes[aid].fitness_history.append(report.overall)
            survival_prob = min(1.0, report.overall / self.selection_threshold)
            survived = random.random() < survival_prob
            results[aid] = survived
            if not survived:
                logger.info(f"自然选择淘汰: {aid} (适应度={report.overall:.3f})")
        self._selections.append({
            "generation": self._generation,
            "survived": sum(1 for v in results.values() if v),
            "eliminated": sum(1 for v in results.values() if not v),
        })
        self._generation += 1
        return results

    def evolve(self) -> list[AgentGenome]:
        """一轮进化: 选择+变异+交叉。"""
        survivors = []
        for aid, genome in self._genomes.items():
            report = self._evaluator.evaluate(aid, self._generation)
            if report.is_viable:
                survivors.append(genome)
        offspring = []
        for genome in survivors:
            child = genome.mutate(rate=0.1)
            offspring.append(child)
        if len(survivors) >= 2:
            for _ in range(max(1, len(survivors) // 2)):
                a, b = random.sample(survivors, 2)
                child = AgentGenome.crossover(a, b)
                offspring.append(child)
        for child in offspring:
            self._genomes[child.agent_id] = child
        self._generation += 1
        return offspring

    def niche_assignment(self, agent_id: str) -> str | None:
        if agent_id not in self._genomes:
            return None
        report = self._evaluator.evaluate(agent_id)
        best_niche = None
        best_compat = 0.0
        for niche in self._niches:
            compat = niche.compatibility(report.scores)
            if compat > best_compat:
                best_compat = compat
                best_niche = niche.name
        return best_niche

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "generation": self._generation,
            "population": len(self._genomes),
            "niches": len(self._niches),
            "selections": len(self._selections),
        }
