import httpx
from config import Config
from llm.tool_handler import format_tools_for_prompt, handle_tool_call
from mcp_server import get_tools

# Persistent client with connection pooling
_ollama_client: httpx.AsyncClient | None = None


async def get_ollama_client() -> httpx.AsyncClient:
    """Get or create persistent Ollama client with connection pooling."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = httpx.AsyncClient(timeout=30.0)
    return _ollama_client


async def close_ollama_client() -> None:
    """Close persistent Ollama client."""
    global _ollama_client
    if _ollama_client is not None:
        await _ollama_client.aclose()
        _ollama_client = None
    return


async def chat_completion(
    system_prompt: str,
    user_message: str,
    context_chunks: list[dict] | None = None,
    retry_count: int = 2,
    temperature: float = 0.7,
    enable_tools: bool = True,
) -> str:
    """Call Ollama chat completion with automatic retry, error recovery, and tool support.

    Args:
        system_prompt: System instruction for the LLM
        user_message: User's message/query
        context_chunks: Optional context chunks from RAG retrieval
        retry_count: Number of retries on failure (default 2)
        temperature: LLM temperature for diversity (lower = more focused)
        enable_tools: Enable tool use in LLM (default True)

    Returns:
        Assistant response text

    Raises:
        Exception: If all retries are exhausted
    """
    if context_chunks is None:
        context_chunks = []

    # Build context section
    context_section = ""
    if context_chunks:
        context_lines = []
        for chunk in context_chunks:
            context_lines.append(f"---\n{chunk['chunk_text']}\n---")
        context_section = "Context:\n\n" + "\n\n".join(context_lines) + "\n\n"

    # Add tools information to system prompt
    enhanced_system_prompt = system_prompt
    if enable_tools:
        tools = get_tools()
        tools_info = format_tools_for_prompt(tools)
        enhanced_system_prompt = system_prompt + "\n" + tools_info

    # Build final message
    full_message = f"{context_section}Question: {user_message}"

    messages = [
        {"role": "system", "content": enhanced_system_prompt},
        {"role": "user", "content": full_message},
    ]

    client = await get_ollama_client()
    last_error: Exception | None = None

    for attempt in range(retry_count):
        try:
            response = await client.post(
                f"{Config.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": Config.OLLAMA_CHAT_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            response.raise_for_status()
            data = response.json()
            response_text = data["message"]["content"]

            # Handle tool calls if enabled
            if enable_tools:
                response_text, tool_info = handle_tool_call(response_text)
                # If a tool was called, append assistant message and loop for follow-up
                if tool_info and "error" not in tool_info:
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append(
                        {"role": "user", "content": "Please use the tool result to provide your final answer."}
                    )
                    # Get final response with tool results
                    follow_up = await client.post(
                        f"{Config.OLLAMA_BASE_URL}/api/chat",
                        json={
                            "model": Config.OLLAMA_CHAT_MODEL,
                            "messages": messages,
                            "stream": False,
                            "options": {"temperature": temperature},
                        },
                    )
                    follow_up.raise_for_status()
                    follow_up_data = follow_up.json()
                    response_text = follow_up_data["message"]["content"]

            return response_text

        except httpx.TimeoutException as e:
            last_error = e
            if attempt < retry_count - 1:
                # On timeout, reduce temperature and retry for more focused response
                temperature = max(0.1, temperature - 0.2)
                continue
            raise

        except Exception as e:
            last_error = e
            if attempt < retry_count - 1:
                continue
            raise

    # Should not reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in chat_completion retry loop")
