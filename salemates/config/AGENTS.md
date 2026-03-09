# AGENTS.md: salemates/config

Configuration management - Pydantic schema and loader.

---

## OVERVIEW

Defines configuration schema using Pydantic and provides loading from YAML files with environment variable interpolation.

---

## STRUCTURE

```
config/
├── __init__.py        # Exports load_config, get_config_path
├── loader.py          # Configuration loading from YAML
└── schema.py          # Pydantic configuration models
```

---

## WHERE TO LOOK

| Task | File | Key Class/Function |
|------|------|-------------------|
| Load config | `loader.py` | `load_config()` |
| Config path | `loader.py` | `get_config_path()` |
| Main schema | `schema.py` | `Config` |
| Channel configs | `schema.py` | `TelegramChannelConfig`, `FeishuChannelConfig`, etc. |
| Session key | `schema.py` | `SessionKey` |
| Sandbox config | `schema.py` | `SandboxConfig` |

---

## KEY CLASSES

### Config (`schema.py`)
```python
class Config(BaseModel):
    app: AppConfig
    gateway: GatewayConfig
    llm: LLMConfig
    database: DatabaseConfig
    redis: RedisConfig
    channels: list[BaseChannelConfig]
    sandbox: SandboxConfig
    workspace: WorkspaceConfig
```

### SessionKey (`schema.py`)
```python
class SessionKey(BaseModel):
    type: str          # Channel type (telegram, feishu, etc.)
    channel_id: str    # Channel instance ID
    chat_id: str       # Chat/conversation ID
    
    def safe_name(self) -> str:
        return f"{self.type}_{self.channel_id}_{self.chat_id}"
```

### Channel Configs
```python
class TelegramChannelConfig(BaseChannelConfig):
    type: ChannelType = ChannelType.TELEGRAM
    token: str
    allow_from: list[str]
    proxy: str | None

class FeishuChannelConfig(BaseChannelConfig):
    type: ChannelType = ChannelType.FEISHU
    app_id: str
    app_secret: str
    encrypt_key: str
    verification_token: str
```

---

## LOADING

```python
from salemates.config import load_config

config = load_config()  # Loads from config/salemates.yaml
```

---

## CONFIGURATION FILE

`config/salemates.yaml`:
```yaml
app:
  name: salemates
  log_level: INFO

gateway:
  http_port: 18790
  ws_port: 18791

llm:
  provider: litellm
  model: gpt-4
  api_key: ${OPENAI_API_KEY}  # Env var interpolation

channels:
  - type: telegram
    token: ${TELEGRAM_BOT_TOKEN}
    allow_from: []
```

---

## ANTI-PATTERNS

- **NEVER** hardcode secrets - use env vars
- **NEVER** modify config at runtime - use immutable pattern
- **NEVER** skip validation - Pydantic handles it