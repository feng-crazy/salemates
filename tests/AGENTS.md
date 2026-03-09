# AGENTS.md: tests

Test suite for SaleMates AI - unit, integration, and acceptance tests.

---

## OVERVIEW

pytest-based testing with pytest-asyncio for async support. Organized by test type: unit (isolated components), integration (component interactions), acceptance (end-to-end scenarios).

---

## STRUCTURE

```
tests/
├── conftest.py              # Global fixtures
├── test_chat_functionality.py
├── unit/                    # Unit tests
│   ├── test_intent.py
│   ├── test_emotion.py
│   ├── test_guardrails.py
│   └── test_state_machine.py
├── integration/             # Integration tests
│   ├── test_rag.py
│   ├── test_followup.py
│   ├── test_sales_flow.py
│   └── test_feishu_channel.py
└── acceptance/              # Acceptance tests
    └── test_acceptance_criteria.py

testdata/                    # Test fixtures
├── mock_data.py
├── feishu_events/
├── conversations/
└── products/
```

---

## WHERE TO LOOK

| Task | File | Key Class |
|------|------|-----------|
| Global fixtures | `conftest.py` | `event_loop`, `temp_dir`, `client` |
| Intent tests | `unit/test_intent.py` | `TestIntentRecognizer` |
| Emotion tests | `unit/test_emotion.py` | `TestEmotionAnalyzer` |
| Guardrail tests | `unit/test_guardrails.py` | `TestGuardrails` |
| State machine tests | `unit/test_state_machine.py` | `TestSalesStageStateMachine` |
| RAG tests | `integration/test_rag.py` | `TestRAGSemanticSearch` |
| Sales flow tests | `integration/test_sales_flow.py` | `TestSalesFlow` |
| Acceptance criteria | `acceptance/test_acceptance_criteria.py` | AC1-AC7 |

---

## FIXTURES (conftest.py)

```python
@pytest.fixture
def event_loop():
    """Session-level event loop for async tests."""
    
@pytest.fixture
def temp_dir(tmp_path):
    """Auto-cleanup temporary directory."""
    
@pytest.fixture
def test_data_dir():
    """Path to testdata/ directory."""
    
@pytest.fixture
def client(test_data_dir):
    """AsyncOpenViking client for testing."""
```

---

## RUNNING TESTS

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Acceptance tests only
pytest tests/acceptance/

# With coverage
pytest tests/ -v --cov=salemates --cov-report=html

# Specific test file
pytest tests/unit/test_intent.py -v

# Specific test function
pytest tests/unit/test_intent.py::TestIntentRecognizer::test_recognize_price_objection
```

---

## ACCEPTANCE CRITERIA

| AC | Description | Test |
|----|-------------|------|
| AC1 | Basic Feishu connection (2s ACK) | `test_ac1_feishu_connection` |
| AC2 | Intent recognition (OBJECTION_PRICE) | `test_ac2_intent_recognition` |
| AC3 | RAG accuracy (correct doc retrieval) | `test_ac3_rag_accuracy` |
| AC4 | RAG hallucination prevention | `test_ac4_rag_hallucination` |
| AC5 | Sales strategy (HESITATION → SPIN) | `test_ac5_sales_strategy` |
| AC6 | Proactive followup (24h silence) | `test_ac6_proactive_followup` |
| AC7 | Stage transitions (complete flow) | `test_ac7_stage_transitions` |

---

## CONVENTIONS

- **Files**: `test_*.py`
- **Classes**: `Test*`
- **Functions**: `test_*`
- **Async tests**: `@pytest.mark.asyncio`
- **Fixtures**: Use `conftest.py` for global, inline for local
- **License header**: Apache 2.0 in all test files

---

## MOCK PATTERNS

```python
@dataclass
class MockLLMProvider:
    """Mock LLM provider for testing."""
    async def chat(self, messages, tools, model, session_id):
        return MockResponse(content="Test response")

@dataclass
class MockVectorStore:
    """Mock vector store for RAG testing."""
    async def search(self, query, k=5):
        return [("doc1", 0.9), ("doc2", 0.8)]
```

---

## ANTI-PATTERNS

- **NEVER** commit with failing tests
- **NEVER** use production credentials in tests
- **NEVER** skip `@pytest.mark.asyncio` for async tests
- **NEVER** leave temp files after tests - use `temp_dir` fixture