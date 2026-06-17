"""Keyword-based search for exact phrase matching and complementing vector search.

Useful for queries with specific dates, names, or technical terms.
"""

import re
from pathlib import Path
from typing import cast

from config import Config


async def keyword_search(query: str, top_k: int = 5) -> list[dict]:
    """Search vault files for keyword matches.

    Returns results sorted by frequency of query terms in the file.

    Args:
        query: Search query
        top_k: Number of top results to return

    Returns:
        List of results: {file_path, title, chunk_text, score}
    """
    if not Config.VAULT_PATH.exists():
        return []

    # Extract keywords (ignore common words)
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "is",
        "are",
        "was",
        "were",
        "been",
        "be",
        "have",
        "has",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "my",
        "your",
        "his",
        "her",
    }

    keywords = [w.lower() for w in re.findall(r"\b\w+\b", query) if w.lower() not in stop_words and len(w) > 2]

    if not keywords:
        return []

    # Search markdown files in vault
    results = {}

    for md_file in Config.VAULT_PATH.rglob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Count keyword matches
            score = 0
            for keyword in keywords:
                # Case-insensitive match, count occurrences
                pattern = rf"\b{re.escape(keyword)}\b"
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                score += matches * 2  # Weight each keyword match

                # Extra points for exact phrases
                if keyword in query.lower():
                    score += len(re.findall(keyword, content, re.IGNORECASE)) * 5

            if score > 0:
                # Extract snippet around first keyword match
                for keyword in keywords:
                    pattern = rf".{{0,100}}\b{re.escape(keyword)}\b.{{0,100}}"
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        snippet = match.group().strip()
                        break
                else:
                    snippet = content[:200]

                relative_path = str(md_file.relative_to(Config.VAULT_PATH))
                results[relative_path] = {
                    "file_path": relative_path,
                    "title": md_file.stem,
                    "chunk_text": snippet,
                    "score": score,
                    "search_type": "keyword",
                }
        except Exception:
            pass

    # Sort by score and return top K
    sorted_results = sorted(results.values(), key=lambda x: x["score"], reverse=True)  # type: ignore
    return sorted_results[:top_k]


async def hybrid_search(
    query: str, vector_results: list[dict], top_k: int = 5, keyword_weight: float = 0.3
) -> list[dict]:
    """Combine vector search and keyword search results.

    Args:
        query: Original query
        vector_results: Results from vector similarity search
        top_k: Number of results to return
        keyword_weight: Weight for keyword results (0.0-1.0)

    Returns:
        Merged results with emphasis on vector similarity but including keyword matches
    """
    # Get keyword results
    keyword_results = await keyword_search(query, top_k=top_k)

    if not keyword_results:
        return vector_results[:top_k]

    # Merge results - prioritize vector but include unique keyword hits
    merged = {}

    # Add vector results first (higher priority)
    for i, result in enumerate(vector_results):
        key = (result["file_path"], result["chunk_text"][:30])
        merged[key] = {**result, "_source": "vector", "_rank": i}

    # Add keyword results that don't overlap with vector results
    unique_keyword_count = 0
    for i, result in enumerate(keyword_results):
        key = (result["file_path"], result["chunk_text"][:30])
        if key not in merged and unique_keyword_count < int(top_k * keyword_weight):
            merged[key] = {**result, "_source": "keyword", "_rank": i}
            unique_keyword_count += 1

    # Sort: vector results first, then keyword
    def sort_key(item: dict) -> tuple[bool, int]:  # type: ignore
        return (item["_source"] != "vector", int(item["_rank"]))

    sorted_results = sorted(merged.values(), key=sort_key)  # type: ignore

    # Remove internal tracking fields
    for r in sorted_results:
        r.pop("_source", None)
        r.pop("_rank", None)

    return sorted_results[:top_k]
