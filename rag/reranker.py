"""Result reranking using LLM for relevance scoring.

Filters out irrelevant results by having the LLM score relevance to the query.
"""

import asyncio
import json
from llm.ollama import chat_completion


async def rerank_results(query: str, results: list[dict], top_k: int = 3) -> list[dict]:
    """Rerank search results by relevance to the original query.

    The LLM scores each result on relevance (0-10), filtering out false positives.

    Args:
        query: Original user query
        results: List of search results (min 3, ideally 5-10)
        top_k: Number of top results to return after reranking

    Returns:
        Top K results reranked by LLM relevance score
    """
    if len(results) <= top_k:
        # Not enough results to rerank
        return results

    system_prompt = """You are a relevance evaluator. Given a user query and candidate documents, score each document's relevance to answering the query.

Score from 0-10:
- 10: Directly answers the query
- 8-9: Highly relevant, contains key information
- 6-7: Somewhat relevant, tangentially related
- 3-5: Barely relevant, wrong context
- 0-2: Not relevant

Return JSON array with scores, one object per document."""

    # Format results for reranking
    document_text = "\n\n".join(
        [f"[Document {i}]\nFile: {r['file_path']}\nContent: {r['chunk_text'][:500]}..." for i, r in enumerate(results)]
    )

    user_message = f"""Query: {query}

Documents:
{document_text}

Return JSON array like: [{{"document_index": 0, "score": 8, "reason": "..."}}, ...]"""

    try:
        response = await chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            enable_tools=False,
            temperature=0.3,  # Low temperature for consistency
        )

        # Extract JSON from response
        import re

        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if not json_match:
            # Fallback: return original results
            return results[:top_k]

        scores = json.loads(json_match.group())

        # Apply scores to results
        scored_results = []
        for score_obj in scores:
            idx = score_obj.get("document_index", 0)
            if idx < len(results):
                results[idx]["relevance_score"] = score_obj.get("score", 5)
                scored_results.append((results[idx], score_obj.get("score", 5)))

        # Sort by score (descending) and return top K
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in scored_results[:top_k]]

    except Exception as e:
        print(f"Reranking failed: {e}")
        # Fallback: return original results
        return results[:top_k]


async def rerank_with_threshold(query: str, results: list[dict], threshold: float = 5.0) -> list[dict]:
    """Rerank results and filter by relevance threshold.

    Removes results that score below threshold (e.g., wrong "Jonathan" person).

    Args:
        query: Original user query
        results: Search results to rerank
        threshold: Minimum relevance score to include (0-10 scale)

    Returns:
        Results above threshold, sorted by score
    """
    if len(results) == 0:
        return []

    reranked = await rerank_results(query, results, top_k=len(results))

    # Filter by threshold
    filtered = [r for r in reranked if r.get("relevance_score", 5) >= threshold]

    return filtered if filtered else reranked[:1]  # Return at least one
