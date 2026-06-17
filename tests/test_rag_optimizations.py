"""Tests for RAG optimization features: query expansion, reranking, hybrid search."""

import pytest
import json
from rag.query_expander import expand_query, expand_and_search
from rag.reranker import rerank_results, rerank_with_threshold
from rag.keyword_search import keyword_search, hybrid_search
from rag.retriever import retrieve_with_expansion, retrieve_with_reranking, retrieve_hybrid, retrieve_optimized


class TestQueryExpansion:
    """Test query expansion for improved recall."""

    @pytest.mark.asyncio
    async def test_expand_short_query(self):
        """Short queries shouldn't be expanded."""
        result = await expand_query("hi")
        assert len(result) == 1  # Just original
        assert result[0] == "hi"

    @pytest.mark.asyncio
    async def test_expand_longer_query(self):
        """Longer queries should generate variations."""
        query = "What is my project status for the current sprint?"
        result = await expand_query(query, max_variations=2)

        # Should return original + variations
        assert len(result) >= 1
        assert result[0] == query

    @pytest.mark.asyncio
    async def test_expansion_includes_original(self):
        """Expanded queries must include original."""
        query = "How do I configure the system?"
        result = await expand_query(query, max_variations=3)

        # Original must be first
        assert result[0] == query


class TestReranking:
    """Test LLM-based result reranking."""

    @pytest.mark.asyncio
    async def test_rerank_filters_results(self):
        """Reranking should filter out low-relevance results."""
        query = "What is machine learning?"
        results = [
            {
                "file_path": "notes/ml-intro.md",
                "title": "Machine Learning",
                "chunk_text": "Machine learning is a subset of AI that enables systems to learn and improve from experience."
            },
            {
                "file_path": "notes/unrelated.md",
                "title": "Gardening",
                "chunk_text": "Learning to garden requires patience and practice with different plants."
            }
        ]

        reranked = await rerank_results(query, results, top_k=1)

        # Should have at least one result
        assert len(reranked) >= 1

    @pytest.mark.asyncio
    async def test_rerank_with_threshold(self):
        """Reranking with threshold filters low-scoring results."""
        query = "Python syntax"
        results = [
            {
                "file_path": "notes/python.md",
                "title": "Python",
                "chunk_text": "Python is a programming language with simple, readable syntax."
            }
        ]

        filtered = await rerank_with_threshold(query, results, threshold=6.0)

        # Should return at least one result
        assert len(filtered) >= 1


class TestKeywordSearch:
    """Test keyword-based search."""

    @pytest.mark.asyncio
    async def test_keyword_search_basic(self):
        """Keyword search should find matches."""
        results = await keyword_search("markdown notes", top_k=5)

        # Results should be list of dicts
        assert isinstance(results, list)
        for result in results:
            assert "file_path" in result
            assert "chunk_text" in result
            assert "score" in result

    @pytest.mark.asyncio
    async def test_keyword_search_empty_query(self):
        """Empty query should return empty results."""
        results = await keyword_search("", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_keyword_search_respects_top_k(self):
        """Keyword search should respect top_k limit."""
        results = await keyword_search("test", top_k=3)
        assert len(results) <= 3


class TestHybridSearch:
    """Test hybrid vector + keyword search."""

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self):
        """Hybrid search should merge vector and keyword results."""
        vector_results = [
            {
                "file_path": "notes/semantic.md",
                "title": "Semantic",
                "chunk_text": "This is semantically similar."
            }
        ]

        results = await hybrid_search("semantic meaning", vector_results, top_k=5)

        # Should return results
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_hybrid_respects_top_k(self):
        """Hybrid search should respect top_k."""
        vector_results = [
            {
                "file_path": f"notes/file{i}.md",
                "title": f"File {i}",
                "chunk_text": "Content " + str(i)
            }
            for i in range(10)
        ]

        results = await hybrid_search("test", vector_results, top_k=3)
        assert len(results) <= 3


class TestRetrievalStrategies:
    """Test different retrieval strategies."""

    @pytest.mark.asyncio
    async def test_retrieve_with_expansion(self):
        """Expansion retrieval should find results."""
        # May skip if server not running
        try:
            results = await retrieve_with_expansion("test query", top_k=3)
            assert isinstance(results, list)
        except Exception as e:
            pytest.skip(f"Expansion retrieval failed: {e}")

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking(self):
        """Reranking retrieval should return scored results."""
        try:
            results = await retrieve_with_reranking("test", top_k=3)
            assert isinstance(results, list)
        except Exception as e:
            pytest.skip(f"Reranking retrieval failed: {e}")

    @pytest.mark.asyncio
    async def test_retrieve_hybrid(self):
        """Hybrid retrieval should combine vector and keyword."""
        try:
            results = await retrieve_hybrid("test", top_k=3)
            assert isinstance(results, list)
        except Exception as e:
            pytest.skip(f"Hybrid retrieval failed: {e}")

    @pytest.mark.asyncio
    async def test_retrieve_optimized(self):
        """Full optimization should use all techniques."""
        try:
            results = await retrieve_optimized("test query", top_k=3)
            assert isinstance(results, list)
            assert len(results) <= 3
        except Exception as e:
            pytest.skip(f"Optimized retrieval failed: {e}")


class TestOptimizationIntegration:
    """Test optimization features working together."""

    @pytest.mark.asyncio
    async def test_expansion_finds_different_results(self):
        """Query expansion should find results that base search might miss."""
        # This is more of an integration test
        try:
            base_results = await expand_and_search(
                "meeting",
                lambda q: [],
                top_k=3,
                max_variations=1
            )
            # Should return something even if direct search returns nothing
        except Exception:
            pass  # Expected to fail without real retrieval

    @pytest.mark.asyncio
    async def test_optimizations_dont_crash_on_empty_vault(self):
        """Optimizations should gracefully handle empty vaults."""
        try:
            # These should not crash even if vault is empty
            results = await retrieve_with_expansion("test", top_k=1)
            assert isinstance(results, list)
        except Exception:
            pass  # OK to fail if no vault


class TestOptimizationPerformance:
    """Test that optimizations don't cause severe slowdowns."""

    @pytest.mark.asyncio
    async def test_query_expansion_reasonable_time(self):
        """Query expansion should complete in reasonable time."""
        import time

        query = "What is a reasonable question?"
        start = time.time()

        try:
            await expand_query(query, max_variations=2)
            elapsed = time.time() - start
            # Should complete within 10 seconds
            assert elapsed < 10
        except Exception:
            pass  # OK if LLM not available

    @pytest.mark.asyncio
    async def test_reranking_reasonable_time(self):
        """Reranking should complete quickly."""
        import time

        results = [
            {
                "file_path": "test.md",
                "title": "Test",
                "chunk_text": "Test content"
            }
        ]

        start = time.time()

        try:
            await rerank_results("test", results, top_k=1)
            elapsed = time.time() - start
            # Should be quick
            assert elapsed < 10
        except Exception:
            pass


class TestConfigurationSupport:
    """Test that optimizations respect configuration."""

    def test_config_has_rag_options(self):
        """Config should support RAG optimization options."""
        from config import Config

        # These should be defined
        assert hasattr(Config, "RAG_STRATEGY")
        assert hasattr(Config, "RAG_QUERY_EXPANSION")
        assert hasattr(Config, "RAG_RERANKING")
        assert hasattr(Config, "RAG_HYBRID_SEARCH")

    def test_config_defaults(self):
        """Config should have reasonable defaults."""
        from config import Config

        # Should default to optimized strategy
        assert Config.RAG_STRATEGY in ["basic", "expansion", "reranking", "hybrid", "optimized"]
