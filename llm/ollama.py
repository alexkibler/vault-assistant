import httpx
from config import Config


async def chat_completion(
    system_prompt: str,
    user_message: str,
    context_chunks: list[dict] | None = None,
) -> str:
    """Call Ollama chat completion. Return assistant response."""
    if context_chunks is None:
        context_chunks = []

    # Build context section
    context_section = ""
    if context_chunks:
        context_lines = []
        for chunk in context_chunks:
            context_lines.append(f"---\n{chunk['chunk_text']}\n---")
        context_section = "Context:\n\n" + "\n\n".join(context_lines) + "\n\n"

    # Build final message
    full_message = f"{context_section}Question: {user_message}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_message},
    ]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.OLLAMA_BASE_URL}/api/chat",
                json={"model": Config.OLLAMA_CHAT_MODEL, "messages": messages, "stream": False},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
    except httpx.TimeoutException:
        # Retry once on timeout
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.OLLAMA_BASE_URL}/api/chat",
                json={"model": Config.OLLAMA_CHAT_MODEL, "messages": messages, "stream": False},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
