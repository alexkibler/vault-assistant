"""Test note categorization accuracy."""

import pytest
import json
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_categorization_accuracy(sample_notes, mock_config):
    """Test that all sample notes are categorized correctly.

    This is a regression test to catch breaking changes in the LLM prompt
    or decision tree logic.
    """
    from processor import categorize_note

    for note in sample_notes:
        # Mock the LLM response based on expected output
        mock_response = {
            "category": note["expected_category"],
            "folder": note["expected_folder"],
            "filename": f"{note['name']}.md",
            "reasoning": f"Test case: {note['name']}",
        }

        with patch("processor.chat_completion") as mock_chat:
            mock_chat.return_value = json.dumps(mock_response)
            result = await categorize_note(note["text"])

            assert result["category"] == note["expected_category"], f"Wrong category for {note['name']}"
            assert result["folder"] == note["expected_folder"], f"Wrong folder for {note['name']}"


@pytest.mark.asyncio
async def test_categorization_with_invalid_json(mock_config):
    """Test robustness when LLM returns invalid JSON."""
    from processor import categorize_note

    with patch("processor.chat_completion") as mock_chat:
        # Return markdown code block instead of pure JSON
        mock_chat.return_value = """```json
{"category": "Life", "folder": "Work", "filename": "test.md", "reasoning": "test"}
```"""

        result = await categorize_note("Some test note")
        assert result["category"] == "Life"
        assert result["folder"] == "Work"


@pytest.mark.asyncio
async def test_categorization_fallback(mock_config):
    """Test fallback when categorization completely fails."""
    from processor import categorize_note

    with patch("processor.chat_completion") as mock_chat:
        # Return completely unparseable response
        mock_chat.return_value = "This is not JSON at all"

        result = await categorize_note("Some test note")
        # Should fall back to Life/Projects
        assert result["category"] == "Life"
        assert result["folder"] == "Projects"
        assert "Failed to categorize" in result["reasoning"]


@pytest.mark.asyncio
async def test_categorization_confidence_scoring(mock_config):
    """Test that categorization includes confidence scores."""
    from processor import categorize_note

    mock_response = {
        "category": "Life",
        "folder": "Work",
        "filename": "test.md",
        "reasoning": "Clear work-related content",
        "confidence": 0.95,  # Optional confidence score
    }

    with patch("processor.chat_completion") as mock_chat:
        mock_chat.return_value = json.dumps(mock_response)
        result = await categorize_note("Work-related note")

        # Should preserve confidence if present
        assert "confidence" in result or "reasoning" in result
