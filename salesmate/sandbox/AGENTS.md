# AGENTS.md: salesmate/sandbox

Sandboxed code execution - isolated runtime for agent tools.

---

## OVERVIEW

Provides sandboxed execution environments for running code and shell commands safely. Multiple backends: OpenSandbox, SRT, AioSandbox, Direct.

---

## STRUCTURE

```
sandbox/
├── __init__.py         # Exports
├── base.py             # SandboxBackend base class
├── manager.py          # SandboxManager
└── backends/
    ├── __init__.py
    ├── opensandbox.py  # OpenSandbox backend
    ├── srt.py          # SRT backend
    ├── aiosandbox.py   # AioSandbox backend
    ├── direct.py       # Direct execution (no sandbox)
    └── ...
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Sandbox manager | `manager.py` | `SandboxManager` |
| Backend interface | `base.py` | `SandboxBackend` |
| OpenSandbox | `backends/opensandbox.py` | `OpenSandboxBackend` |
| SRT | `backends/srt.py` | `SRTBackend` |
| AioSandbox | `backends/aiosandbox.py` | `AioSandboxBackend` |
| Direct | `backends/direct.py` | `DirectBackend` |

---

## KEY CLASSES

### SandboxManager (`manager.py`)
```python
class SandboxManager:
    def __init__(self, backend: SandboxBackend, workspace_root: Path):
        ...
    
    def get_workspace_path(self, session_key: SessionKey) -> Path:
        """Get workspace directory for session."""
    
    async def execute(self, code: str, language: str = "python") -> str:
        """Execute code in sandbox."""
    
    def to_workspace_id(self, session_key: SessionKey) -> str:
        """Convert session key to workspace ID."""
```

### SandboxBackend (`base.py`)
```python
class SandboxBackend(ABC):
    @abstractmethod
    async def execute(self, code: str, language: str) -> str:
        """Execute code and return result."""
    
    @abstractmethod
    def get_workspace_path(self, workspace_id: str) -> Path:
        """Get workspace directory."""
```

---

## BACKENDS

| Backend | Description | Use Case |
|---------|-------------|----------|
| OpenSandbox | OpenSandbox.io API | Production, multi-tenant |
| SRT | Secure Runtime | Production, local |
| AioSandbox | Async sandbox | Development |
| Direct | No isolation | Development only |

---

## CONFIGURATION

```yaml
sandbox:
  backend: opensandbox
  mode: per-session
  workspace_root: ./workspace
```

---

## USAGE

```python
from salesmate.sandbox import SandboxManager
from salesmate.sandbox.backends.opensandbox import OpenSandboxBackend

backend = OpenSandboxBackend(api_key="...")
manager = SandboxManager(backend, workspace_root=Path("./workspace"))

# Execute code
result = await manager.execute("print('Hello')", language="python")

# Get session workspace
ws_path = manager.get_workspace_path(session_key)
```

---

## ANTI-PATTERNS

- **NEVER** use Direct backend in production
- **NEVER** execute untrusted code without sandbox
- **NEVER** skip timeout limits