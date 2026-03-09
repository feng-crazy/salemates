# AGENTS.md: salemates/bus

Event-driven message bus - decouples channels from agent loop.

---

## OVERVIEW

Implements an async message bus for communication between channels and the agent loop. Supports inbound messages (from platforms) and outbound messages (to platforms).

---

## STRUCTURE

```
bus/
├── __init__.py     # Exports
├── events.py       # Event types (InboundMessage, OutboundMessage)
└── queue.py        # MessageBus implementation
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Message bus | `queue.py` | `MessageBus` |
| Inbound message | `events.py` | `InboundMessage` |
| Outbound message | `events.py` | `OutboundMessage` |
| Event types | `events.py` | `OutboundEventType` |

---

## KEY CLASSES

### MessageBus (`queue.py`)
```python
class MessageBus:
    async def publish_inbound(self, msg: InboundMessage) -> None:
        """Publish message from channel to agent."""
    
    async def consume_inbound(self) -> InboundMessage:
        """Consume next inbound message (blocks until available)."""
    
    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Publish message from agent to channel."""
    
    async def subscribe_outbound(self, callback: Callable[[OutboundMessage], None]) -> None:
        """Subscribe to outbound messages."""
```

### InboundMessage (`events.py`)
```python
@dataclass
class InboundMessage:
    sender_id: str                    # User identifier
    content: str                      # Message text
    session_key: SessionKey           # Session routing
    timestamp: datetime               # When received
    media: list[str]                  # Media URLs
    metadata: dict[str, Any]          # Platform-specific data
```

### OutboundMessage (`events.py`)
```python
@dataclass
class OutboundMessage:
    session_key: SessionKey
    content: str
    event_type: OutboundEventType = OutboundEventType.RESPONSE
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

### OutboundEventType (`events.py`)
```python
class OutboundEventType(str, Enum):
    RESPONSE = "response"       # Normal response
    TOOL_CALL = "tool_call"     # Tool being called
    TOOL_RESULT = "tool_result" # Tool result
    REASONING = "reasoning"     # Reasoning content
    ITERATION = "iteration"     # Iteration marker
```

---

## FLOW

```
Channel → bus.publish_inbound(InboundMessage)
                      ↓
         AgentLoop.consume_inbound()
                      ↓
         AgentLoop.process_message()
                      ↓
         bus.publish_outbound(OutboundMessage)
                      ↓
Channel ← bus.subscribe_outbound()
```

---

## USAGE

```python
from salemates.bus import MessageBus, InboundMessage, OutboundMessage

bus = MessageBus()

# Channel publishes inbound
await bus.publish_inbound(InboundMessage(
    session_key=SessionKey(type="telegram", channel_id="bot1", chat_id="123"),
    sender_id="user1",
    content="Hello"
))

# Agent loop consumes
msg = await bus.consume_inbound()

# Agent publishes outbound
await bus.publish_outbound(OutboundMessage(
    session_key=msg.session_key,
    content="Hi there!"
))
```

---

## ANTI-PATTERNS

- **NEVER** block in publish methods
- **NEVER** modify messages after publishing
- **NEVER** use bus for non-message communication