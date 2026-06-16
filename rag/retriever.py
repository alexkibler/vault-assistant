from indexer.embedder import embed_text
from indexer.store import search_chunks


async def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve similar chunks from vault for a query."""
    embedding = await embed_text(query)
    results = await search_chunks(embedding, top_k)
    return results
