# Local Autonomous Runtime Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete a verifiable local backend implementation of the proposed autonomous evolution system.

**Architecture:** Add a local runtime layer over the existing dual-ring backend. The runtime composes event bus, skill lifecycle, approval queue, permission gate, sandbox runner, algorithm experiment runner, and a small FastAPI cockpit. All dangerous operations are represented as explicit requests and remain blocked until approved.

**Tech Stack:** Python 3.10+, pytest, FastAPI optional, filesystem-backed JSON/JSONL state, subprocess without shell.

---

### Task 1: Governance Approval Queue And Permission Gate

**Files:**
- Create: `dual_ring_ai/core/governance.py`
- Test: `dual_ring_ai/test_local_autonomous_runtime.py`

- [ ] Write failing tests for creating, approving, rejecting, and persisting approval requests.
- [ ] Write failing tests for blocking operations that exceed a skill or agent policy.
- [ ] Implement `GovernanceStore`, `ApprovalRequest`, `PermissionGate`, and `PermissionDecision`.

### Task 2: Sandbox Runner

**Files:**
- Create: `dual_ring_ai/core/sandbox_runner.py`
- Modify: `dual_ring_ai/executor/execution_engine.py`
- Test: `dual_ring_ai/test_local_autonomous_runtime.py`

- [ ] Write failing tests for running a skill inside a bounded workspace with argv-only commands.
- [ ] Write failing tests for rejecting shell/network/unsafe filesystem policies.
- [ ] Implement `SandboxRunner` and wire `ExecutionEngine` to use it when configured.

### Task 3: Algorithm Experiment Runner

**Files:**
- Create: `dual_ring_ai/core/algorithm_experiment.py`
- Test: `dual_ring_ai/test_local_autonomous_runtime.py`

- [ ] Write failing tests for comparing baseline and candidate metrics.
- [ ] Write failing tests for producing a promotion recommendation only when all metric thresholds improve.
- [ ] Implement deterministic experiment evaluation over local JSON datasets.

### Task 4: Local Runtime Orchestrator

**Files:**
- Create: `dual_ring_ai/runtime/local_runtime.py`
- Test: `dual_ring_ai/test_local_autonomous_runtime.py`

- [ ] Write failing tests that instantiate the local runtime with temporary directories and verify all core services are available.
- [ ] Implement runtime factory and status snapshot.

### Task 5: Cockpit API

**Files:**
- Create: `dual_ring_ai/dashboard/cockpit_api.py`
- Test: `dual_ring_ai/test_local_autonomous_runtime.py`

- [ ] Write failing tests for status, approval listing, approval decision, and algorithm proposal listing endpoints.
- [ ] Implement FastAPI app factory with no mandatory server start in tests.

### Task 6: Verification

Run:

```bash
python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py dual_ring_ai/test_full_backend_evolution.py dual_ring_ai/test_local_autonomous_runtime.py -q
```

Then run `dual_ring_ai/test_strategist.py -q` separately and clean any generated workspace or strategist files.
