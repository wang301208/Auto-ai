from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EdgeType(Enum):
    CAUSAL = "causal"
    CONFOUNDED = "confounded"
    MEDIATED = "mediated"


@dataclass
class CausalNode:
    name: str
    domain: str = ""
    observable: bool = True
    interventions: int = 0
    observations: int = 0


@dataclass
class CausalEdge:
    source: str
    target: str
    edge_type: EdgeType = EdgeType.CAUSAL
    strength: float = 0.5
    confidence: float = 0.0
    evidence_count: int = 0


@dataclass
class InterventionResult:
    target: str
    intervention: str
    original_value: Any = None
    intervened_value: Any = None
    effect_size: float = 0.0
    confidence: float = 0.0
    confounders_controlled: list[str] = field(default_factory=list)


class CausalGraph:
    """有向无环图(DAG)表示变量间的因果依赖关系。"""

    def __init__(self):
        self._nodes: dict[str, CausalNode] = {}
        self._edges: list[CausalEdge] = []
        self._adj: dict[str, list[str]] = {}

    def add_node(self, name: str, domain: str = "", observable: bool = True) -> CausalNode:
        node = CausalNode(name=name, domain=domain, observable=observable)
        self._nodes[name] = node
        self._adj.setdefault(name, [])
        return node

    def add_edge(self, source: str, target: str, strength: float = 0.5,
                 edge_type: EdgeType = EdgeType.CAUSAL) -> CausalEdge:
        if source not in self._nodes:
            self.add_node(source)
        if target not in self._nodes:
            self.add_node(target)
        edge = CausalEdge(source=source, target=target, edge_type=edge_type, strength=strength)
        self._edges.append(edge)
        self._adj.setdefault(source, []).append(target)
        if self._has_cycle():
            self._edges.pop()
            self._adj[source].pop()
            logger.warning(f"拒绝添加边{source}->{target}: 会创建环")
            return CausalEdge(source=source, target=target, strength=0)
        return edge

    def _has_cycle(self) -> bool:
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(v: str) -> bool:
            visited.add(v)
            rec_stack.add(v)
            for neighbor in self._adj.get(v, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(v)
            return False

        for node in self._nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def get_parents(self, node: str) -> list[str]:
        return [e.source for e in self._edges if e.target == node]

    def get_children(self, node: str) -> list[str]:
        return self._adj.get(node, [])

    def get_ancestors(self, node: str) -> set[str]:
        ancestors: set[str] = set()
        queue = list(self.get_parents(node))
        while queue:
            n = queue.pop(0)
            if n not in ancestors:
                ancestors.add(n)
                queue.extend(self.get_parents(n))
        return ancestors

    def get_confounders(self, cause: str, effect: str) -> list[str]:
        cause_ancestors = self.get_ancestors(cause)
        effect_ancestors = self.get_ancestors(effect)
        return list(cause_ancestors & effect_ancestors)

    def d_separated(self, x: str, y: str, conditioned: set[str] | None = None) -> bool:
        conditioned = conditioned or set()
        parents_x = set(self.get_parents(x))
        parents_y = set(self.get_parents(y))
        common = parents_x & parents_y
        if not common:
            return True
        if common & conditioned:
            return True
        return False

    @property
    def nodes(self) -> list[CausalNode]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[CausalEdge]:
        return list(self._edges)


class CausalReasoner:
    """因果推理器: do-演算和反事实推理。"""

    def __init__(self, graph: CausalGraph | None = None):
        self.graph = graph or CausalGraph()
        self._intervention_history: list[InterventionResult] = []

    def do_intervention(self, target: str, value: Any,
                        controlled: set[str] | None = None) -> InterventionResult:
        """模拟do(X=x)干预: 切断target的所有入边，设为固定值。"""
        controlled = controlled or set()
        confounders = self.graph.get_confounders(target, "")
        controlled_confounders = [c for c in confounders if c in controlled]
        result = InterventionResult(
            target=target,
            intervention=f"do({target}={value})",
            intervened_value=value,
            confounders_controlled=controlled_confounders,
            confidence=len(controlled_confounders) / max(1, len(confounders)),
        )
        if target in self.graph._nodes:
            self.graph._nodes[target].interventions += 1
        self._intervention_history.append(result)
        return result

    def estimate_effect(self, cause: str, effect: str,
                        confounders: set[str] | None = None) -> dict[str, Any]:
        """估计因果效应: 通过后门调整控制混杂因子。"""
        confounders = confounders or set()
        found_confounders = self.graph.get_confounders(cause, effect)
        uncontrolled = set(found_confounders) - confounders
        edge = None
        for e in self.graph.edges:
            if e.source == cause and e.target == effect:
                edge = e
                break
        base_effect = edge.strength if edge else 0.0
        bias = 0.2 * len(uncontrolled)
        return {
            "cause": cause,
            "effect": effect,
            "estimated_effect": base_effect,
            "bias_upper_bound": bias,
            "confounders_found": found_confounders,
            "confounders_controlled": list(confounders & set(found_confounders)),
            "confounders_uncontrolled": list(uncontrolled),
            "is_identified": len(uncontrolled) == 0,
        }

    def counterfactual(self, actual_cause: str, actual_value: Any,
                       counterfactual_value: Any, effect: str) -> dict[str, Any]:
        """反事实推理: "如果当时X=x'而不是X=x，Y会怎样？\""""
        return {
            "actual": {actual_cause: actual_value},
            "counterfactual": {actual_cause: counterfactual_value},
            "effect_variable": effect,
            "question": f"如果{actual_cause}={counterfactual_value}而非{actual_value}，{effect}会怎样？",
            "requires_abduction": True,
            "requires_intervention": True,
            "requires_prediction": True,
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "nodes": len(self.graph.nodes),
            "edges": len(self.graph.edges),
            "interventions": len(self._intervention_history),
        }
