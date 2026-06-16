import httpx
from config import Config


async def embed_text(text: str) -> list[float]:
    """Call Ollama embeddings API and return vector."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{Config.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": Config.OLLAMA_EMBED_MODEL, "prompt": text},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]
