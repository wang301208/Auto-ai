"""Governance module for AutoAI.

Provides policy enforcement, boundary management, rate limiting, audit logging,
quota management, auto-evolution, autonomy escalation, modification chains,
and break logging for agent operations.

Philosophy: Agent autonomously manages boundaries. Human role: post-hoc audit only.
No approval workflow. No supervised mode.
"""

from .policy import Policy, PolicyRule, PolicyEffect, PolicyEvaluator
from .approval import ApprovalStore, ApprovalRequest, ApprovalStatus
from .rate_limit import RateLimiter, RateLimitRule, TokenBucket
from .audit import AuditLog, AuditEntry, AuditEventType
from .quota import QuotaManager, QuotaScope, QuotaExceededError
from .gate import GovernanceGate, GovernanceDecision
from .policy_evolver import PolicyEvolver, EvolutionConfig, EvolutionResult
from .autonomy_level import (
    AutonomyLevel, AutonomyCapabilities, AutonomyConfig,
    AutonomyManager, EscalationRecord,
)
from .modification_chain import (
    ModificationType, ModificationStatus, TestResult,
    ModificationBlock, ModificationChain, GENESIS_HASH,
)
from .experience_store import IssueType, FixPattern, ExperienceStore
from .project_fingerprint import ProjectFingerprint, ProjectRegistry
from .boundary_manager import (
    BoundaryManager, ConstraintKind, Constraint, ConstraintSet,
    SEED_CONSTRAINTS, AUTONOMY_PRESETS,
)
from .break_log import BreakLog, BreakRecord
from .break_report import BreakReport

__all__ = [
    "Policy",
    "PolicyRule",
    "PolicyEffect",
    "PolicyEvaluator",
    "ApprovalStore",
    "ApprovalRequest",
    "ApprovalStatus",
    "RateLimiter",
    "RateLimitRule",
    "TokenBucket",
    "AuditLog",
    "AuditEntry",
    "AuditEventType",
    "QuotaManager",
    "QuotaScope",
    "QuotaExceededError",
    "GovernanceGate",
    "GovernanceDecision",
    "PolicyEvolver",
    "EvolutionConfig",
    "EvolutionResult",
    "AutonomyLevel",
    "AutonomyCapabilities",
    "AutonomyConfig",
    "AutonomyManager",
    "EscalationRecord",
    "ModificationType",
    "ModificationStatus",
    "TestResult",
    "ModificationBlock",
    "ModificationChain",
    "GENESIS_HASH",
    "IssueType",
    "FixPattern",
    "ExperienceStore",
    "ProjectFingerprint",
    "ProjectRegistry",
    "BoundaryManager",
    "ConstraintKind",
    "Constraint",
    "ConstraintSet",
    "SEED_CONSTRAINTS",
    "AUTONOMY_PRESETS",
    "BreakLog",
    "BreakRecord",
    "BreakReport",
]
