"""Phase kappa: 知识涌现 - 知识图谱自构建、语义压缩、跨域迁移、信念修正。"""

from autoai.knowledge.graph import KnowledgeGraph, KnowledgeNode, KnowledgeEdge
from autoai.knowledge.compressor import SemanticCompressor, ConceptDigest
from autoai.knowledge.transfer import CrossDomainTransfer, DomainBridge
from autoai.knowledge.belief import BeliefSystem, Belief, BeliefRevision

__all__ = [
    "KnowledgeGraph", "KnowledgeNode", "KnowledgeEdge",
    "SemanticCompressor", "ConceptDigest",
    "CrossDomainTransfer", "DomainBridge",
    "BeliefSystem", "Belief", "BeliefRevision",
]
