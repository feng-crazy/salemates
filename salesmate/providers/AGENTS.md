# AGENTS.md: salesmate/providers

LLM provider abstractions - unified interface for multiple LLM backends.

---

## OVERVIEW

Provides abstraction over LLM providers via LiteLLM. Supports OpenAI, Anthropic, local models, and custom endpoints. Single interface for all LLM operations.

---

## STRUCTURE

```
providers/
├── __init__.py           # Exports
├── base.py               # LLMProvider abstract base
├── litellm_provider.py   # LiteLLM implementation
├── registry.py           # Provider registration
└── transcription.py      # Audio transcription
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Provider interface | `base.py` | `LLMProvider` |
| LiteLLM implementation | `litellm_provider.py` | `LiteLLMProvider` |
| Provider registration | `registry.py` | `ProviderRegistry` |
| Audio transcription | `transcription.py` | `TranscriptionService` |

---

## KEY CLASSES

### LLMProvider (`base.py`)
```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        session_id: str | None = None,
    ) -> LLMResponse:
        """Send chat completion request."""
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model identifier."""
```

### LLMResponse (`base.py`)
```python
@dataclass
class LLMResponse:
    content: str | None
    has_tool_calls: bool
    tool_calls: list[ToolCall]
    reasoning_content: str | None
    usage: dict[str, int]
```

### LiteLLMProvider (`litellm_provider.py`)
```python
class LiteLLMProvider(LLMProvider):
    """LiteLLM-based provider supporting OpenAI, Anthropic, etc."""
    
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "gpt-4"):
        ...
    
    async def chat(self, messages, tools, model, session_id) -> LLMResponse:
        # Uses litellm.acompletion()
```

---

## USAGE

```python
from salesmate.providers import LiteLLMProvider

provider = LiteLLMProvider(
    api_key="sk-...",
    model="gpt-4"
)

response = await provider.chat(
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

## SUPPORTED MODELS

Via LiteLLM:
- OpenAI: `gpt-4`, `gpt-3.5-turbo`
- Anthropic: `claude-3-opus`, `claude-3-sonnet`
- Local: `ollama/llama2`, `lmstudio/...`
- Custom: Any OpenAI-compatible endpoint

---

## ANTI-PATTERNS

- **NEVER** expose API keys in logs
- **NEVER** hardcode model names - use config
- **NEVER** ignore rate limits - handle gracefully