"""Query expansion using LLM to generate related search queries.

Improves recall by searching for semantically related queries.
"""

import asyncio
from llm.ollama import chat_completion


async def expand_query(query: str, max_variations: int = 2) -> list[str]:
    """Generate related queries for a single user query.

    Args:
        query: Original user query
        max_variations: Number of related queries to generate (2-3 recommended)

    Returns:
        List including original + generated queries
    """
    if len(query.strip()) < 10:
        # Very short queries probably don't need expansion
        return [query]

    system_prompt = """You are a search query optimizer. Given a user's question, generate 1-2 alternative queries that would retrieve the same or related information.

Focus on:
- Synonym variations (e.g., "meeting" -> "conversation", "discussed with")
- Related concepts (e.g., "project status" -> "timeline", "progress")
- Different phrasings of the same question

Return ONLY the alternative queries, one per line, without numbering or explanation."""

    try:
        response = await chat_completion(
            system_prompt=system_prompt,
            user_message=f"Original query: {query}\n\nGenerate {max_variations} alternative queries:",
            enable_tools=False,  # Don't need tools for this
            temperature=0.5,  # Lower temperature for consistency
        )

        # Parse response - should be lines of queries
        alternative_queries = [q.strip() for q in response.strip().split("\n") if q.strip() and len(q.strip()) > 5]

        # Return original + generated (limit to max_variations)
        return [query] + alternative_queries[:max_variations]

    except Exception as e:
        # If expansion fails, just return original
        print(f"Query expansion failed: {e}")
        return [query]


async def expand_and_search(query: str, search_fn, top_k: int = 5, max_variations: int = 2) -> list[dict]:
    """Expand query and search for all variations, merge results.

    Args:
        query: Original user query
        search_fn: Async function(embedding) -> list[dict] that searches the index
        top_k: Top K results to return from merged searches
        max_variations: Number of query variations (2-3 recommended)

    Returns:
        Merged and deduplicated top-K results from all queries
    """
    from rag.retriever import retrieve
    from indexer.embedder import embed_text

    # Expand the query
    queries = await expand_query(query, max_variations=max_variations)

    # Search with all query variations
    all_results = {}  # Use dict to deduplicate by file_path + chunk_text

    for expanded_query in queries:
        try:
            results = await retrieve(expanded_query, top_k=top_k)
            for result in results:
                # Use path + text as unique key to avoid duplicates
                key = (result["file_path"], result["chunk_text"][:50])
                if key not in all_results:
                    all_results[key] = result
        except Exception as e:
            print(f"Search failed for '{expanded_query}': {e}")

    # Return top K from merged results
    merged = list(all_results.values())
    return merged[:top_k]
