# AGENTS.md: salemates/channels

Multi-platform message handling - unified interface for all chat platforms.

---

## OVERVIEW

Implements channel adapters for Feishu, Telegram, WhatsApp, Slack, Discord, DingTalk, QQ, MoChat, Email, and OpenAPI. All channels extend `BaseChannel` and integrate with the message bus.

---

## STRUCTURE

```
channels/
├── base.py           # BaseChannel abstract class
├── manager.py        # ChannelManager (lifecycle)
├── utils.py          # Shared utilities
├── feishu.py         # Feishu/Lark adapter
├── telegram.py       # Telegram adapter
├── whatsapp.py       # WhatsApp adapter (via bridge)
├── slack.py          # Slack adapter
├── discord.py        # Discord adapter
├── dingtalk.py       # DingTalk adapter
├── qq.py             # QQ adapter
├── mochat.py         # MoChat adapter
├── email.py          # Email adapter
├── openapi.py        # OpenAPI adapter
├── chat.py           # Generic chat adapter
└── single_turn.py    # Single-turn message handler
```

---

## WHERE TO LOOK

| Task | File | Key Class/Function |
|------|------|-------------------|
| Add new channel | `base.py` | Extend `BaseChannel` |
| Channel lifecycle | `manager.py` | `ChannelManager` |
| Feishu webhook | `feishu.py` | `FeishuChannel` |
| Telegram bot | `telegram.py` | `TelegramChannel` |
| WhatsApp bridge | `whatsapp.py` | `WhatsAppChannel` |
| Slack bot | `slack.py` | `SlackChannel` |
| Permission check | `base.py` | `is_allowed()` |
| Message handling | `base.py` | `_handle_message()` |

---

## KEY CLASSES

### BaseChannel (`base.py`)
```python
class BaseChannel(ABC):
    name: str
    
    async def start(self) -> None           # Connect to platform
    async def stop(self) -> None            # Cleanup
    async def send(self, msg: OutboundMessage) -> None
    def is_allowed(self, sender_id: str) -> bool
    async def _handle_message(self, sender_id, chat_id, content, media, metadata)
```

### Message Flow
```
Platform Webhook → Channel._handle_message() → bus.publish_inbound(InboundMessage)
                                                          ↓
                                              AgentLoop._process_message()
                                                          ↓
                                              bus.publish_outbound(OutboundMessage)
                                                          ↓
                                              Channel.send()
```

---

## ADDING A NEW CHANNEL

1. Create `newplatform.py` extending `BaseChannel`:
```python
class NewPlatformChannel(BaseChannel):
    name = "newplatform"
    
    async def start(self) -> None:
        # Connect to platform, start listening
        
    async def stop(self) -> None:
        # Cleanup
        
    async def send(self, msg: OutboundMessage) -> None:
        # Send message to platform
```

2. Add config schema in `salemates/config/schema.py`:
```python
class NewPlatformChannelConfig(BaseChannelConfig):
    type: ChannelType = ChannelType.NEWPLATFORM
    api_key: str = ""
```

3. Register in `ChannelManager` (`manager.py`)

---

## CONVENTIONS

- All channels use `SessionKey` for routing (type, channel_id, chat_id)
- Use `self.bus.publish_inbound()` for incoming messages
- Check `is_allowed()` before processing
- Handle media via `_parse_data_uri()` and `_extract_images()`

---

## ANTI-PATTERNS

- **NEVER** block in `start()` - use async
- **NEVER** skip `is_allowed()` check
- **NEVER** send messages directly - use `bus.publish_outbound()`