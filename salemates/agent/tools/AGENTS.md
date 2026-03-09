# AGENTS.md: salemates/agent/tools

Tool implementations - capabilities the agent can use.

---

## OVERVIEW

Tools are capabilities the agent can invoke: file operations, web search, customer profiles, quote generation, shell execution, etc. All tools extend the `Tool` base class.

---

## STRUCTURE

```
tools/
├── base.py                # Tool abstract base class
├── registry.py            # ToolRegistry (registration, execution)
├── factory.py             # register_default_tools()
├── customer_profile_tool.py   # Customer profile management
├── quote_generator.py     # Quote generation
├── competitor_tool.py     # Competitor analysis
├── filesystem.py          # File operations (read, write, list)
├── shell.py               # Shell command execution
├── web.py                 # HTTP requests
├── websearch/             # Web search implementations
│   ├── base.py           # SearchBackend base
│   ├── brave.py          # Brave Search
│   ├── ddgs.py           # DuckDuckGo Search
│   ├── exa.py            # Exa Search
│   └── registry.py       # SearchBackendRegistry
├── message.py             # Message sending
├── spawn.py               # Spawn sub-agents
├── cron.py                # Cron job management
├── image.py               # Image generation
└── ov_file.py             # OpenViking file operations
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Create new tool | `base.py` | `Tool` |
| Register tool | `registry.py` | `ToolRegistry.register()` |
| Default tools | `factory.py` | `register_default_tools()` |
| Customer profiles | `customer_profile_tool.py` | `CustomerProfileTool` |
| Quote generation | `quote_generator.py` | `QuoteGeneratorTool` |
| Competitor analysis | `competitor_tool.py` | `CompetitorTool` |
| Web search | `websearch/` | `SearchBackend` |

---

## KEY CLASSES

### Tool (`base.py`)
```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str
    
    @property
    @abstractmethod
    def description(self) -> str
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]
    
    @abstractmethod
    async def execute(self, tool_context: ToolContext, **kwargs) -> str
    
    def to_schema(self) -> dict  # OpenAI function schema
```

### ToolContext (`base.py`)
```python
@dataclass
class ToolContext:
    session_key: SessionKey
    sandbox_manager: SandboxManager | None
    workspace_id: str
    sender_id: str | None
```

### ToolRegistry (`registry.py`)
```python
class ToolRegistry:
    def register(self, tool: Tool) -> None
    def get_definitions(self) -> list[dict]
    async def execute(self, name: str, args: dict, session_key, sandbox_manager, sender_id) -> str
```

---

## ADDING A NEW TOOL

1. Create new file `my_tool.py`:
```python
from salemates.agent.tools.base import Tool, ToolContext

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Does something useful"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input to process"}
            },
            "required": ["input"]
        }
    
    async def execute(self, ctx: ToolContext, input: str) -> str:
        # Implementation
        return "Result"
```

2. Register in `factory.py`:
```python
registry.register(MyTool())
```

---

## CONVENTIONS

- Tool names: `snake_case`
- Return strings (not complex objects)
- Use `ToolContext` for session/workspace access
- Validate params via `validate_params()` if needed

---

## ANTI-PATTERNS

- **NEVER** return complex objects - always return strings
- **NEVER** bypass `ToolRegistry` for tool execution
- **NEVER** skip parameter validation in production