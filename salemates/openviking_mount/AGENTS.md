# AGENTS.md: salemates/openviking_mount

FUSE filesystem integration for OpenViking - exposes LLM sessions as a filesystem.

---

## OVERVIEW

Mounts OpenViking sessions as a FUSE filesystem, allowing file-based access to LLM conversations, memory, and workspace files. Used for session persistence and debugging.

---

## STRUCTURE

```
openviking_mount/
├── mount.py             # FUSE mount entry point
├── manager.py           # MountManager (lifecycle)
├── viking_fuse.py       # FUSE operations implementation
├── fuse_simple.py       # Simple FUSE operations
├── fuse_simple_debug.py # Debug FUSE operations
├── fuse_finder.py       # File finding utilities
├── ov_server.py         # OpenViking server integration
├── fuse_proxy.py        # Proxy for FUSE operations
├── session_integration.py # Session management integration
├── user_apikey_manager.py # API key management
└── __init__.py
```

---

## WHERE TO LOOK

| Task | File | Key Class/Function |
|------|------|-------------------|
| Mount filesystem | `mount.py` | `mount_filesystem()` |
| Lifecycle management | `manager.py` | `MountManager` |
| FUSE operations | `viking_fuse.py` | `VikingFuse` |
| Debug operations | `fuse_simple_debug.py` | `DebugFuseOps` |
| OpenViking server | `ov_server.py` | `OVServer` |
| Session integration | `session_integration.py` | `SessionIntegration` |

---

## KEY CLASSES

### MountManager (`manager.py`)
```python
class MountManager:
    """Manages FUSE mount lifecycle."""
    def mount(self, mount_point: Path) -> None
    def unmount(self) -> None
    def is_mounted(self) -> bool
```

### VikingFuse (`viking_fuse.py`)
```python
class VikingFuse(fuse.Operations):
    """FUSE operations for OpenViking."""
    def getattr(self, path, fh=None)
    def readdir(self, path, fh)
    def read(self, path, size, offset, fh)
    def write(self, path, data, offset, fh)
```

---

## USAGE

```bash
# Mount OpenViking workspace
python -m salemates.openviking_mount /mnt/viking

# Access sessions as files
ls /mnt/viking/sessions/
cat /mnt/viking/sessions/telegram_12345/memory.md
```

---

## FILESYSTEM STRUCTURE

```
/mnt/viking/
├── sessions/
│   └── {session_key}/
│       ├── memory.md      # Long-term memory
│       ├── history.md     # Conversation history
│       └── workspace/     # Session workspace files
├── skills/                # Skill definitions
└── config/                # Configuration files
```

---

## ANTI-PATTERNS

- **NEVER** mount without cleanup handling
- **NEVER** write directly to memory files - use `MemoryStore`
- **NEVER** block FUSE operations - use async patterns

---

## NOTES

- Requires `fusepy` package (install: `pip install fusepy`)
- Linux/macOS only (FUSE not available on Windows)
- Unmount cleanly: `fusermount -u /mnt/viking` or `umount /mnt/viking`