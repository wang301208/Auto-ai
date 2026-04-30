# Full Backend Evolution Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the backend-safe implementation of the proposed autonomous evolution architecture without pretending to implement external UI shells, real academic search, or unrestricted AGI behavior.

**Architecture:** Extend the current `dual_ring_ai` backend with explicit sandbox policy, lifecycle audit logs, algorithm registry, algorithm evolution proposals, and agent blueprint metadata. Every autonomous change remains a proposal until validated and approved.

**Tech Stack:** Python 3.10+, pytest, JSON/YAML metadata, existing `dual_ring_ai` event bus, filesystem-backed registries.

---

### Task 1: Sandbox Policy For Generated Capabilities

**Files:**
- Modify: `dual_ring_ai/core/skill_lifecycle.py`
- Test: `dual_ring_ai/test_full_backend_evolution.py`

- [ ] **Step 1: Write failing tests**

Test that `skill.json` must include a `security_policy` section and that validation rejects policies with network access, shell access, or writes outside the workspace unless explicitly allowed.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dual_ring_ai/test_full_backend_evolution.py -q`

Expected: FAIL because policy validation does not exist.

- [ ] **Step 3: Implement policy validation**

Add `SandboxPolicy` with `network`, `shell`, `filesystem` fields and persist the accepted policy in `lifecycle.json`.

### Task 2: Lifecycle Audit Log

**Files:**
- Modify: `dual_ring_ai/core/skill_lifecycle.py`
- Test: `dual_ring_ai/test_full_backend_evolution.py`

- [ ] **Step 1: Write failing tests**

Test that validation and publication append JSONL audit entries containing action, result, actor, skill name, and timestamp.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dual_ring_ai/test_full_backend_evolution.py -q`

Expected: FAIL because audit logging does not exist.

- [ ] **Step 3: Implement audit logging**

Add filesystem JSONL audit log support under `logs/skill_lifecycle_audit.jsonl` by default, configurable in constructor.

### Task 3: Algorithm Registry

**Files:**
- Create: `dual_ring_ai/core/algorithm_registry.py`
- Test: `dual_ring_ai/test_full_backend_evolution.py`

- [ ] **Step 1: Write failing tests**

Test that algorithms can be registered with metadata, evaluation metrics, source module, version, status, and rollback target.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dual_ring_ai/test_full_backend_evolution.py -q`

Expected: FAIL because registry does not exist.

- [ ] **Step 3: Implement registry**

Store algorithm manifests in `algorithm_library/<name>_<version>/algorithm.json`. Provide list/get/register APIs.

### Task 4: Algorithm Evolution Protocol

**Files:**
- Create: `dual_ring_ai/genesis/algorithmist.py`
- Test: `dual_ring_ai/test_full_backend_evolution.py`

- [ ] **Step 1: Write failing tests**

Test that the algorithmist can create a structured proposal for replacing a thinking engine and emits `ALGORITHM_RESEARCH_PROPOSED` with hypothesis, experiment design, metrics, and human approval requirement.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dual_ring_ai/test_full_backend_evolution.py -q`

Expected: FAIL because algorithmist and event type do not exist.

- [ ] **Step 3: Implement algorithmist proposal flow**

Add event type constants and a proposal method. Do not implement autonomous deployment.

### Task 5: Agent Blueprint Thinking Engine Metadata

**Files:**
- Create: `dual_ring_ai/core/agent_blueprint.py`
- Test: `dual_ring_ai/test_full_backend_evolution.py`

- [ ] **Step 1: Write failing tests**

Test YAML load/save for `role_name`, `version`, `agent_class`, `thinking_engine.name`, `thinking_engine.version`, and `evaluation_suite`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dual_ring_ai/test_full_backend_evolution.py -q`

Expected: FAIL because blueprint support does not exist in `dual_ring_ai/core`.

- [ ] **Step 3: Implement blueprint metadata**

Add simple dataclasses and YAML loader/dumper.

### Task 6: Verification

Run:

```bash
python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py dual_ring_ai/test_full_backend_evolution.py dual_ring_ai/test_strategist.py -q
```

Clean generated test artifacts. Report remaining future work as explicit non-goals: UI shell, real sandbox containers, academic search integrations, and automatic deployment of algorithms.
