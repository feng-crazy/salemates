# AGENTS.md: salemates/agent/safety

Safety mechanisms - guardrails, emotion fuse, confidence routing, human handoff.

---

## OVERVIEW

Prevents unauthorized commitments and policy violations. Four types of guardrails: Price, Contract, Feature, Competitor. Plus emotion-based handoff and confidence-based routing.

---

## STRUCTURE

```
safety/
├── guardrails.py           # Rule-based safety checks
├── emotion_fuse.py         # Emotional safety (handoff triggers)
├── confidence_router.py    # Confidence-based routing
├── human_handoff.py        # Human escalation system
└── __init__.py
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Add guardrail | `guardrails.py` | `GuardrailManager` |
| Price rules | `guardrails.py` | `PriceGuardrail` |
| Contract rules | `guardrails.py` | `ContractGuardrail` |
| Feature rules | `guardrails.py` | `FeatureGuardrail` |
| Competitor rules | `guardrails.py` | `CompetitorGuardrail` |
| Emotion handoff | `emotion_fuse.py` | `EmotionFuse` |
| Confidence routing | `confidence_router.py` | `ConfidenceRouter` |
| Human escalation | `human_handoff.py` | `HumanHandoffManager` |

---

## KEY CLASSES

### GuardrailType (`guardrails.py`)
```python
class GuardrailType(str, Enum):
    PRICE = "price"           # Unauthorized pricing/discount
    CONTRACT = "contract"     # Unauthorized contract terms
    FEATURE = "feature"       # Claims about unverified features
    COMPETITOR = "competitor" # False competitor comparisons
```

### ViolationSeverity (`guardrails.py`)
```python
class ViolationSeverity(str, Enum):
    WARNING = "warning"  # Soft alert - warn but allow
    BLOCK = "block"      # Hard block - prevent response
    REVIEW = "review"    # Flag for human review
```

### GuardrailManager (`guardrails.py`)
```python
class GuardrailManager:
    def add_guardrail(self, guardrail: Guardrail) -> None
    def check(self, response: str) -> list[GuardrailViolation]
```

### PriceGuardrail
- Max discount: 15% (configurable)
- Detects: "20%折扣", "打个折", "优惠"
- Severity: WARNING if within limit, BLOCK if exceeded

### ContractGuardrail
- Blocks: contract commitments, legal terms
- Severity: BLOCK (must route to human)

### EmotionFuse (`emotion_fuse.py`)
```python
class EmotionFuse:
    """Triggers human handoff based on emotion thresholds."""
    anger_threshold: float = 0.7
    frustration_threshold: float = 0.7
```

### ConfidenceRouter (`confidence_router.py`)
```python
class ConfidenceRouter:
    """Routes based on confidence score."""
    HIGH = 0.9      # Direct auto-reply
    MEDIUM = 0.6    # Draft for human review
    LOW = 0.0       # Immediate human handoff
```

---

## FLOW

```
AI Response → Guardrails.check() → Violations?
                                      ↓ Yes
                                  Severity decision
                                      ↓
                      WARNING: Log, allow
                      BLOCK: Prevent, notify human
                      REVIEW: Queue for review
```

---

## ANTI-PATTERNS

- **NEVER** skip guardrail check before sending response
- **NEVER** allow discount > max_discount_percent
- **NEVER** make contract commitments without human approval
- **NEVER** claim unverified features

---

## CONFIGURATION

In `config/salemates.yaml`:
```yaml
safety:
  price_guardrail:
    enabled: true
    max_discount_percent: 15.0
  emotion_fuse:
    enabled: true
    anger_threshold: 0.7
```