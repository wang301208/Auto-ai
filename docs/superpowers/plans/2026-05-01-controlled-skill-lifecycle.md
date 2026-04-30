# Controlled Skill Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first safe backend slice of the proposed autonomous-evolution architecture: capability gaps can produce skill proposals, proposals are validated in an isolated workspace, and approved skills are published without direct git merge or push.

**Architecture:** Keep the existing `dual_ring_ai` event-driven design. Add a small skill lifecycle module that validates generated skills with pytest in a bounded directory, publishes them into `skill_library`, and records manifest metadata. Harden skill execution by removing shell command construction.

**Tech Stack:** Python 3.10+, pytest, pathlib, subprocess without shell, existing `dual_ring_ai` event bus and librarian abstractions.

---

### Task 1: Controlled Skill Execution

**Files:**
- Modify: `dual_ring_ai/executor/execution_engine.py`
- Test: `dual_ring_ai/test_controlled_skill_lifecycle.py`

- [ ] **Step 1: Write failing test**

Test that skill execution passes arguments without `shell=True`, rejects unknown skill paths, and returns JSON output from a simple local skill.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py -q`

Expected: FAIL because controlled execution helpers do not exist yet.

- [ ] **Step 3: Implement minimal execution hardening**

Use `subprocess.run([sys.executable, str(main_file), ...], shell=False, cwd=skill_dir)`. Convert parameters to CLI arguments with a list builder.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py -q`

Expected: PASS for execution tests.

### Task 2: Skill Proposal Validation

**Files:**
- Create: `dual_ring_ai/core/skill_lifecycle.py`
- Test: `dual_ring_ai/test_controlled_skill_lifecycle.py`

- [ ] **Step 1: Write failing test**

Test that a proposed skill directory must contain `main.py`, `test_main.py`, and `skill.json`, and that validation runs `pytest test_main.py` inside the proposed skill directory.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py -q`

Expected: FAIL because the lifecycle module does not exist.

- [ ] **Step 3: Implement validator**

Add `SkillLifecycleManager.validate_proposal(skill_dir)` returning a structured `SkillValidationResult`.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py -q`

Expected: PASS for validation tests.

### Task 3: Approved Skill Publication

**Files:**
- Modify: `dual_ring_ai/core/skill_lifecycle.py`
- Modify: `dual_ring_ai/genesis/qa_agent.py`
- Test: `dual_ring_ai/test_controlled_skill_lifecycle.py`

- [ ] **Step 1: Write failing test**

Test that publishing an approved skill copies the validated skill into `skill_library/<name>_<version>/`, writes `lifecycle.json`, and emits `SKILL_CREATED`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py -q`

Expected: FAIL because publication is not implemented.

- [ ] **Step 3: Implement publication**

Add `publish_approved_skill(skill_dir, approved_by, source_request_id)` and wire `QAAgent._deploy_approved_fix` to publish skill artifacts instead of running git checkout/merge/push.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py -q`

Expected: PASS.

### Task 4: Verification

**Files:**
- No new code unless tests expose issues.

- [ ] **Step 1: Run focused verification**

Run: `python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py dual_ring_ai/test_system.py dual_ring_ai/test_strategist.py -q`

- [ ] **Step 2: Inspect git diff**

Run: `git diff -- dual_ring_ai tests docs`

- [ ] **Step 3: Report remaining gaps**

Document that algorithm evolution, frontend, full sandbox isolation, and external network governance remain future phases.
