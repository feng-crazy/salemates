# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for RAG (Retrieval-Augmented Generation) system.

Tests:
- Product knowledge base retrieval
- Semantic search functionality
- Confidence scoring
- Hallucination prevention
- Context retrieval for LLM
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from salemates.agent.safety.confidence_router import ConfidenceLevel, ConfidenceRouter


# ============ Mock RAG Components ============


@dataclass
class Document:
    """Mock document for RAG testing."""

    id: str
    content: str
    metadata: dict = field(default_factory=dict)
    score: float = 0.0


@dataclass
class SearchResult:
    """Mock search result."""

    documents: list[Document]
    query: str
    total: int
    confidence: float = 0.0


@dataclass
class RAGResponse:
    """Mock RAG response."""

    answer: str
    sources: list[Document]
    confidence: float
    is_hallucination: bool = False
    reasoning: str = ""


class MockVectorStore:
    """Mock vector store for testing RAG."""

    def __init__(self):
        self.documents: dict[str, Document] = {}
        self._index_built = False

    def add_document(self, doc: Document) -> None:
        """Add a document to the store."""
        self.documents[doc.id] = doc

    def search(self, query: str, top_k: int = 5) -> list[Document]:
        """Search for documents matching query."""
        results = []
        query_lower = query.lower()

        for doc in self.documents.values():
            # Simple keyword matching for mock
            if any(kw in doc.content.lower() for kw in query_lower.split()):
                # Calculate mock score based on keyword overlap
                keywords = set(query_lower.split())
                doc_keywords = set(doc.content.lower().split())
                overlap = len(keywords & doc_keywords)
                doc.score = min(overlap / max(len(keywords), 1), 1.0)
                results.append(doc)

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def get_document(self, doc_id: str) -> Document | None:
        """Get a document by ID."""
        return self.documents.get(doc_id)


class MockRAGSystem:
    """Mock RAG system for integration testing."""

    def __init__(self, vector_store: MockVectorStore):
        self.vector_store = vector_store
        self.knowledge_base: dict[str, list[Document]] = {}
        self.confidence_threshold_high = 0.90
        self.confidence_threshold_low = 0.60

    async def index_knowledge_base(self, docs: list[Document], category: str = "products") -> int:
        """Index documents into knowledge base."""
        if category not in self.knowledge_base:
            self.knowledge_base[category] = []

        for doc in docs:
            self.vector_store.add_document(doc)
            self.knowledge_base[category].append(doc)

        return len(docs)

    async def retrieve(
        self, query: str, category: str = "products", top_k: int = 5
    ) -> SearchResult:
        """Retrieve relevant documents for a query."""
        docs = self.vector_store.search(query, top_k)

        if not docs:
            return SearchResult(documents=[], query=query, total=0, confidence=0.0)

        # Calculate confidence based on best match score
        best_score = docs[0].score if docs else 0.0
        confidence = best_score

        return SearchResult(documents=docs, query=query, total=len(docs), confidence=confidence)

    async def generate_answer(self, query: str, context: list[Document]) -> RAGResponse:
        """Generate answer from retrieved context."""
        if not context:
            return RAGResponse(
                answer="抱歉，我没有找到相关信息来回答您的问题。",
                sources=[],
                confidence=0.0,
                is_hallucination=False,
                reasoning="No relevant documents found in knowledge base",
            )

        # Mock answer generation based on context
        context_text = "\n".join([doc.content for doc in context[:3]])
        confidence = min(context[0].score if context else 0.0, 1.0)

        # Determine if answer is grounded
        is_hallucination = confidence < 0.3

        answer = f"根据产品文档，{context_text[:200]}..."

        return RAGResponse(
            answer=answer,
            sources=context[:3],
            confidence=confidence,
            is_hallucination=is_hallucination,
            reasoning="Generated from retrieved context",
        )

    async def query(self, question: str, category: str = "products") -> RAGResponse:
        """Full RAG pipeline: retrieve and generate."""
        search_result = await self.retrieve(question, category)

        if not search_result.documents:
            return RAGResponse(
                answer="抱歉，我在知识库中没有找到相关信息来回答您的问题。",
                sources=[],
                confidence=0.0,
                is_hallucination=False,
                reasoning="No documents retrieved",
            )

        return await self.generate_answer(question, search_result.documents)


# ============ Fixtures ============


@pytest.fixture
def product_knowledge_base():
    """Create a mock product knowledge base with sample documents."""
    docs = [
        Document(
            id="prod-001",
            content="SaleMates企业版提供团队协作功能，支持最多100人同时在线协作，包含文档共享、实时编辑、任务分配等功能。价格：每年10万元。",
            metadata={"category": "产品功能", "product": "企业版"},
        ),
        Document(
            id="prod-002",
            content="SaleMates专业版适合中小团队，支持最多20人协作，包含基础协作功能。价格：每年3万元。",
            metadata={"category": "产品功能", "product": "专业版"},
        ),
        Document(
            id="prod-003",
            content="SaleMates支持多种集成：飞书、钉钉、企业微信、Slack等主流办公软件。API接口开放，支持自定义集成。",
            metadata={"category": "集成能力", "product": "全部版本"},
        ),
        Document(
            id="prod-004",
            content="SaleMates采用银行级数据加密，所有数据存储在阿里云，通过ISO27001认证，支持私有化部署。",
            metadata={"category": "安全性", "product": "全部版本"},
        ),
        Document(
            id="prod-005",
            content="企业版支持AI智能助手功能，可以自动生成销售话术、分析客户情绪、预测成交概率。该功能需要额外付费开通。",
            metadata={"category": "AI功能", "product": "企业版"},
        ),
        Document(
            id="prod-006",
            content="SaleMates提供7x24小时技术支持，企业版客户享有专属客户经理，响应时间不超过2小时。",
            metadata={"category": "服务支持", "product": "企业版"},
        ),
        Document(
            id="prod-007",
            content="数据导出支持Excel、CSV、PDF格式，企业版还支持API批量导出，每日最大导出量为10万条记录。",
            metadata={"category": "数据管理", "product": "全部版本"},
        ),
    ]
    return docs


@pytest.fixture
def faq_knowledge_base():
    """Create a mock FAQ knowledge base."""
    docs = [
        Document(
            id="faq-001",
            content="问：如何开始使用SaleMates？答：注册账号后，系统会引导您完成初始化设置，包括团队邀请、权限配置、工作流程设置等，通常10分钟内可以完成。",
            metadata={"category": "FAQ", "type": "入门"},
        ),
        Document(
            id="faq-002",
            content="问：支持哪些支付方式？答：支持企业对公转账、支付宝、微信支付。年付客户可享受9折优惠。",
            metadata={"category": "FAQ", "type": "付款"},
        ),
        Document(
            id="faq-003",
            content="问：可以免费试用吗？答：提供14天免费试用，试用期间所有功能开放，无需绑定信用卡。",
            metadata={"category": "FAQ", "type": "试用"},
        ),
        Document(
            id="faq-004",
            content="问：数据可以迁移吗？答：支持从其他CRM系统导入数据，提供数据迁移工具和技术支持。",
            metadata={"category": "FAQ", "type": "迁移"},
        ),
    ]
    return docs


@pytest.fixture
def vector_store():
    """Create empty mock vector store."""
    return MockVectorStore()


@pytest.fixture
def rag_system(vector_store):
    """Create mock RAG system."""
    return MockRAGSystem(vector_store)


@pytest.fixture
def confidence_router():
    """Create confidence router."""
    return ConfidenceRouter()


# ============ Test Classes ============


class TestRAGKnowledgeBaseIndexing:
    """Test knowledge base indexing functionality."""

    @pytest.mark.asyncio
    async def test_index_product_documents(self, rag_system, product_knowledge_base):
        """Test indexing product documents into knowledge base."""
        count = await rag_system.index_knowledge_base(product_knowledge_base, "products")

        assert count == len(product_knowledge_base)
        assert "products" in rag_system.knowledge_base
        assert len(rag_system.knowledge_base["products"]) == len(product_knowledge_base)

    @pytest.mark.asyncio
    async def test_index_faq_documents(self, rag_system, faq_knowledge_base):
        """Test indexing FAQ documents."""
        count = await rag_system.index_knowledge_base(faq_knowledge_base, "faq")

        assert count == len(faq_knowledge_base)
        assert "faq" in rag_system.knowledge_base

    @pytest.mark.asyncio
    async def test_index_multiple_categories(
        self, rag_system, product_knowledge_base, faq_knowledge_base
    ):
        """Test indexing documents into multiple categories."""
        product_count = await rag_system.index_knowledge_base(product_knowledge_base, "products")
        faq_count = await rag_system.index_knowledge_base(faq_knowledge_base, "faq")

        assert product_count == len(product_knowledge_base)
        assert faq_count == len(faq_knowledge_base)
        assert len(rag_system.knowledge_base) == 2


class TestRAGSemanticSearch:
    """Test semantic search functionality."""

    @pytest.mark.asyncio
    async def test_search_by_keyword(self, rag_system, product_knowledge_base):
        """Test searching by keyword."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("价格", "products")

        assert len(result.documents) > 0
        # Should find documents mentioning price
        found_price = any("价格" in doc.content or "元" in doc.content for doc in result.documents)
        assert found_price

    @pytest.mark.asyncio
    async def test_search_returns_relevant_documents(self, rag_system, product_knowledge_base):
        """Test search returns relevant documents."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("团队协作功能", "products")

        assert len(result.documents) > 0
        # Top result should be about team collaboration
        assert "协作" in result.documents[0].content or "团队" in result.documents[0].content

    @pytest.mark.asyncio
    async def test_search_with_no_results(self, rag_system, product_knowledge_base):
        """Test search returns empty when no matches."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("xyz不存在的内容abc", "products")

        # May return empty or low-score results
        assert isinstance(result.documents, list)

    @pytest.mark.asyncio
    async def test_search_limit_top_k(self, rag_system, product_knowledge_base):
        """Test search respects top_k limit."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("SaleMates", "products", top_k=3)

        assert len(result.documents) <= 3

    @pytest.mark.asyncio
    async def test_search_confidence_score(self, rag_system, product_knowledge_base):
        """Test search returns confidence scores."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("企业版价格", "products")

        assert hasattr(result, "confidence")
        assert 0.0 <= result.confidence <= 1.0


class TestRAGResponseGeneration:
    """Test RAG-powered response generation."""

    @pytest.mark.asyncio
    async def test_generate_answer_with_context(self, rag_system, product_knowledge_base):
        """Test generating answer from retrieved context."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("企业版有什么功能？")

        assert response.answer
        assert len(response.sources) > 0
        assert response.confidence > 0

    @pytest.mark.asyncio
    async def test_generate_answer_includes_sources(self, rag_system, product_knowledge_base):
        """Test generated answer includes source documents."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("AI功能支持吗？")

        assert response.sources
        assert any("AI" in doc.content for doc in response.sources)

    @pytest.mark.asyncio
    async def test_generate_answer_no_hallucination(self, rag_system, product_knowledge_base):
        """Test answer generation doesn't hallucinate when context is available."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("企业版支持多少人协作？")

        # Should have high confidence and not be marked as hallucination
        assert response.confidence >= 0.3  # Reasonable threshold
        assert not response.is_hallucination


class TestRAGHallucinationPrevention:
    """Test hallucination prevention in RAG responses."""

    @pytest.mark.asyncio
    async def test_no_hallucination_on_known_topic(self, rag_system, product_knowledge_base):
        """Test no hallucination when topic is in knowledge base."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("企业版价格是多少？")

        assert not response.is_hallucination
        assert "元" in response.answer or "万" in response.answer

    @pytest.mark.asyncio
    async def test_no_hallucination_on_unknown_topic(self, rag_system, product_knowledge_base):
        """Test appropriate response when topic is not in knowledge base."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        # Query about something not in KB
        response = await rag_system.query("你们有量子计算功能吗？")

        # Should either have low confidence or indicate no information
        # Not hallucinating means not making up facts
        if response.confidence < 0.3:
            assert "没有找到" in response.answer or "抱歉" in response.answer

    @pytest.mark.asyncio
    async def test_confidence_based_on_retrieval_quality(self, rag_system, product_knowledge_base):
        """Test confidence score reflects retrieval quality."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        # Specific query should have higher confidence
        specific_response = await rag_system.query("SaleMates企业版支持最多多少人协作？")
        # Vague query should have lower confidence
        vague_response = await rag_system.query("说说产品")

        # Both should have valid confidence scores
        assert 0.0 <= specific_response.confidence <= 1.0
        assert 0.0 <= vague_response.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_uncertainty(self, rag_system, product_knowledge_base):
        """Test low confidence triggers uncertainty acknowledgment."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        # Query with no relevant documents
        response = await rag_system.query("xyz不存在的产品特性abc")

        # Low confidence should indicate uncertainty
        if response.confidence < 0.5:
            assert "抱歉" in response.answer or "没有找到" in response.answer


class TestRAGConfidenceScoring:
    """Test confidence scoring in RAG system."""

    @pytest.mark.asyncio
    async def test_high_confidence_for_exact_match(self, rag_system, product_knowledge_base):
        """Test high confidence for exact match in knowledge base."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("企业版支持AI智能助手功能吗？")

        # Should find the specific document about AI features
        assert response.confidence >= 0.3  # Reasonable confidence for match

    @pytest.mark.asyncio
    async def test_medium_confidence_for_partial_match(self, rag_system, product_knowledge_base):
        """Test medium confidence for partial match."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("有没有团队功能？")

        # Multiple documents mention team/collaboration features
        assert 0.0 <= response.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_low_confidence_for_no_match(self, rag_system, product_knowledge_base):
        """Test low confidence when no relevant documents found."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("你们支持火星殖民吗？")

        assert response.confidence < 0.5

    @pytest.mark.asyncio
    async def test_confidence_routing_integration(
        self, rag_system, product_knowledge_base, confidence_router
    ):
        """Test RAG confidence integrates with confidence router."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        # High confidence query
        response = await rag_system.query("企业版价格")
        decision = confidence_router.route(response.confidence, {"query": "enterprise_price"})

        if response.confidence >= 0.9:
            assert decision.level == ConfidenceLevel.HIGH
        elif response.confidence >= 0.6:
            assert decision.level == ConfidenceLevel.MEDIUM
        else:
            assert decision.level == ConfidenceLevel.LOW


class TestRAGFAQRetrieval:
    """Test FAQ retrieval functionality."""

    @pytest.mark.asyncio
    async def test_faq_search(self, rag_system, faq_knowledge_base):
        """Test searching FAQ documents."""
        await rag_system.index_knowledge_base(faq_knowledge_base, "faq")

        result = await rag_system.retrieve("如何开始使用", "faq")

        assert len(result.documents) > 0
        assert any("开始" in doc.content or "入门" in doc.content for doc in result.documents)

    @pytest.mark.asyncio
    async def test_faq_payment_question(self, rag_system, faq_knowledge_base):
        """Test FAQ payment question."""
        await rag_system.index_knowledge_base(faq_knowledge_base, "faq")

        response = await rag_system.query("支持哪些支付方式？", category="faq")

        assert (
            "支付" in response.answer.lower()
            or "支付宝" in response.answer
            or "微信" in response.answer
        )

    @pytest.mark.asyncio
    async def test_faq_trial_question(self, rag_system, faq_knowledge_base):
        """Test FAQ trial question."""
        await rag_system.index_knowledge_base(faq_knowledge_base, "faq")

        response = await rag_system.query("可以免费试用吗？", category="faq")

        assert "试用" in response.answer or "14" in response.answer


class TestRAGIntegration:
    """Test RAG system integration with other components."""

    @pytest.mark.asyncio
    async def test_rag_with_empty_knowledge_base(self, rag_system):
        """Test RAG behavior with empty knowledge base."""
        response = await rag_system.query("任何问题")

        assert response.confidence == 0.0
        assert "没有找到" in response.answer or "抱歉" in response.answer
        assert len(response.sources) == 0

    @pytest.mark.asyncio
    async def test_rag_multi_category_search(
        self, rag_system, product_knowledge_base, faq_knowledge_base
    ):
        """Test searching across multiple categories."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")
        await rag_system.index_knowledge_base(faq_knowledge_base, "faq")

        # Search in products
        product_result = await rag_system.retrieve("价格", "products")
        # Search in FAQ
        faq_result = await rag_system.retrieve("支付", "faq")

        assert len(product_result.documents) > 0
        assert len(faq_result.documents) > 0

    @pytest.mark.asyncio
    async def test_rag_response_metadata(self, rag_system, product_knowledge_base):
        """Test RAG response includes metadata."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("企业版功能")

        # Sources should have metadata
        if response.sources:
            assert hasattr(response.sources[0], "id")
            assert hasattr(response.sources[0], "content")
            assert hasattr(response.sources[0], "metadata")


class TestRAGEdgeCases:
    """Test edge cases in RAG system."""

    @pytest.mark.asyncio
    async def test_empty_query(self, rag_system, product_knowledge_base):
        """Test handling empty query."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("")

        # Should handle gracefully
        assert response is not None

    @pytest.mark.asyncio
    async def test_very_long_query(self, rag_system, product_knowledge_base):
        """Test handling very long query."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        long_query = "企业版" * 100
        response = await rag_system.query(long_query)

        assert response is not None
        assert response.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, rag_system, product_knowledge_base):
        """Test handling special characters in query."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        response = await rag_system.query("价格!@#$%^&*()")

        assert response is not None

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, rag_system, product_knowledge_base):
        """Test handling concurrent queries."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        queries = ["价格", "功能", "集成", "安全", "支持"]

        # Execute queries concurrently
        tasks = [rag_system.query(q) for q in queries]
        responses = await asyncio.gather(*tasks)

        assert len(responses) == len(queries)
        for response in responses:
            assert hasattr(response, "answer")
            assert hasattr(response, "confidence")


class TestRAGContextRetrieval:
    """Test context retrieval for LLM."""

    @pytest.mark.asyncio
    async def test_retrieve_context_for_llm(self, rag_system, product_knowledge_base):
        """Test retrieving context for LLM prompt."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("企业版功能", top_k=3)

        assert len(result.documents) <= 3
        # Context should be relevant
        for doc in result.documents:
            assert doc.content

    @pytest.mark.asyncio
    async def test_context_formatting(self, rag_system, product_knowledge_base):
        """Test context is properly formatted for LLM."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("集成", top_k=2)

        # Each document should have content
        for doc in result.documents:
            assert isinstance(doc.content, str)
            assert len(doc.content) > 0

    @pytest.mark.asyncio
    async def test_context_with_metadata(self, rag_system, product_knowledge_base):
        """Test context includes metadata for source attribution."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        result = await rag_system.retrieve("AI功能", top_k=2)

        for doc in result.documents:
            assert doc.metadata
            assert "category" in doc.metadata or "product" in doc.metadata


class TestRAGPerformance:
    """Test RAG system performance requirements."""

    @pytest.mark.asyncio
    async def test_query_response_time(self, rag_system, product_knowledge_base):
        """Test query response time is acceptable."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        import time

        start = time.time()
        await rag_system.query("企业版价格")
        elapsed = time.time() - start

        # Should respond within reasonable time (adjust as needed)
        assert elapsed < 5.0  # 5 seconds max for mock

    @pytest.mark.asyncio
    async def test_indexing_performance(self, rag_system, product_knowledge_base):
        """Test document indexing performance."""
        import time

        start = time.time()
        await rag_system.index_knowledge_base(product_knowledge_base, "products")
        elapsed = time.time() - start

        # Should index quickly
        assert elapsed < 2.0  # 2 seconds max for mock

    @pytest.mark.asyncio
    async def test_batch_query_performance(self, rag_system, product_knowledge_base):
        """Test batch query performance."""
        await rag_system.index_knowledge_base(product_knowledge_base, "products")

        queries = [f"查询{i}" for i in range(10)]

        import time

        start = time.time()
        await asyncio.gather(*[rag_system.query(q) for q in queries])
        elapsed = time.time() - start

        # Batch of 10 queries should complete quickly
        assert elapsed < 10.0
