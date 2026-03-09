# AGENTS.md: salemates/session

Session state management - conversation persistence.

---

## OVERVIEW

Manages session state including message history, metadata, and persistence. Sessions are keyed by `SessionKey` (channel, chat_id) and stored in Redis or filesystem.

---

## STRUCTURE

```
session/
├── __init__.py     # Exports
└── manager.py      # SessionManager
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Session manager | `manager.py` | `SessionManager` |
| Session model | `manager.py` | `Session` |

---

## KEY CLASSES

### SessionManager (`manager.py`)
```python
class SessionManager:
    def __init__(self, data_path: Path, sandbox_manager=None):
        ...
    
    def get_or_create(self, session_key: SessionKey, skip_heartbeat: bool = False) -> Session:
        """Get existing session or create new one."""
    
    async def save(self, session: Session) -> None:
        """Persist session to storage."""
    
    def delete(self, session_key: SessionKey) -> None:
        """Delete session."""
    
    def list_sessions(self) -> list[SessionKey]:
        """List all active sessions."""
```

### Session (`manager.py`)
```python
@dataclass
class Session:
    key: SessionKey
    messages: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str, sender_id: str | None = None, tools_used: list | None = None):
        """Add message to history."""
    
    def get_history(self) -> list[dict]:
        """Get messages formatted for LLM."""
    
    def clear(self) -> None:
        """Clear message history."""
```

---

## SESSION STORAGE

Sessions stored in `bot_data_path/sessions/`:
```
bot_data/
└── sessions/
    └── telegram_bot1_123.json
```

---

## USAGE

```python
from salemates.session import SessionManager
from salemates.config.schema import SessionKey

manager = SessionManager(data_path=Path("./bot_data"))

# Get or create session
session = manager.get_or_create(SessionKey(
    type="telegram",
    channel_id="bot1",
    chat_id="123"
))

# Add message
session.add_message("user", "Hello", sender_id="user1")

# Save
await manager.save(session)

# Get history for LLM
history = session.get_history()
# [{"role": "user", "content": "Hello"}]
```

---

## ANTI-PATTERNS

- **NEVER** modify `session.messages` directly - use `add_message()`
- **NEVER** skip `save()` after modifications
- **NEVER** store large binary data in session - use media URLs