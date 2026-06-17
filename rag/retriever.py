from indexer.embedder import embed_text
from indexer.store import search_chunks


async def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve similar chunks from vault for a query."""
    embedding = await embed_text(query)
    results = await search_chunks(embedding, top_k)
    return results


async def retrieve_with_expansion(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve using query expansion for better recall.

    Generates 2 alternative queries and merges results.
    """
    from rag.query_expander import expand_and_search

    return await expand_and_search(query, retrieve, top_k=top_k, max_variations=2)


async def retrieve_with_reranking(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve and rerank by LLM relevance to query.

    Filters out false positives and sorts by actual relevance.
    """
    from rag.reranker import rerank_results

    # Get more results initially to allow reranking to filter
    results = await retrieve(query, top_k=max(top_k * 2, 10))

    if len(results) <= top_k:
        return results

    return await rerank_results(query, results, top_k=top_k)


async def retrieve_hybrid(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve using hybrid keyword + vector search.

    Combines exact keyword matches with semantic similarity.
    """
    from rag.keyword_search import hybrid_search

    # Vector search
    embedding = await embed_text(query)
    vector_results = await search_chunks(embedding, top_k=top_k)

    # Merge with keyword search
    return await hybrid_search(query, vector_results, top_k=top_k, keyword_weight=0.2)


async def retrieve_optimized(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve using all optimizations: expansion + hybrid + reranking.

    Best results but slowest (3+ LLM calls).
    """
    from rag.query_expander import expand_and_search
    from rag.reranker import rerank_results
    from rag.keyword_search import hybrid_search

    # 1. Expand query and search with variations
    expanded_results = await expand_and_search(query, retrieve, top_k=top_k * 2)

    # 2. Hybrid search for unique keyword matches
    embedding = await embed_text(query)
    vector_results = await search_chunks(embedding, top_k=top_k * 2)
    hybrid_results = await hybrid_search(query, vector_results, top_k=top_k * 2)

    # 3. Merge and deduplicate
    merged = {}
    for r in expanded_results + hybrid_results:
        key = (r["file_path"], r["chunk_text"][:50])
        merged[key] = r

    results = list(merged.values())[:top_k * 2]

    # 4. Rerank by relevance
    if len(results) > top_k:
        return await rerank_results(query, results, top_k=top_k)

    return results[:top_k]
