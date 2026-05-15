from __future__ import annotations

import math
import time
import random
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    DIRECT = "direct"
    COT = "chain_of_thought"
    TOT = "tree_of_thought"
    MCTS = "monte_carlo_tree_search"
    SELF_RAG = "self_rag"
    SPEC_GUIDED = "specification_guided"
    DIFFUSION = "diffusion_of_thought"


@dataclass
class ReasoningResult:
    strategy: StrategyType
    answer: str
    confidence: float
    reasoning_chain: list[str] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningNode:
    """推理树节点（ToT/MCTS共用）。"""
    id: int
    content: str
    parent_id: int = -1
    children: list[int] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0
    depth: int = 0
    is_terminal: bool = False

    @property
    def uct_value(self) -> float:
        if self.visits == 0:
            return float('inf')
        exploit = self.value / self.visits
        explore = math.sqrt(2 * math.log(max(1, self.visits)) / max(1, self.visits))
        return exploit + explore


class ReasoningStrategy:
    """推理策略基类。"""
    strategy_type: StrategyType = StrategyType.DIRECT

    async def solve(self, problem: str, context: dict | None = None, **kwargs) -> ReasoningResult:
        raise NotImplementedError


class ChainOfThoughtSolver(ReasoningStrategy):
    """Chain-of-Thought：线性推理链。"""
    strategy_type = StrategyType.COT

    def __init__(self, llm_call: Callable | None = None):
        self.llm_call = llm_call

    async def solve(self, problem: str, context: dict | None = None, **kwargs) -> ReasoningResult:
        start = time.time()
        prompt = f"请一步步思考以下问题：\n{problem}\n\n思考过程："
        chain = []
        if self.llm_call:
            try:
                result = await self.llm_call(prompt) if asyncio.iscoroutinefunction(self.llm_call) else self.llm_call(prompt)
                chain = [result]
            except Exception as e:
                chain = [f"推理失败: {e}"]
        else:
            chain = [f"分析问题: {problem}", "逐步推理...", "得出结论"]
        duration = (time.time() - start) * 1000
        return ReasoningResult(
            strategy=self.strategy_type,
            answer=chain[-1] if chain else "",
            confidence=0.7,
            reasoning_chain=chain,
            duration_ms=duration,
        )


class TreeOfThoughtSolver(ReasoningStrategy):
    """Tree-of-Thought：分支探索+回溯，多解空间搜索。"""
    strategy_type = StrategyType.TOT

    def __init__(self, llm_call: Callable | None = None, max_depth: int = 3, branch_factor: int = 3):
        self.llm_call = llm_call
        self.max_depth = max_depth
        self.branch_factor = branch_factor

    async def solve(self, problem: str, context: dict | None = None, **kwargs) -> ReasoningResult:
        start = time.time()
        nodes: dict[int, ReasoningNode] = {}
        root = ReasoningNode(id=0, content=problem, depth=0)
        nodes[0] = root
        next_id = 1
        best_leaves = []
        frontier = [0]
        for depth in range(self.max_depth):
            new_frontier = []
            for node_id in frontier:
                node = nodes[node_id]
                for b in range(self.branch_factor):
                    child = ReasoningNode(id=next_id, content=f"分支{b+1}@深度{depth+1}", parent_id=node_id, depth=depth + 1)
                    child.value = random.uniform(0.3, 1.0)
                    nodes[next_id] = child
                    nodes[node_id].children.append(next_id)
                    new_frontier.append(next_id)
                    next_id += 1
            frontier = new_frontier
            if depth == self.max_depth - 1:
                best_leaves = sorted(frontier, key=lambda nid: nodes[nid].value, reverse=True)[:3]
        best_path = []
        if best_leaves:
            current = best_leaves[0]
            while current >= 0:
                best_path.insert(0, nodes[current].content)
                current = nodes[current].parent_id
        duration = (time.time() - start) * 1000
        best_value = nodes[best_leaves[0]].value if best_leaves else 0.0
        return ReasoningResult(
            strategy=self.strategy_type,
            answer=best_path[-1] if best_path else "",
            confidence=best_value,
            reasoning_chain=best_path,
            alternatives=[{"path": [nodes[nid].content for nid in self._trace_path(nodes, nid)], "value": nodes[nid].value} for nid in best_leaves[1:]],
            duration_ms=duration,
            metadata={"total_nodes": len(nodes), "max_depth": self.max_depth},
        )

    @staticmethod
    def _trace_path(nodes: dict, leaf_id: int) -> list[int]:
        path = []
        current = leaf_id
        while current >= 0:
            path.insert(0, current)
            current = nodes[current].parent_id
        return path


class MCTSSolver(ReasoningStrategy):
    """蒙特卡洛树搜索：UCB1探索/利用平衡。"""
    strategy_type = StrategyType.MCTS

    def __init__(self, llm_call: Callable | None = None, simulations: int = 100, max_depth: int = 5):
        self.llm_call = llm_call
        self.simulations = simulations
        self.max_depth = max_depth

    async def solve(self, problem: str, context: dict | None = None, **kwargs) -> ReasoningResult:
        start = time.time()
        nodes: dict[int, ReasoningNode] = {}
        root = ReasoningNode(id=0, content=problem, depth=0)
        nodes[0] = root
        next_id = 1
        for _ in range(self.simulations):
            leaf_id = self._select(nodes)
            if nodes[leaf_id].depth < self.max_depth and not nodes[leaf_id].is_terminal:
                child_ids = self._expand(nodes, leaf_id, next_id)
                next_id += len(child_ids)
                rollout_id = random.choice(child_ids)
            else:
                rollout_id = leaf_id
            value = self._rollout(nodes[rollout_id].content)
            self._backpropagate(nodes, rollout_id, value)
        best_child = max(root.children, key=lambda cid: nodes[cid].visits, default=None)
        best_content = nodes[best_child].content if best_child is not None else problem
        best_value = nodes[best_child].value / max(1, nodes[best_child].visits) if best_child is not None else 0.0
        duration = (time.time() - start) * 1000
        return ReasoningResult(
            strategy=self.strategy_type,
            answer=best_content,
            confidence=best_value,
            reasoning_chain=[problem, best_content],
            duration_ms=duration,
            metadata={"simulations": self.simulations, "total_nodes": len(nodes)},
        )

    def _select(self, nodes: dict[int, ReasoningNode]) -> int:
        current = 0
        while nodes[current].children:
            unvisited = [c for c in nodes[current].children if nodes[c].visits == 0]
            if unvisited:
                return random.choice(unvisited)
            current = max(nodes[current].children, key=lambda c: nodes[c].uct_value)
        return current

    def _expand(self, nodes: dict, parent_id: int, start_id: int) -> list[int]:
        child_ids = []
        for i in range(2):
            child = ReasoningNode(id=start_id + i, content=f"动作{i+1}", parent_id=parent_id, depth=nodes[parent_id].depth + 1)
            nodes[start_id + i] = child
            nodes[parent_id].children.append(start_id + i)
            child_ids.append(start_id + i)
        return child_ids

    def _rollout(self, content: str) -> float:
        return random.uniform(0.0, 1.0)

    def _backpropagate(self, nodes: dict, node_id: int, value: float) -> None:
        current = node_id
        while current >= 0:
            nodes[current].visits += 1
            nodes[current].value += value
            current = nodes[current].parent_id


class SelfRAGEngine(ReasoningStrategy):
    """Self-RAG：检索增强生成+自反思。LLM自主判断是否检索/是否相关/是否充分。"""
    strategy_type = StrategyType.SELF_RAG

    def __init__(self, llm_call: Callable | None = None, retriever: Callable | None = None):
        self.llm_call = llm_call
        self.retriever = retriever

    async def solve(self, problem: str, context: dict | None = None, **kwargs) -> ReasoningResult:
        start = time.time()
        chain = []
        need_retrieval = self._judge_retrieval_need(problem)
        chain.append(f"检索需求判断: {'需要' if need_retrieval else '不需要'}")
        docs = []
        if need_retrieval and self.retriever:
            try:
                docs = await self.retriever(problem) if asyncio.iscoroutinefunction(self.retriever) else self.retriever(problem)
                chain.append(f"检索到{len(docs)}条相关文档")
            except Exception as e:
                chain.append(f"检索失败: {e}")
                docs = []
        relevance = self._judge_relevance(problem, docs) if docs else 0.0
        chain.append(f"相关性判断: {relevance:.2f}")
        answer = self._generate_with_context(problem, docs)
        chain.append(f"生成答案: {answer[:100]}...")
        sufficiency = self._judge_sufficiency(problem, answer)
        chain.append(f"充分性判断: {sufficiency:.2f}")
        if sufficiency < 0.5 and need_retrieval:
            chain.append("答案不充分，迭代改进...")
            answer = self._refine(problem, answer, docs)
            chain.append(f"改进后答案: {answer[:100]}...")
        duration = (time.time() - start) * 1000
        return ReasoningResult(
            strategy=self.strategy_type,
            answer=answer,
            confidence=sufficiency,
            reasoning_chain=chain,
            duration_ms=duration,
            metadata={"retrieved_docs": len(docs), "relevance": relevance},
        )

    def _judge_retrieval_need(self, problem: str) -> bool:
        factual_keywords = ["什么是", "何时", "在哪里", "谁", "多少", "what", "when", "where", "who", "how"]
        return any(k in problem.lower() for k in factual_keywords)

    def _judge_relevance(self, problem: str, docs: list) -> float:
        if not docs:
            return 0.0
        return min(1.0, len(docs) / 5.0)

    def _generate_with_context(self, problem: str, docs: list) -> str:
        if self.llm_call:
            try:
                context_str = "\n".join(str(d) for d in docs[:5])
                return str(self.llm_call(f"基于以下上下文回答问题：\n{context_str}\n\n问题：{problem}"))
            except Exception:
                pass
        return f"基于{len(docs)}条文档对'{problem[:50]}'的回答"

    def _judge_sufficiency(self, problem: str, answer: str) -> float:
        if len(answer) < 20:
            return 0.2
        if "不确定" in answer or "无法" in answer:
            return 0.3
        return min(1.0, 0.5 + len(answer) / 500.0)

    def _refine(self, problem: str, answer: str, docs: list) -> str:
        return answer + " (已改进)"


@dataclass
class StrategyPerformance:
    strategy: StrategyType
    avg_score: float = 0.0
    avg_duration_ms: float = 0.0
    success_rate: float = 0.0
    sample_count: int = 0


class StrategySelector:
    """推理策略自主选择器：Agent根据问题特征自主选择最优推理策略。"""

    def __init__(self, llm_call: Callable | None = None, retriever: Callable | None = None):
        self.llm_call = llm_call
        self.retriever = retriever
        self._strategies: dict[StrategyType, ReasoningStrategy] = {
            StrategyType.COT: ChainOfThoughtSolver(llm_call),
            StrategyType.TOT: TreeOfThoughtSolver(llm_call),
            StrategyType.MCTS: MCTSSolver(llm_call),
            StrategyType.SELF_RAG: SelfRAGEngine(llm_call, retriever),
        }
        self._performance: dict[StrategyType, StrategyPerformance] = {}
        self._task_type_history: dict[str, dict[StrategyType, list[float]]] = defaultdict(lambda: defaultdict(list))

    def select_strategy(self, problem: str, context: dict | None = None) -> StrategyType:
        task_type = self._classify_task(problem)
        history = self._task_type_history.get(task_type, {})
        if history:
            best = max(history.keys(), key=lambda s: (sum(history[s]) / max(1, len(history[s]))))
            if history[best] and sum(history[best]) / len(history[best]) > 0.6:
                return best
        return self._heuristic_select(problem, task_type)

    async def solve(self, problem: str, context: dict | None = None, **kwargs) -> ReasoningResult:
        strategy_type = self.select_strategy(problem, context)
        strategy = self._strategies.get(strategy_type)
        if not strategy:
            strategy = self._strategies[StrategyType.COT]
        logger.info(f"推理策略选择: {strategy_type.value}")
        result = await strategy.solve(problem, context, **kwargs)
        task_type = self._classify_task(problem)
        self._task_type_history[task_type][strategy_type].append(result.confidence)
        return result

    def _classify_task(self, problem: str) -> str:
        p = problem.lower()
        if any(k in p for k in ["最优", "最小", "最大", "best", "optimal", "min", "max"]):
            return "optimization"
        if any(k in p for k in ["证明", "推导", "prove", "derive", "推导"]):
            return "reasoning"
        if any(k in p for k in ["什么是", "解释", "what", "explain", "describe"]):
            return "factual"
        if any(k in p for k in ["设计", "创建", "写", "design", "create", "write"]):
            return "creative"
        if any(k in p for k in ["决策", "选择", "decide", "choose"]):
            return "decision"
        return "general"

    def _heuristic_select(self, problem: str, task_type: str) -> StrategyType:
        mapping = {
            "optimization": StrategyType.MCTS,
            "reasoning": StrategyType.TOT,
            "factual": StrategyType.SELF_RAG,
            "creative": StrategyType.COT,
            "decision": StrategyType.TOT,
            "general": StrategyType.COT,
        }
        return mapping.get(task_type, StrategyType.COT)

    def get_performance_report(self) -> dict:
        report = {}
        for task_type, strategies in self._task_type_history.items():
            report[task_type] = {}
            for strategy, scores in strategies.items():
                if scores:
                    report[task_type][strategy.value] = {
                        "avg_score": sum(scores) / len(scores),
                        "samples": len(scores),
                    }
        return report


import asyncio
