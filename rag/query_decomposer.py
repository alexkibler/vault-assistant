"""Query decomposition for compound questions.

Splits "who did I meet and what did we discuss?" into:
1. "Who did I meet today?"
2. "What did we discuss?"

Then retrieves for each and synthesizes results.
"""

import re
from llm.ollama import chat_completion


def _is_compound_question(query: str) -> bool:
    """Detect if query has multiple parts (who AND what, etc)."""
    compound_patterns = [
        r"\s+and\s+",  # "who and what"
        r"\s+then\s+",  # "first do this then"
        r",\s*and\s",  # "X, and Y"
        r"\?.*\?",  # "question? question?"
    ]
    return len(query) > 20 and any(re.search(p, query.lower()) for p in compound_patterns)


async def decompose_query(query: str) -> list[str]:
    """Break compound question into sub-questions.

    Args:
        query: Original compound query

    Returns:
        List of individual questions (min 1, usually 1-3)
    """
    # Simple heuristics for common patterns
    if " and " in query.lower() and len(query) > 40:
        # Likely compound question
        system_prompt = """You are a question decomposer. Break complex questions into simpler sub-questions.

Goal: Split "who did I meet AND what did we talk about" into:
1. "Who did I meet today?"
2. "What did we discuss?"

Rules:
- Each sub-question should be answerable with vault search
- Keep original context (dates, people, etc.)
- Maximum 3 sub-questions
- Return ONLY the questions, one per line"""

        try:
            response = await chat_completion(
                system_prompt=system_prompt,
                user_message=f"Break this into sub-questions:\n{query}",
                enable_tools=False,
                temperature=0.3,
            )

            # Parse response
            sub_questions = [
                q.strip().rstrip("?") + "?"
                for q in response.strip().split("\n")
                if q.strip() and len(q.strip()) > 5 and "?" in q
            ]

            if sub_questions:
                return sub_questions
        except Exception as e:
            print(f"Query decomposition failed: {e}")

    # Fallback: return original
    return [query]


async def retrieve_with_decomposition(
    query: str, retrieve_fn, top_k: int = 5
) -> dict:
    """Retrieve for compound question by decomposing then merging.

    Args:
        query: Original query (may be compound)
        retrieve_fn: Async function(query_str) -> list[dict] for single query
        top_k: Top K results to return

    Returns:
        {
            "sub_questions": [...],
            "results": [...],
            "synthesis_context": "...",
        }
    """
    sub_questions = await decompose_query(query)

    if len(sub_questions) <= 1:
        # Not compound, just retrieve normally
        results = await retrieve_fn(query, top_k=top_k)
        return {
            "sub_questions": [query],
            "results": results,
            "synthesis_context": "Single question search",
        }

    # Retrieve for each sub-question
    all_results = {}

    for sub_q in sub_questions:
        try:
            results = await retrieve_fn(sub_q, top_k=top_k)
            for result in results:
                key = (result["file_path"], result["chunk_text"][:50])
                if key not in all_results:
                    all_results[key] = result
        except Exception as e:
            print(f"Retrieval failed for '{sub_q}': {e}")

    merged_results = list(all_results.values())[:top_k * 2]

    return {
        "sub_questions": sub_questions,
        "results": merged_results,
        "synthesis_context": f"Compound question decomposed into {len(sub_questions)} parts: {', '.join(sub_questions)}",
    }
