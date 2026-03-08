# PROJECT KNOWLEDGE BASE: SalesMate AI

**Generated:** 2026-03-08
**Stack:** Python 3.11+ (primary), TypeScript/Node.js 20+ (bridge)

---

## OVERVIEW

24/7 autonomous sales agent with multi-channel integration. AI-powered conversational platform implementing SPIN/FAB/BANT sales methodologies with safety guardrails and human handoff.

---

## STRUCTURE

```
salesmate/              # Main Python package
├── agent/              # Core AI agent logic (loop, tools, safety, stages)
├── channels/           # Multi-platform adapters (Feishu, Telegram, WhatsApp, etc.)
├── bus/                # Event-driven message bus
├── cli/                # Typer CLI commands
├── config/             # Pydantic configuration schema
├── console/            # Gradio web console
├── cron/               # Scheduled task service
├── hooks/              # Plugin hook system
├── integrations/       # Third-party integrations (Langfuse)
├── openviking_mount/   # FUSE filesystem for OpenViking
├── providers/          # LLM provider abstractions (LiteLLM)
├── sandbox/            # Sandboxed code execution backends
├── session/            # Session state management
└── utils/              # Utilities (tracing, helpers)

bridge/                 # TypeScript WhatsApp bridge (Baileys)
config/                 # Configuration templates (YAML)
deploy/                 # Docker, Kubernetes (VKE) configs
tests/                  # Test suite (unit, integration, acceptance)
workspace/              # Runtime workspace (skills, memory)
```

---

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Entry point | `salesmate/__main__.py`, `salesmate/cli/commands.py` | CLI via Typer |
| Agent loop | `salesmate/agent/loop.py` | Core processing engine |
| Add channel | `salesmate/channels/` | Extend `BaseChannel` |
| Add tool | `salesmate/agent/tools/` | Extend `Tool` class |
| Safety rules | `salesmate/agent/safety/guardrails.py` | Price, contract, feature, competitor |
| Config schema | `salesmate/config/schema.py` | Pydantic models |
| Tests | `tests/unit/`, `tests/integration/`, `tests/acceptance/` | pytest + pytest-asyncio |

---

## CONVENTIONS

**Python:**
- Line length: 100 chars (ruff)
- Lint rules: E, F, I, N, W (ignore E501)
- Type hints required
- Google-style docstrings
- Private methods: `_underscore_prefix`

**Naming:**
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- Files: `snake_case.py`

**TypeScript (bridge):**
- ES2022 target, strict mode enabled
- ESM modules

---

## ANTI-PATTERNS

- **NEVER** use bare `except:` clauses - catch specific exceptions
- **NEVER** skip to pricing when customer shows hesitation - use SPIN first
- **NEVER** commit hardcoded secrets or API keys
- **NEVER** use bare `except Exception:` without handling specific errors
- **ALWAYS** use `secrets.compare_digest()` for timing-safe comparisons

---

## COMMANDS

```bash
# Development
make dev          # Start Docker dev environment (ports 18790, 18791, 6379, 5432)
make install      # pip install -e ".[dev,test,feishu]"
make test         # pytest tests/ -v --cov=salesmate
make lint         # ruff check . && ruff format --check .

# CLI
salesmate gateway   # Start gateway server (default ports 18790/18791)
salesmate chat      # Interactive chat with agent
salesmate status    # Show bot status
salesmate cron list # Manage scheduled jobs

# Docker
docker build -t salesmate:latest .
docker-compose up -d

# Bridge (TypeScript)
cd bridge && npm install && npm run build
```

---

## PORTS

| Service | Port | Purpose |
|---------|------|---------|
| HTTP API | 18790 | Main API endpoint |
| Gateway/Console | 18791 | WebSocket gateway, Gradio console |
| Redis | 6379 | Session cache |
| PostgreSQL | 5432 | Persistent storage |
| OpenViking | 1933 | LLM service |
| WhatsApp Bridge | 3001 | Node.js WebSocket bridge |

---

## KEY ARCHITECTURE

### Agent Loop Flow
```
Message → Intent Recognition → Emotion Analysis → Strategy Engine → Safety Guardrails → Response
```

### Sales Pipeline Stages
```
NewContact → Discovery → Presentation → Negotiation → Close/Lost
```

### Safety System
- **Guardrails**: Price, Contract, Feature, Competitor
- **Emotion Fuse**: Threshold-based triggers for human handoff
- **Confidence Router**: High/Medium/Low routing decisions

### Channels (Multi-Platform)
Extend `BaseChannel` in `salesmate/channels/base.py`:
- `start()` - Connect to platform
- `stop()` - Cleanup
- `send(msg)` - Send message
- `_handle_message()` - Process inbound

---

## TESTING

```bash
pytest tests/                           # All tests
pytest tests/unit/                      # Unit tests
pytest tests/integration/               # Integration tests
pytest tests/acceptance/                # Acceptance tests
pytest -v --cov=salesmate --cov-report=html  # With coverage
```

**Conventions:**
- Files: `test_*.py`
- Classes: `Test*`
- Functions: `test_*`
- Async: `@pytest.mark.asyncio`
- Fixtures: `tests/conftest.py`

---

## NOTES

- No GitHub Actions CI/CD - uses Makefile for build automation
- Hybrid stack: Python backend + Node.js bridge
- Optional dependencies for channels in `pyproject.toml` (telegram, feishu, slack, etc.)
- License: Apache 2.0 (see LICENSE file)