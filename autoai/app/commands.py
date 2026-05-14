"""Unified CLI command groups for AutoAI.

Consolidates all scattered scripts into a single `aai` command hierarchy:

    aai              - Start Auto-AI assistant (default)
    aai skill        - Skill library management (replaces skill_cli.py + librarian_cli.py)
    aai orchestrate  - Orchestrator management (replaces run_orchestrator.py + run_blueprint_orchestrator.py)
    aai evolve       - Algorithm evolution (replaces auto_evolve.py + simple_evolution.py)
    aai ingest       - Data ingestion (replaces data_ingestion.py)
    aai tui          - TUI terminal (replaces launch_tui.py)
    aai plugin       - Plugin management (replaces generate_plugins.py + install_plugin_deps.py)
    aai governance   - Governance operations (replaces approve_fix.py)
    aai alphaevolve  - AlphaEvolve workflows (unchanged)
    aai doctor       - Health check (replaces test_tui.py + tui doctor)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .i18n import _


def _check_python_version() -> None:
    if sys.version_info < (3, 12):
        raise click.ClickException(_("Python 3.12 or higher is required to run AutoAI."))


# ======================================================================
# Skill command group
# ======================================================================

@click.group(help=_("Skill library management."))
def skill() -> None:
    pass


@skill.command("search", help=_("Search for skills in the library."))
@click.argument("query")
@click.option("-k", "--top-k", default=5, help=_("Number of results"))
def skill_search(query: str, top_k: int) -> None:
    from autoai.config import Config
    from autoai.skills.librarian import LibrarianAgent

    config = Config()
    librarian = LibrarianAgent(config)
    results = librarian.find_skill(query, top_k=top_k)
    if not results:
        click.echo(_("No skills found matching query."))
        return
    for i, r in enumerate(results, 1):
        click.echo(f"{i}. {r.get('skill_name', 'unknown')} v{r.get('version', '?')} - {r.get('description', '')}")


@skill.command("add", help=_("Add a skill to the library."))
@click.argument("skill_path", type=click.Path(exists=True))
@click.option("--source", default="local", help=_("Skill source type"))
def skill_add(skill_path: str, source: str) -> None:
    from autoai.config import Config
    from autoai.skills.library import SkillLibrary

    config = Config()
    library = SkillLibrary(config)
    library.add_skill(Path(skill_path))
    click.echo(_("Skill added successfully."))


@skill.command("test", help=_("Run tests for a skill."))
@click.argument("skill_name")
def skill_test(skill_name: str) -> None:
    import subprocess

    result = subprocess.run(
        ["pytest", "-q", "-k", skill_name],
        capture_output=True,
        text=True,
    )
    click.echo(result.stdout)
    if result.returncode != 0:
        click.echo(result.stderr, err=True)
        raise SystemExit(result.returncode)


@skill.command("register-new", help=_("Scan git history and register new skills."))
@click.option("--repo-path", default=".", help=_("Repository root path"))
def skill_register_new(repo_path: str) -> None:
    from autoai.skills.librarian import LibrarianAgent
    from autoai.config import Config
    import subprocess

    config = Config()
    librarian = LibrarianAgent(config)
    try:
        output = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=A", "HEAD~1"],
            cwd=repo_path, text=True,
        )
    except Exception:
        click.echo(_("Could not read git history."))
        return
    for line in output.splitlines():
        if line.endswith("skill.json"):
            skill_path = Path(repo_path) / line
            librarian.library.add_skill(skill_path)
            click.echo(f"Registered: {line}")


@skill.command("audit", help=_("Show skill audit log."))
def skill_audit() -> None:
    from autoai.telemetry.audit import get_audit_log

    for entry in get_audit_log():
        click.echo(f"[{entry.get('timestamp', '')}] {entry.get('action', '')}: {entry.get('skill_name', '')}")


# ======================================================================
# Orchestrate command group
# ======================================================================

@click.group(help=_("Orchestrator management."))
def orchestrate() -> None:
    pass


@orchestrate.command("start", help=_("Start the AutoAI orchestrator."))
@click.option("--agents", "-a", multiple=True, help=_("Agent names to start"))
@click.option("--workdir", default=".", help=_("Working directory"))
@click.option("--db-path", default="events.db", help=_("Event database path"))
def orchestrate_start(agents: tuple[str], workdir: str, db_path: str) -> None:
    from autoai.orchestrator import Orchestrator, AVAILABLE_AGENTS

    agent_list = list(agents) if agents else AVAILABLE_AGENTS
    orch = Orchestrator(db_path=db_path, agents=agent_list)
    click.echo(f"Starting orchestrator with agents: {agent_list}")
    orch.start()


@orchestrate.command("blueprint", help=_("Start blueprint-based orchestrator."))
@click.option("--charter-url", required=True, help=_("Git URL for charter repo"))
@click.option("--events-db", default="events.db", help=_("Event database path"))
@click.option("--poll", default=30.0, type=float, help=_("Poll interval in seconds"))
def orchestrate_blueprint(charter_url: str, events_db: str, poll: float) -> None:
    from autoai.orchestrator_blueprint import BlueprintOrchestrator

    orch = BlueprintOrchestrator(charter_url=charter_url, events_db_path=events_db)
    click.echo(f"Starting blueprint orchestrator (poll={poll}s)")
    orch.run(poll_interval=poll)


@orchestrate.command("execute", help=_("Run a goal through the Executor agent."))
@click.argument("goal")
def orchestrate_execute(goal: str) -> None:
    from autoai.agents.executor import Executor
    from autoai.config import Config
    from autoai.event_bus import MessageQueue

    config = Config()
    executor = Executor(config=config, message_queue=MessageQueue())
    plan = executor.plan(goal)
    click.echo(_("Planned steps:"))
    for i, step in enumerate(plan, 1):
        click.echo(f"  {i}. {step.description}")
    results = executor.execute(plan)
    for i, result in enumerate(results, 1):
        click.echo(f"  {i}. {result}")


@orchestrate.command("multi-agent", help=_("Launch the full multi-agent system."))
@click.option("--autonomous/--no-autonomous", default=True, help=_("Enable autonomous mode"))
@click.option("--fleet", default="governance/agents_fleet.json", help=_("Fleet config file"))
@click.option("--workspace", default=".", help=_("Workspace directory"))
def orchestrate_multi_agent(autonomous: bool, fleet: str, workspace: str) -> None:
    from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
    from pathlib import Path

    config = SystemConfig(
        autonomous=autonomous,
        enable_tui=True,
        enable_health_monitor=True,
        enable_agent_pool=True,
        enable_policy_evolver=autonomous,
        enable_checkpoint=True,
    )
    system = MultiAgentSystem(
        workspace_path=Path(workspace).resolve(),
        config=config,
    )
    system.setup()
    click.echo(f"Multi-agent system ready: {len(system.agent_factory.created_agents)} agents")
    click.echo(f"  Autonomous: {autonomous}")
    click.echo(f"  Fleet: {fleet}")
    click.echo("Press Ctrl+C to stop.")
    system.start()
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
    finally:
        system.stop()


@orchestrate.command("checkpoints", help=_("List workflow checkpoints."))
@click.option("--dir", "ckpt_dir", default="governance/checkpoints", help=_("Checkpoint directory"))
def orchestrate_checkpoints(ckpt_dir: str) -> None:
    from autoai.agents.workflow_checkpoint import CheckpointManager

    mgr = CheckpointManager(checkpoint_dir=ckpt_dir)
    listing = mgr.list_checkpoints()
    if not listing:
        click.echo("No checkpoints found.")
        return
    for ckpt in listing:
        click.echo(
            f"  {ckpt['workflow_id']:15s}  {ckpt.get('workflow_name', ''):20s}  "
            f"tasks={ckpt.get('tasks_completed', 0)}/{ckpt.get('tasks_total', 0)}  "
            f"saved={ckpt.get('saved_at', '')}"
        )


# ======================================================================
# Evolve command group
# ======================================================================

@click.group(help=_("Algorithm evolution and strategy optimization."))
def evolve() -> None:
    pass


@evolve.command("run", help=_("Run strategy evolution loop."))
@click.option("-g", "--generations", default=10, type=int, help=_("Number of generations"))
@click.option("-p", "--population", default=20, type=int, help=_("Population size"))
@click.option("-r", "--retain", default=0.3, type=float, help=_("Retention ratio"))
@click.option("--incoming", default=None, help=_("Path to incoming strategies YAML"))
@click.option("--save-best", default=None, help=_("Path to save best strategy"))
def evolve_run(generations: int, population: int, retain: float, incoming: str | None, save_best: str | None) -> None:
    import yaml

    try:
        from openevolve.runner.evaluate import evaluate
    except ImportError:
        raise click.ClickException("openevolve is required: pip install -e '.[alphaevolve]'")

    from seed_population import generate_population

    pop = generate_population(population)
    if incoming:
        with open(incoming) as f:
            incoming_strategies = yaml.safe_load(f)
        if isinstance(incoming_strategies, list):
            pop.extend(incoming_strategies)

    best_strategy = None
    best_score = float("-inf")

    for gen in range(generations):
        scored = [(s, evaluate(s)) for s in pop]
        scored.sort(key=lambda x: x[1], reverse=True)
        click.echo(f"Generation {gen+1}/{generations}: best={scored[0][1]:.4f}")

        if scored[0][1] > best_score:
            best_score = scored[0][1]
            best_strategy = scored[0][0]

        retain_count = max(2, int(len(pop) * retain))
        pop = [s for s, _ in scored[:retain_count]]

    if save_best and best_strategy:
        with open(save_best, "w") as f:
            yaml.dump(best_strategy, f)
        click.echo(f"Best strategy saved to {save_best} (score={best_score:.4f})")
    elif best_strategy:
        click.echo(f"Best score: {best_score:.4f}")


@evolve.command("seed", help=_("Generate initial strategy population."))
@click.option("-n", "--num", default=20, type=int, help=_("Number of strategies"))
@click.option("-o", "--output", default="population.yaml", help=_("Output file"))
def evolve_seed(num: int, output: str) -> None:
    from seed_population import generate_population
    import yaml

    pop = generate_population(num)
    with open(output, "w") as f:
        yaml.dump(pop, f)
    click.echo(f"Generated {num} strategies -> {output}")


# ======================================================================
# Ingest command
# ======================================================================

@click.command(help=_("Ingest files into vector memory."))
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--init", is_flag=True, help=_("Initialize memory before ingesting"))
@click.option("--overlap", default=100, type=int, help=_("Chunk overlap"))
@click.option("--max-length", default=3000, type=int, help=_("Max chunk length"))
def ingest(paths: tuple[str], init: bool, overlap: int, max_length: int) -> None:
    from autoai.config import Config
    from autoai.memory.vector import VectorMemory
    from autoai.commands.file_operations import ingest_file

    config = Config()
    memory = VectorMemory(config)

    if init:
        memory.clear()

    for path_str in paths:
        p = Path(path_str)
        if p.is_file():
            click.echo(f"Ingesting: {p}")
            ingest_file(str(p), memory, config)
        elif p.is_dir():
            for fp in p.rglob("*"):
                if fp.is_file() and not fp.name.startswith("."):
                    click.echo(f"Ingesting: {fp}")
                    ingest_file(str(fp), memory, config)

    click.echo(_("Ingestion complete."))


# ======================================================================
# TUI command
# ======================================================================

@click.command(help=_("Launch the terminal user interface."))
@click.option("--dev", is_flag=True, help=_("Start in development mode"))
def tui(dev: bool) -> None:
    import subprocess
    import os

    ui_dir = Path(__file__).parent.parent.parent / "ui-tui"

    if not ui_dir.exists():
        raise click.ClickException(f"TUI directory not found: {ui_dir}")

    if not dev:
        if not (ui_dir / "dist" / "entry.js").exists():
            click.echo("Installing TUI dependencies...")
            subprocess.run(["npm", "install"], cwd=str(ui_dir), check=True)
            subprocess.run(["npm", "run", "build"], cwd=str(ui_dir), check=True)

        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        subprocess.run(["node", "dist/entry.js"], cwd=str(ui_dir))
    else:
        subprocess.run(["npm", "run", "dev"], cwd=str(ui_dir))


# ======================================================================
# Plugin command group
# ======================================================================

@click.group(help=_("Plugin management."))
def plugin() -> None:
    pass


@plugin.command("generate", help=_("Generate plugin modules from spec files."))
@click.argument("spec_dir", type=click.Path(exists=True))
def plugin_generate(spec_dir: str) -> None:
    import json
    from pathlib import Path

    spec_path = Path(spec_dir)
    for spec_file in spec_path.glob("*.spec.json"):
        spec = json.loads(spec_file.read_text())
        click.echo(f"Generating plugin from: {spec_file.name}")
        try:
            from scripts.generate_plugins import generate_plugin
            generate_plugin(spec, spec_file.parent)
        except ImportError:
            click.echo("  (stub generation - openai not available)")


@plugin.command("install-deps", help=_("Install dependencies for all plugins."))
def plugin_install_deps() -> None:
    import subprocess
    from pathlib import Path

    plugins_dir = Path("plugins")
    if not plugins_dir.exists():
        click.echo("No plugins directory found.")
        return

    for plugin_path in plugins_dir.iterdir():
        req_file = plugin_path / "requirements.txt"
        if req_file.exists():
            click.echo(f"Installing deps for {plugin_path.name}...")
            subprocess.run(
                ["pip", "install", "-r", str(req_file)],
                capture_output=True,
            )


@plugin.command("init-kb", help=_("Initialize knowledge vector database from plugins."))
@click.option("--plugin-repo", default="plugins", help=_("Plugin repository path"))
@click.option("--persist-dir", default="chroma_db", help=_("Persistence directory"))
def plugin_init_kb(plugin_repo: str, persist_dir: str) -> None:
    from autoai.config import Config
    from autoai.memory.vector.utils import get_memory
    from autoai.skills.vector_db import ChromaVectorDB

    config = Config()
    db = ChromaVectorDB(persist_dir=persist_dir)
    click.echo(f"Initialized knowledge DB at {persist_dir}")


# ======================================================================
# Governance command group
# ======================================================================

@click.group(help=_("Governance operations."))
def governance() -> None:
    pass


@governance.command("breaks", help=_("View boundary break records (post-hoc audit)."))
@click.option("--constraint", "constraint_kind", default=None, help=_("Filter by constraint kind"))
@click.option("--agent", "agent_id", default=None, help=_("Filter by agent ID"))
@click.option("--since", default=None, help=_("Filter since ISO timestamp"))
@click.option("--limit", default=20, type=int, help=_("Number of records"))
@click.option("--summary", "summary_only", is_flag=True, help=_("Show summary only"))
def governance_breaks(constraint_kind: str | None, agent_id: str | None, since: str | None, limit: int, summary_only: bool) -> None:
    from governance.break_report import BreakReport

    reporter = BreakReport()
    report = reporter.generate(
        constraint_kind=constraint_kind,
        agent_id=agent_id,
        since=since,
        limit=limit,
        summary_only=summary_only,
    )
    click.echo(report)


@governance.command("audit", help=_("Query governance audit log."))
@click.option("--limit", default=20, type=int, help=_("Number of entries"))
@click.option("--principal", default=None, help=_("Filter by principal"))
@click.option("--event-type", "event_type", default=None, help=_("Filter by event type"))
@click.option("--since", default=None, help=_("Filter since ISO timestamp"))
def governance_audit(limit: int, principal: str | None, event_type: str | None, since: str | None) -> None:
    from governance.audit import AuditLog, AuditEventType

    log = AuditLog()
    et = AuditEventType(event_type) if event_type else None
    entries = log.query(principal=principal, event_type=et, since=since, limit=limit)
    for entry in entries:
        click.echo(f"  [{entry.timestamp}] {entry.event_type} {entry.principal}/{entry.operation}: {entry.decision}")


@governance.command("policy", help=_("Show current policy status."))
@click.option("--policy-file", default="governance/default_policy.json", help=_("Policy file path"))
def governance_policy(policy_file: str) -> None:
    from governance.policy import Policy
    from pathlib import Path

    path = Path(policy_file)
    if not path.exists():
        click.echo(f"Policy file not found: {policy_file}")
        return
    policy = Policy.load(path)
    click.echo(f"Policy: {policy.name}")
    click.echo(f"  Default effect: {policy.default_effect.value}")
    click.echo(f"  Rules: {len(policy.rules)}")
    for rule in sorted(policy.rules, key=lambda r: r.priority):
        click.echo(f"    [{rule.priority:3d}] {rule.effect.value:6s} {rule.operation:20s} -> {rule.principal}/{rule.resource}")


@governance.command("evolve", help=_("Trigger policy auto-evolution."))
@click.option("--lookback", default=24.0, type=float, help=_("Lookback hours"))
@click.option("--policy-file", default="governance/default_policy.json", help=_("Policy file path"))
def governance_evolve(lookback: float, policy_file: str) -> None:
    from governance import GovernanceGate, PolicyEvolver

    gate = GovernanceGate()
    evolver = PolicyEvolver(gate=gate)
    result = evolver.evolve(lookback_hours=lookback)
    if result.skipped:
        click.echo(f"Evolution skipped: {result.reason}")
    elif result.adjustments:
        click.echo(f"Applied {len(result.adjustments)} adjustments:")
        for adj in result.adjustments:
            click.echo(f"  {adj.get('type', '?')}: {json.dumps(adj, ensure_ascii=False)[:120]}")
    else:
        click.echo("No adjustments needed.")


@governance.command("fleet", help=_("Show agent fleet configuration."))
@click.option("--fleet-file", default="governance/agents_fleet.json", help=_("Fleet config file"))
def governance_fleet(fleet_file: str) -> None:
    from pathlib import Path

    path = Path(fleet_file)
    if not path.exists():
        click.echo(f"Fleet file not found: {fleet_file}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    click.echo(f"Fleet: {data.get('fleet_name', 'unknown')}")
    for agent in data.get("agents", []):
        roles = ", ".join(agent.get("roles", []))
        caps = ", ".join(agent.get("capabilities", []))
        click.echo(f"  {agent['agent_id']:15s}  roles=[{roles}]  caps=[{caps}]  max_tasks={agent.get('max_concurrent_tasks', '?')}")


# ======================================================================
# Doctor command
# ======================================================================

@click.command(help=_("Run health diagnostics."))
def doctor() -> None:
    import importlib.util
    import shutil

    def _has_spec(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ModuleNotFoundError, ValueError):
            return False

    checks = [
        ("Python >= 3.12", sys.version_info >= (3, 12)),
        ("openai", _has_spec("openai")),
        ("chromadb", _has_spec("chromadb")),
        ("rich", _has_spec("rich")),
        ("click", _has_spec("click")),
        ("httpx", _has_spec("httpx")),
        ("Node.js", shutil.which("node") is not None),
        ("npm", shutil.which("npm") is not None),
        ("git", shutil.which("git") is not None),
        ("governance/", Path("governance").is_dir()),
        ("governance/default_policy.json", Path("governance/default_policy.json").is_file()),
        ("governance/agents_fleet.json", Path("governance/agents_fleet.json").is_file()),
        ("model_router/", _has_spec("autoai.llm.model_router")),
        ("unified_task", _has_spec("autoai.agents.unified_task")),
        ("sandbox/", _has_spec("autoai.sandbox")),
        ("distributed/", _has_spec("autoai.distributed")),
        ("streaming", _has_spec("autoai.llm.model_router.streaming")),
        ("self_think", _has_spec("autoai.agents.self_think")),
        ("boundary_manager", _has_spec("governance.boundary_manager")),
        ("break_log", _has_spec("governance.break_log")),
        ("ray (optional)", _has_spec("ray")),
        ("seccomp (optional)", sys.platform == "linux" and _has_spec("seccomp")),
        ("self_modify", _has_spec("autoai.agents.self_modify")),
        ("arch_diagnoser", _has_spec("autoai.agents.arch_diagnoser")),
        ("arch_refactorer", _has_spec("autoai.agents.arch_refactorer")),
        ("capability_injector", _has_spec("autoai.agents.capability_injector")),
        ("protocol_upgrader", _has_spec("autoai.agents.protocol_upgrader")),
        ("consensus_engine", _has_spec("autoai.agents.consensus_engine")),
        ("division_emerger", _has_spec("autoai.agents.division_emerger")),
        ("knowledge_mesh", _has_spec("autoai.agents.knowledge_mesh")),
        ("democratic_governance", _has_spec("autoai.agents.democratic_governance")),
        ("unattended_runner", _has_spec("autoai.agents.unattended_runner")),
        ("full_evolution_loop", _has_spec("autoai.agents.full_evolution_loop")),
        ("evolution_community", _has_spec("autoai.agents.evolution_community")),
    ]

    all_pass = True
    for name, ok in checks:
        optional = "(optional)" in name
        status = "OK" if ok else ("SKIP" if optional else "MISSING")
        click.echo(f"  {name}: {status}")
        if not ok and not optional:
            all_pass = False

    if all_pass:
        click.echo("All checks passed.")
    else:
        click.echo("Some checks failed.", err=True)
        raise SystemExit(1)


@click.command("dependency-audit", help=_("Audit external dependencies: usage, risk, and reduction opportunities."))
@click.option("--unused-only", is_flag=True, help=_("Show only unused dependencies"))
@click.option("--json-output", "as_json", is_flag=True, help=_("Output as JSON"))
def dependency_audit(unused_only: bool, as_json: bool) -> None:
    import importlib.util
    from pathlib import Path as P

    CORE_DEPS = {
        "beautifulsoup4": "bs4",
        "colorama": "colorama",
        "openai": "openai",
        "python-dotenv": "dotenv",
        "pyyaml": "yaml",
        "requests": "requests",
        "tiktoken": "tiktoken",
        "click": "click",
        "pydantic": "pydantic",
        "prompt_toolkit": "prompt_toolkit",
    }
    OPTIONAL_DEPS = {
        "spacy": "spacy",
        "chromadb": "chromadb",
        "redis": "redis",
        "orjson": "orjson",
        "ftfy": "ftfy",
        "inflection": "inflection",
        "distro": "distro",
        "Pillow": "PIL",
        "selenium": "selenium",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "duckduckgo-search": "duckduckgo_search",
        "gTTS": "gtts",
        "PyPDF2": "PyPDF2",
        "python-docx": "docx",
        "markdown": "markdown",
        "jsonschema": "jsonschema",
        "charset-normalizer": "charset_normalizer",
        "watchdog": "watchdog",
        "pinecone-client": "pinecone",
        "readability-lxml": "readability",
        "pylatexenc": "pylatexenc",
        "webdriver-manager": "webdriver_manager",
        "agent-protocol": "agent_protocol",
        "google-api-python-client": "googleapiclient",
    }

    def _has_spec(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ModuleNotFoundError, ValueError):
            return False

    def _count_imports(module_name: str) -> int:
        count = 0
        for py in P("autoai").rglob("*.py"):
            if "__pycache__" in str(py):
                continue
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
                if f"import {module_name}" in text or f"from {module_name}" in text:
                    count += 1
            except Exception:
                pass
        return count

    results = []
    for pip_name, import_name in {**CORE_DEPS, **OPTIONAL_DEPS}.items():
        installed = _has_spec(import_name)
        imports = _count_imports(import_name)
        category = "core" if pip_name in CORE_DEPS else "optional"
        results.append({
            "package": pip_name,
            "import_as": import_name,
            "installed": installed,
            "import_count": imports,
            "category": category,
            "status": "unused" if imports == 0 else ("uninstalled" if not installed else "active"),
        })

    if unused_only:
        results = [r for r in results if r["import_count"] == 0]

    if as_json:
        click.echo(json.dumps(results, indent=2))
        return

    click.echo(_("=== Dependency Audit Report ==="))
    click.echo("")
    for r in sorted(results, key=lambda x: (x["import_count"], x["category"])):
        icon = {"active": "OK", "unused": "UNUSED", "uninstalled": "MISSING"}[r["status"]]
        click.echo(f"  {r['package']:<30s} imports={r['import_count']:>2d}  [{r['category']:<8s}] {icon}")
    click.echo("")
    active = sum(1 for r in results if r["status"] == "active")
    unused = sum(1 for r in results if r["status"] == "unused")
    missing = sum(1 for r in results if r["status"] == "uninstalled")
    click.echo(_("Summary: {active} active, {unused} unused, {missing} missing").format(active=active, unused=unused, missing=missing))



# ======================================================================
# Model command group
# ======================================================================

@click.group(help=_("Unified model routing and management."))
def model() -> None:
    pass


@model.command("list", help=_("List all registered models."))
@click.option("--provider", "-p", default=None, help=_("Filter by provider"))
@click.option("--tier", "-t", default=None, help=_("Filter by tier (fast/balanced/smart/embedding)"))
@click.option("--local", "local_only", is_flag=True, help=_("Show only local models"))
def model_list(provider: str | None, tier: str | None, local_only: bool) -> None:
    from autoai.llm.model_router import ModelRegistry
    from autoai.llm.model_router.model_spec import ModelCapability

    registry = ModelRegistry()
    registry.load_builtin_specs()
    models = registry.list_models(provider=provider, tier=tier, local_only=local_only)

    if not models:
        click.echo(_("No models found."))
        return

    for m in models:
        local_tag = " [LOCAL]" if m.is_local else ""
        free_tag = " [FREE]" if m.is_free else ""
        click.echo(f"  {m.model_id:<30s} {m.provider_name:<12s} {m.tier.value:<10s} ctx={m.max_context_tokens:>7d}{local_tag}{free_tag}")


@model.command("route", help=_("Show routing decision for a task."))
@click.option("--tier", "-t", default="balanced", help=_("Task tier (fast/balanced/smart)"))
@click.option("--tokens", default=1000, help=_("Estimated token count"))
@click.option("--strategy", default="cost_optimal", help=_("Routing strategy"))
def model_route(tier: str, tokens: int, strategy: str) -> None:
    from autoai.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
    from autoai.llm.model_router.model_spec import ModelTier
    from autoai.llm.model_router.model_router import RoutingStrategy

    registry = ModelRegistry()
    registry.load_builtin_specs()
    policy = RoutingPolicy(strategy=RoutingStrategy(strategy))
    router = ModelRouter(registry=registry, policy=policy)

    model_tier = ModelTier(tier)
    decision = router.route(task_tier=model_tier, estimated_tokens=tokens)

    if decision:
        click.echo(f"  Model:    {decision.model_id}")
        click.echo(f"  Provider: {decision.provider_name}")
        click.echo(f"  Tier:     {decision.tier.value}")
        click.echo(f"  Est.Cost: ${decision.estimated_cost:.6f}")
        click.echo(f"  Reason:   {decision.reason}")
        if decision.degradation_path:
            click.echo(f"  Fallback: {' -> '.join(decision.degradation_path)}")
    else:
        click.echo(_("No routing decision found."), err=True)


@model.command("providers", help=_("Show registered providers and their health."))
def model_providers() -> None:
    from autoai.llm.model_router import ModelRegistry, OllamaProvider

    registry = ModelRegistry()
    registry.load_builtin_specs()

    ollama = OllamaProvider(auto_detect=True)
    if ollama.is_detected:
        registry.register_provider(ollama)

    click.echo(_("Built-in model specs:"))
    summary = registry.summary()
    for provider, count in summary.get("by_provider", {}).items():
        click.echo(f"  {provider}: {count} models")
    click.echo(f"\n  Total: {summary['total_models']} models, {summary['total_providers']} providers")

    if ollama.is_detected:
        click.echo(f"\n  Ollama: DETECTED at {ollama.base_url}")
        for m in ollama.list_models():
            click.echo(f"    - {m}")
    else:
        click.echo(f"\n  Ollama: not detected (install from https://ollama.com)")


# ======================================================================
# Dashboard command
# ======================================================================

@click.command(help=_("Launch terminal system dashboard (pure TUI, no browser)."))
@click.option("--refresh", "-r", default=1.0, help=_("Refresh rate in seconds"))
def dashboard(refresh: float) -> None:
    from autoai.app.dashboard import TerminalDashboard
    from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
    from pathlib import Path

    click.echo(_("Starting terminal dashboard..."))
    config = SystemConfig(
        autonomous=True,
        enable_health_monitor=True,
        enable_agent_pool=True,
        enable_tui=False,
        enable_task_scheduler=True,
        enable_model_router=True,
        detect_local_models=True,
    )
    system = MultiAgentSystem(config=config)
    try:
        system.setup()
    except Exception as e:
        click.echo(f"[warn] Partial setup: {e}")

    dash = TerminalDashboard(system=system, refresh_rate=refresh)
    click.echo(_("Press Ctrl+C to exit"))
    dash.run()
