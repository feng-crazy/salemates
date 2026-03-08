# AGENTS.md: salesmate/agent

Core AI agent logic - the brain of the sales agent.

---

## OVERVIEW

Implements the agent loop, tool execution, memory management, sales stages, safety mechanisms, and strategies.

---

## STRUCTURE

```
agent/
├── loop.py           # Core processing engine (AgentLoop)
├── context.py        # ContextBuilder for message assembly
├── memory.py         # MemoryStore (short-term + long-term)
├── skills.py         # SkillsLoader for agent capabilities
├── subagent.py       # SubagentManager for spawning sub-agents
├── tools/            # Tool implementations
├── stages/           # Sales stage state machine
├── strategies/       # Sales strategies (SPIN, FAB, BANT)
├── safety/           # Guardrails and human handoff
├── intent/           # Intent recognition
├── emotion/          # Emotion analysis
├── followup/         # Proactive follow-up engine
├── repositories/     # Data repositories (customer)
└── models/           # Data models (customer profile)
```

---

## WHERE TO LOOK

| Task | File | Key Class/Function |
|------|------|-------------------|
| Main loop | `loop.py` | `AgentLoop` |
| Message context | `context.py` | `ContextBuilder.build_messages()` |
| Memory | `memory.py` | `MemoryStore` |
| Sales stages | `stages/state_machine.py` | `SalesStageStateMachine` |
| Stage transitions | `stages/transitions.py` | `StageTransitionEngine` |
| Tools registry | `tools/registry.py` | `ToolRegistry` |
| Tool base | `tools/base.py` | `Tool` |
| Add new tool | `tools/*.py` | Extend `Tool` class |
| Intent recognition | `intent/recognizer.py` | `IntentRecognizer` |
| Emotion analysis | `emotion/analyzer.py` | `EmotionAnalyzer` |
| Follow-up engine | `followup/engine.py` | `FollowUpEngine` |

---

## KEY CLASSES

### AgentLoop (`loop.py`)
```python
class AgentLoop:
    """Core processing engine."""
    def __init__(self, bus, provider, workspace, model, config, ...)
    async def run(self) -> None           # Main loop
    async def _process_message(msg)       # Process inbound
    async def _run_agent_loop(messages)   # LLM + tool execution
    async def process_direct(content)     # CLI/cron usage
```

**Flow:**
1. Receive message from bus
2. Get/create session
3. Build context (history + memory + skills)
4. Call LLM
5. Execute tool calls (if any)
6. Send response to bus

### Tool (`tools/base.py`)
```python
class Tool(ABC):
    @property
    def name(self) -> str
    @property
    def description(self) -> str
    @property
    def parameters(self) -> dict
    async def execute(self, context: ToolContext, **kwargs) -> str
```

### SalesStageStateMachine (`stages/state_machine.py`)
```
NEW_CONTACT → DISCOVERY → PRESENTATION → NEGOTIATION → CLOSE
                  ↓              ↓              ↓
               LOST           LOST           LOST
```

---

## CONVENTIONS

- All tools extend `Tool` base class
- Use `ToolContext` for runtime context
- Register tools via `ToolRegistry.register()`
- Stage transitions must be validated via `can_transition()`
- Memory consolidation via `MemoryStore.append_history()`

---

## ANTI-PATTERNS

- **NEVER** bypass `AgentLoop` for direct LLM calls in production
- **NEVER** skip stage validation - use `can_transition()` before `transition()`
- **NEVER** hardcode tool definitions - use `to_schema()` method