# AGENTS.md: salemates/agent/profile

Customer profile extraction and personalization - enabling "thousand-person-thousand-faces".

---

## OVERVIEW

This module provides intelligent extraction of customer information from conversations
and generates personalized sales strategies. It integrates with OpenViking for
long-term memory and semantic search.

---

## STRUCTURE

```
profile/
├── __init__.py           # Exports
├── extractor.py          # CustomerProfileExtractor - BANT extraction
├── personalization.py    # PersonalizationEngine - strategy generation
├── memory_manager.py     # EnhancedMemoryManager - unified memory access
└── AGENTS.md            # This file
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Extract BANT from text | `extractor.py` | `CustomerProfileExtractor` |
| Generate personalized strategy | `personalization.py` | `PersonalizationEngine` |
| Unified memory access | `memory_manager.py` | `EnhancedMemoryManager` |
| Customer context | `memory_manager.py` | `CustomerMemoryContext` |

---

## KEY CLASSES

### CustomerProfileExtractor (`extractor.py`)

```python
class CustomerProfileExtractor:
    """Extracts BANT data, pain points, preferences from conversation."""
    
    async def extract(
        self, 
        conversation: str, 
        current_profile: CustomerProfile | None = None
    ) -> ProfileExtractionResult:
        """Extract customer info from text."""
    
    async def apply_updates(
        self, 
        profile: CustomerProfile, 
        result: ProfileExtractionResult
    ) -> CustomerProfile:
        """Apply extracted info to profile."""
```

### PersonalizationEngine (`personalization.py`)

```python
class PersonalizationEngine:
    """Generates personalized strategies based on customer profile."""
    
    async def generate_strategy(
        self,
        context: PersonalizationContext,
        situation: str,
        recent_emotion: str = "neutral"
    ) -> StrategySuggestion:
        """Generate personalized strategy suggestion."""
    
    def infer_communication_style(self, profile: CustomerProfile) -> CommunicationStyle:
        """Infer how to communicate with this customer."""
    
    def infer_decision_style(self, profile: CustomerProfile) -> DecisionStyle:
        """Infer customer's decision-making style."""
```

### EnhancedMemoryManager (`memory_manager.py`)

```python
class EnhancedMemoryManager:
    """Unified access to CustomerProfile + OpenViking memory."""
    
    async def get_context(
        self,
        user_id: str,
        current_message: str,
        workspace_id: str,
        session_history: list[dict] | None = None
    ) -> CustomerMemoryContext:
        """Get comprehensive context for a customer."""
```

### CustomerMemoryContext (`memory_manager.py`)

```python
@dataclass
class CustomerMemoryContext:
    """Combined context from memory and customer profile."""
    customer_profile: CustomerProfile
    long_term_memory: str
    user_profile: str
    recent_memories: list[dict]
    personalization_hints: dict
    
    def to_prompt_context(self) -> str:
        """Format as context string for LLM prompt."""
```

---

## USAGE

### Extract Profile from Conversation

```python
from salemates.agent.profile import CustomerProfileExtractor
from salemates.agent.models.customer import CustomerProfile

extractor = CustomerProfileExtractor(provider, model="gpt-4")

result = await extractor.extract(
    conversation="我们预算50万，我是技术总监，需要团队协作工具",
    current_profile=CustomerProfile(id="user_123")
)

print(result.bant_updates)
# {'budget': 500000, 'authority': '技术总监'}

print(result.pain_points)
# ['需要团队协作工具']

profile = CustomerProfile(id="user_123")
await extractor.apply_updates(profile, result)
```

### Generate Personalized Strategy

```python
from salemates.agent.profile import (
    PersonalizationEngine, 
    PersonalizationContext,
    CommunicationStyle
)

engine = PersonalizationEngine(provider)

context = PersonalizationContext(
    customer_id="user_123",
    profile=customer_profile,
    communication_style=CommunicationStyle.TECHNICAL,
    decision_style=DecisionStyle.COMPARATIVE
)

suggestion = await engine.generate_strategy(
    context=context,
    situation="客户询问价格",
    recent_emotion="neutral"
)

print(suggestion.content)
print(suggestion.reasoning)
print(suggestion.stage_transition_hint)
```

### Get Unified Memory Context

```python
from salemates.agent.profile import EnhancedMemoryManager

manager = EnhancedMemoryManager(provider, workspace, model="gpt-4")

context = await manager.get_context(
    user_id="user_123",
    current_message="我想了解你们的报价",
    workspace_id="workspace_001",
    session_history=session.messages
)

# Use in LLM prompt
system_prompt = f"""
{context.to_prompt_context()}

Based on the above customer information, provide a personalized response.
"""
```

---

## INTEGRATION WITH AGENT LOOP

To integrate with `AgentLoop`, modify `context.py` to use `EnhancedMemoryManager`:

```python
# In ContextBuilder.build_system_prompt()
from salemates.agent.profile import EnhancedMemoryManager

class ContextBuilder:
    def __init__(self, workspace, provider=None, ...):
        self.enhanced_memory = EnhancedMemoryManager(
            provider=provider,
            workspace=workspace
        ) if provider else None
    
    async def build_system_prompt(self, session_key, current_message, history):
        # ... existing code ...
        
        # Add enhanced customer context
        if self.enhanced_memory and sender_id:
            customer_context = await self.enhanced_memory.get_context(
                user_id=sender_id,
                current_message=current_message,
                workspace_id=workspace_id,
                session_history=history
            )
            parts.append(customer_context.to_prompt_context())
```

---

## DATA FLOW

```
User Message
     │
     ▼
┌─────────────────────────────────┐
│    CustomerProfileExtractor     │
│  Extract: BANT, Pain Points,    │
│  Preferences, Signals           │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│      CustomerProfile            │
│  Updated with extracted data    │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│   PersonalizationEngine         │
│  Generate strategy based on     │
│  profile + preferences          │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│     EnhancedMemoryManager       │
│  Store in OpenViking            │
│  Semantic search for context    │
└─────────────────────────────────┘
```

---

## ANTI-PATTERNS

- **NEVER** extract on every message - use threshold (min_messages=3)
- **NEVER** ignore extraction failures - log and continue gracefully
- **NEVER** store sensitive data without encryption
- **NEVER** bypass profile cache for frequent lookups

---

## FUTURE ENHANCEMENTS

1. **Profile Persistence**: Store CustomerProfile in PostgreSQL
2. **Learning from Feedback**: Track successful/failed approaches
3. **Multi-modal Extraction**: Extract from images, voice transcripts
4. **A/B Testing**: Compare personalization strategies