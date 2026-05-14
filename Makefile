# AutoAI Unified Makefile
# All project operations accessible through a single entry point.
# Usage: make <target>   or   make help

.PHONY: help install dev test lint fmt clean run \
        skill-search skill-add skill-test \
        orchestrate-start orchestrate-blueprint \
        evolve-run evolve-seed \
        ingest plugin-generate plugin-install-deps \
        governance-list governance-audit \
        tui doctor docker-build docker-run

DEFAULT_GOAL := help

# ============================================================
# Configuration
# ============================================================
PYTHON      ?= python
PIP         ?= pip
AGPT        ?= aai
PYTEST      ?= pytest
DOCKER      ?= docker
NODE        ?= node
NPM         ?= npm

# ============================================================
# Help
# ============================================================
help: ## Show this help message
	@echo "AutoAI Unified Command Reference"
	@echo "=================================="
	@echo ""
	@echo "Core Commands:"
	@echo "  make run              Start AutoAI assistant"
	@echo "  make install          Install project dependencies"
	@echo "  make dev              Install with dev dependencies"
	@echo "  make test             Run test suite"
	@echo "  make lint             Run all linters"
	@echo "  make fmt              Auto-format code"
	@echo "  make clean            Remove build artifacts"
	@echo ""
	@echo "Skill Management:"
	@echo "  make skill-search q=  Search skills (q=QUERY)"
	@echo "  make skill-add p=     Add skill (p=PATH)"
	@echo "  make skill-test s=    Test skill (s=NAME)"
	@echo ""
	@echo "Orchestration:"
	@echo "  make orchestrate-start   Start orchestrator"
	@echo "  make orchestrate-blueprint  Start blueprint orchestrator"
	@echo ""
	@echo "Evolution:"
	@echo "  make evolve-run      Run strategy evolution"
	@echo "  make evolve-seed     Generate seed population"
	@echo ""
	@echo "Data & Plugins:"
	@echo "  make ingest p=       Ingest files (p=PATHS)"
	@echo "  make plugin-generate  Generate plugins from specs"
	@echo "  make plugin-install-deps  Install plugin dependencies"
	@echo ""
	@echo "Governance:"
	@echo "  make governance-list  List approval requests"
	@echo "  make governance-audit Show audit log"
	@echo ""
	@echo "Other:"
	@echo "  make tui             Launch TUI"
	@echo "  make doctor          Run health check"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-run      Run Docker container"

# ============================================================
# Core
# ============================================================
install: ## Install project
	$(PIP) install -e .

dev: ## Install with dev dependencies
	$(PIP) install -e ".[dev]"

test: ## Run test suite with coverage
	$(PYTEST) --cov=autoai --cov-report=term-missing -q

lint: ## Run all linters (black, ruff, mypy)
	black --check .
	ruff check .
	mypy autoai/

fmt: ## Auto-format code
	black .
	ruff check --fix .
	isort .

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

run: ## Start AutoAI assistant
	$(AGPT)

# ============================================================
# Skill Management
# ============================================================
skill-search: ## Search skills (set q=QUERY)
	$(AGPT) skill search "$(q)"

skill-add: ## Add skill (set p=PATH)
	$(AGPT) skill add "$(p)"

skill-test: ## Test skill (set s=NAME)
	$(AGPT) skill test "$(s)"

# ============================================================
# Orchestration
# ============================================================
orchestrate-start: ## Start orchestrator
	$(AGPT) orchestrate start

orchestrate-blueprint: ## Start blueprint orchestrator
	$(AGPT) orchestrate blueprint --charter-url "$(charter_url)"

# ============================================================
# Evolution
# ============================================================
evolve-run: ## Run strategy evolution
	$(AGPT) evolve run -g $(generations)

evolve-seed: ## Generate seed population
	$(AGPT) evolve seed -n $(population)

# ============================================================
# Data & Plugins
# ============================================================
ingest: ## Ingest files (set p=PATHS)
	$(AGPT) ingest "$(p)"

plugin-generate: ## Generate plugins from specs
	$(AGPT) plugin generate plugins/

plugin-install-deps: ## Install plugin dependencies
	$(AGPT) plugin install-deps

# ============================================================
# Governance
# ============================================================
governance-list: ## List approval requests
	$(AGPT) governance list

governance-audit: ## Show audit log
	$(AGPT) governance audit

# ============================================================
# TUI & Health
# ============================================================
tui: ## Launch TUI
	$(AGPT) tui

doctor: ## Run health diagnostics
	$(AGPT) doctor

# ============================================================
# Docker
# ============================================================
docker-build: ## Build Docker image
	$(DOCKER) build -t autoai .

docker-run: ## Run Docker container
	$(DOCKER) run -it --rm autoai

# ============================================================
# Legacy script compatibility (deprecated, use aai commands)
# ============================================================
run-orchestrator: ## [DEPRECATED] Use: aai orchestrate start
	$(AGPT) orchestrate start

run-blueprint: ## [DEPRECATED] Use: aai orchestrate blueprint
	$(AGPT) orchestrate blueprint --charter-url "$(charter_url)"

run-executor: ## [DEPRECATED] Use: aai orchestrate execute
	$(AGPT) orchestrate execute "$(goal)"

launch-tui: ## [DEPRECATED] Use: aai tui
	$(AGPT) tui

approve-fix: ## [DEPRECATED] Use: aai governance approve
	$(AGPT) governance approve "$(request_id)"
