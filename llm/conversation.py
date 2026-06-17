"""Conversation history tracking for multi-turn interactions.

Stores conversation threads to enable follow-up questions with context.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

# In-memory conversation store (TODO: persist to DB for production)
_conversations = {}
_conversation_ttl = timedelta(hours=1)  # Clear old conversations after 1 hour


def create_conversation() -> str:
    """Create a new conversation thread.

    Returns:
        Conversation ID (UUID)
    """
    conv_id = str(uuid.uuid4())
    _conversations[conv_id] = {
        "id": conv_id,
        "created_at": datetime.now(),
        "messages": [],
    }
    return conv_id


def add_message(
    conversation_id: str,
    role: str,  # "user", "assistant"
    content: str,
    metadata: dict | None = None,
) -> None:
    """Add message to conversation history.

    Args:
        conversation_id: Which conversation thread
        role: "user" or "assistant"
        content: Message text
        metadata: Optional metadata (sources, etc.)
    """
    if conversation_id not in _conversations:
        _conversations[conversation_id] = {
            "id": conversation_id,
            "created_at": datetime.now(),
            "messages": [],
        }

    _conversations[conversation_id]["messages"].append(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
    )


def get_conversation_history(conversation_id: str, limit: int = 5) -> list[dict]:
    """Retrieve conversation history.

    Args:
        conversation_id: Which conversation thread
        limit: Max messages to return (most recent)

    Returns:
        List of messages (oldest first)
    """
    if conversation_id not in _conversations:
        return []

    messages = _conversations[conversation_id]["messages"]

    # Return most recent N messages
    return messages[-limit:] if limit > 0 else messages


def get_last_message(conversation_id: str) -> dict | None:
    """Get the last message in a conversation.

    Useful for follow-ups to understand previous context.
    """
    history = get_conversation_history(conversation_id, limit=1)
    return history[0] if history else None


def get_conversation_context(conversation_id: str) -> str:
    """Get formatted context from conversation history for LLM.

    Includes previous messages with sources/metadata.
    """
    history = get_conversation_history(conversation_id, limit=10)

    if not history:
        return ""

    context_lines = ["Previous conversation context:"]
    for msg in history:
        role = "You" if msg["role"] == "user" else "Assistant"
        context_lines.append(f"\n{role}: {msg['content']}")

        # Add sources if available
        if msg["metadata"].get("sources"):
            sources = msg["metadata"]["sources"]
            context_lines.append(f"  Sources: {', '.join(sources[:3])}")

    return "\n".join(context_lines)


def cleanup_old_conversations() -> int:
    """Remove conversations older than TTL.

    Returns:
        Number of conversations deleted
    """
    now = datetime.now()
    to_delete = []

    for conv_id, conv in _conversations.items():
        if now - conv["created_at"] > _conversation_ttl:
            to_delete.append(conv_id)

    for conv_id in to_delete:
        del _conversations[conv_id]

    return len(to_delete)


def clear_conversation(conversation_id: str) -> None:
    """Clear conversation history."""
    if conversation_id in _conversations:
        del _conversations[conversation_id]
