# AGENTS.md: bridge

TypeScript WhatsApp bridge - connects WhatsApp Web to Python backend.

---

## OVERVIEW

Node.js/TypeScript bridge using Baileys library for WhatsApp Web integration. Runs WebSocket server to communicate with Python backend. Handles QR authentication, message forwarding, and reconnection.

---

## STRUCTURE

```
bridge/
├── src/
│   ├── index.ts        # Entry point
│   ├── server.ts       # WebSocket server
│   ├── whatsapp.ts     # WhatsApp client (Baileys)
│   └── types.d.ts      # TypeScript type definitions
├── package.json        # npm dependencies
├── tsconfig.json       # TypeScript config
└── dist/               # Compiled JavaScript (generated)
```

---

## WHERE TO LOOK

| Task | File | Key Class/Function |
|------|------|-------------------|
| Entry point | `src/index.ts` | `main()` |
| WebSocket server | `src/server.ts` | `BridgeServer` |
| WhatsApp client | `src/whatsapp.ts` | `WhatsAppClient` |
| Types | `src/types.d.ts` | `Message`, `BridgeConfig` |

---

## KEY CLASSES

### BridgeServer (`server.ts`)
```typescript
class BridgeServer {
    constructor(port: number, token: string)
    start(): void
    onMessage(callback: (msg: Message) => void): void
    send(msg: Message): void
}
```

### WhatsAppClient (`whatsapp.ts`)
```typescript
class WhatsAppClient {
    connect(): Promise<void>
    disconnect(): void
    sendMessage(to: string, content: string): Promise<void>
    onMessage(callback: (msg: Message) => void): void
}
```

---

## BUILD & RUN

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Run bridge
npm start

# Development (build + run)
npm run dev
```

---

## ENVIRONMENT VARIABLES

| Variable | Default | Description |
|----------|---------|-------------|
| `BRIDGE_PORT` | 3001 | WebSocket server port |
| `BRIDGE_TOKEN` | - | Authentication token |
| `AUTH_DIR` | `./auth` | WhatsApp auth state directory |

---

## PROTOCOL

Python backend connects via WebSocket:

```
Python → Bridge: { "type": "send", "to": "1234567890", "content": "Hello" }
Bridge → Python: { "type": "message", "from": "1234567890", "content": "Hi" }
```

---

## ANTI-PATTERNS

- **NEVER** hardcode auth credentials
- **NEVER** expose bridge port publicly without authentication
- **NEVER** ignore QR code scans - handle gracefully

---

## NOTES

- Node.js >= 20.0.0 required
- Uses `@whiskeysockets/baileys` for WhatsApp Web
- Auth state persisted in `AUTH_DIR`
- Bundled into Python package during build