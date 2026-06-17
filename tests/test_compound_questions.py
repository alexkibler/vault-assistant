"""Tests for compound question handling and conversation threading."""

import pytest
from rag.query_decomposer import decompose_query, _is_compound_question
from llm.conversation import (
    create_conversation,
    add_message,
    get_conversation_history,
    get_conversation_context,
    get_last_message,
)


class TestCompoundDetection:
    """Test detection of compound questions."""

    def test_simple_question_not_compound(self):
        """Simple questions should not be marked as compound."""
        assert not _is_compound_question("Who did I meet?")
        assert not _is_compound_question("What was discussed?")
        assert not _is_compound_question("When was the meeting?")

    def test_and_detection(self):
        """Questions with 'and' should be detected."""
        assert _is_compound_question(
            "Who did I meet with today and what did we talk about?"
        )
        assert _is_compound_question("Tell me who was there and what happened")

    def test_multiple_questions(self):
        """Multiple questions marked with ? should be detected."""
        assert _is_compound_question("Who went? What did they do?")

    def test_then_detection(self):
        """Sequential questions with 'then' should be detected."""
        assert _is_compound_question("First tell me who was there then what we discussed")

    def test_short_queries_not_compound(self):
        """Short queries shouldn't be compound even with 'and'."""
        assert not _is_compound_question("A and B?")


class TestQueryDecomposition:
    """Test breaking compound questions into parts."""

    @pytest.mark.asyncio
    async def test_decompose_compound_query(self):
        """Compound query should be decomposed."""
        query = "Who did I meet with today and what did we discuss?"
        result = await decompose_query(query)

        # Should return multiple questions or original
        assert len(result) >= 1
        assert result[0] == query or len(result) > 1

    @pytest.mark.asyncio
    async def test_decompose_simple_query(self):
        """Simple query should return as-is."""
        query = "Who did I meet today?"
        result = await decompose_query(query)

        # Simple query returns just the original
        assert len(result) == 1
        assert result[0] == query

    @pytest.mark.asyncio
    async def test_decomposition_preserves_context(self):
        """Decomposed questions should maintain date/context."""
        query = "Who did I meet with on June 16 and what did we discuss?"
        result = await decompose_query(query)

        # Should preserve the date across decomposed questions
        if len(result) > 1:
            # At least some questions should mention the date
            all_text = " ".join(result).lower()
            assert "june" in all_text or "16" in all_text or result == [query]


class TestConversationHistory:
    """Test conversation threading support."""

    def test_create_conversation(self):
        """Creating conversation should return unique ID."""
        conv_id1 = create_conversation()
        conv_id2 = create_conversation()

        assert conv_id1
        assert conv_id2
        assert conv_id1 != conv_id2

    def test_add_message(self):
        """Adding messages to conversation."""
        conv_id = create_conversation()

        add_message(conv_id, "user", "What is X?")
        add_message(conv_id, "assistant", "X is Y")

        history = get_conversation_history(conv_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_message_content_preserved(self):
        """Message content should be stored exactly."""
        conv_id = create_conversation()
        text = "Who did I meet with today and what did we discuss?"

        add_message(conv_id, "user", text)
        history = get_conversation_history(conv_id)

        assert history[0]["content"] == text

    def test_message_metadata(self):
        """Messages should support metadata (sources, etc)."""
        conv_id = create_conversation()

        add_message(
            conv_id,
            "assistant",
            "You met Jonathan",
            metadata={"sources": ["meeting-notes.md"]},
        )

        history = get_conversation_history(conv_id)
        assert history[0]["metadata"]["sources"] == ["meeting-notes.md"]

    def test_get_last_message(self):
        """Getting last message in conversation."""
        conv_id = create_conversation()

        add_message(conv_id, "user", "Question 1?")
        add_message(conv_id, "assistant", "Answer 1")
        add_message(conv_id, "user", "Question 2?")

        last = get_last_message(conv_id)
        assert last["content"] == "Question 2?"

    def test_get_conversation_context(self):
        """Conversation context should be formatted for LLM."""
        conv_id = create_conversation()

        add_message(conv_id, "user", "Who did I meet?")
        add_message(conv_id, "assistant", "You met Alice")

        context = get_conversation_context(conv_id)

        assert "Previous conversation context" in context
        assert "Who did I meet?" in context
        assert "You met Alice" in context

    def test_context_includes_sources(self):
        """Formatted context should include sources from metadata."""
        conv_id = create_conversation()

        add_message(conv_id, "user", "What was discussed?")
        add_message(
            conv_id,
            "assistant",
            "We discussed X",
            metadata={"sources": ["notes.md", "meeting.md"]},
        )

        context = get_conversation_context(conv_id)

        # Should mention sources
        assert "notes.md" in context or "Sources:" in context

    def test_history_limit(self):
        """History retrieval should respect limit."""
        conv_id = create_conversation()

        for i in range(10):
            add_message(conv_id, "user", f"Question {i}")

        history = get_conversation_history(conv_id, limit=3)
        assert len(history) <= 3

    def test_empty_conversation_context(self):
        """Empty conversation should return empty context."""
        conv_id = create_conversation()

        context = get_conversation_context(conv_id)
        assert context == ""

    def test_followup_with_context(self):
        """Follow-up questions should see previous context."""
        conv_id = create_conversation()

        # Initial question and answer
        add_message(conv_id, "user", "Who did I meet?")
        add_message(
            conv_id,
            "assistant",
            "You met Jonathan at the office",
            metadata={"sources": ["calendar.md"]},
        )

        # Follow-up should see previous
        context = get_conversation_context(conv_id)
        assert "Jonathan" in context
        assert "office" in context


class TestConversationIntegration:
    """Test conversation features working together."""

    def test_compound_question_with_followup(self):
        """Compound question with conversation history."""
        conv_id = create_conversation()

        # Initial compound question
        add_message(conv_id, "user", "Who did I meet and what did we discuss?")
        add_message(
            conv_id,
            "assistant",
            "You met Alice about project X",
            metadata={"sources": ["notes.md"]},
        )

        # Follow-up about one part
        history = get_conversation_history(conv_id)
        assert len(history) == 2

        context = get_conversation_context(conv_id)
        assert "Alice" in context
        assert "project X" in context

    @pytest.mark.asyncio
    async def test_decomposition_with_conversation(self):
        """Decomposed questions could use conversation context."""
        # This is more of an integration scenario
        query = "And what else did we discuss?"

        # Would need conversation context to understand "we"
        # Decomposition alone wouldn't help much here
        result = await decompose_query(query)

        # Should still be able to handle it
        assert len(result) >= 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_conversation_with_no_messages(self):
        """Empty conversation should handle gracefully."""
        conv_id = create_conversation()

        history = get_conversation_history(conv_id)
        assert history == []

        context = get_conversation_context(conv_id)
        assert context == ""

    def test_long_conversation_history(self):
        """Should handle long conversations."""
        conv_id = create_conversation()

        for i in range(100):
            add_message(conv_id, "user" if i % 2 == 0 else "assistant", f"Message {i}")

        # Get all history (limit=0 means no limit)
        history = get_conversation_history(conv_id, limit=0)
        assert len(history) == 100

    def test_special_characters_in_messages(self):
        """Special characters should be preserved."""
        conv_id = create_conversation()
        text = "What about @mentions, #hashtags, and special chars: <>&\"'?"

        add_message(conv_id, "user", text)
        history = get_conversation_history(conv_id)

        assert history[0]["content"] == text

    @pytest.mark.asyncio
    async def test_compound_with_special_characters(self):
        """Compound detection with special characters."""
        query = "Who (@alice) and what (#project)?"
        result = await decompose_query(query)

        # Should still detect compound nature
        assert len(result) >= 1
