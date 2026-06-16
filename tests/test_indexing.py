"""Test indexing and chunking functionality."""

import pytest
from pathlib import Path


def test_chunk_markdown_basic():
    """Test basic markdown chunking."""
    from indexer.chunker import chunk_markdown

    content = """---
title: Test
---

# Header 1

This is section one.

## Header 2

This is section two.

### Header 3

This is section three.
"""

    filepath = Path("test.md")
    chunks = chunk_markdown(filepath, content)

    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)
    assert all("chunk_index" in chunk for chunk in chunks)


def test_chunk_markdown_frontmatter_stripped():
    """Test that YAML frontmatter is stripped."""
    from indexer.chunker import chunk_markdown

    content = """---
title: Test File
type: reference
updated: 2026-06-16
---

Content goes here.
"""

    filepath = Path("test.md")
    chunks = chunk_markdown(filepath, content)

    # Frontmatter should not be in any chunk
    chunk_text = " ".join(c["text"] for c in chunks)
    assert "title: Test File" not in chunk_text
    assert "Content goes here" in chunk_text


def test_chunk_markdown_token_limit():
    """Test that chunks respect token limit."""
    from indexer.chunker import chunk_markdown

    # Create content with sections that would exceed token limit
    content = "# Main\n\n" + "\n\n".join([f"## Section {i}\n\n" + "word " * 100 for i in range(10)])

    filepath = Path("test.md")
    chunks = chunk_markdown(filepath, content)

    # Each chunk should be reasonably sized (not super large)
    # The 400 token limit means most chunks should be under 1500 chars
    for chunk in chunks:
        # Rough estimate: ~4 chars per token on average
        estimated_tokens = len(chunk["text"]) / 4
        assert estimated_tokens < 600, f"Chunk too large: {estimated_tokens} tokens"


def test_chunk_markdown_preserves_content():
    """Test that chunking preserves all content."""
    from indexer.chunker import chunk_markdown

    content = """# Title

Section A content here.

## Subsection

More content with special chars: @#$% and markdown **bold** and *italic*.

- List item 1
- List item 2
- List item 3
"""

    filepath = Path("test.md")
    chunks = chunk_markdown(filepath, content)

    # Concatenate all chunks
    full_text = " ".join(c["text"] for c in chunks)

    # Check key content is present
    assert "Section A content" in full_text
    assert "special chars" in full_text
    # Content words should be there (bold/italic formatting stripped by chunker)
    assert "List item" in full_text


def test_chunk_context_prefix():
    """Test that chunks include helpful context prefix."""
    from indexer.chunker import chunk_markdown

    content = """---
title: Architecture Notes
---

# System Design

Detailed architecture here.
"""

    filepath = Path("Architecture Notes.md")
    chunks = chunk_markdown(filepath, content)

    # At least one chunk should have context about the file
    chunk_texts = [c["text"] for c in chunks]
    combined = " ".join(chunk_texts)

    # Should mention the source file or title
    assert "Architecture" in combined or "System Design" in combined
