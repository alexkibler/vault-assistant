"""Auto-generate Whisper vocabulary from vault content."""

import re
from pathlib import Path
from collections import Counter


def extract_proper_nouns(content: str) -> set[str]:
    """Extract proper nouns (capitalized words) from content."""
    # Find capitalized words (proper nouns)
    words = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", content)
    return set(word for word in words if len(word) > 2)


def extract_wikilinks(content: str) -> set[str]:
    """Extract wikilinks from markdown content."""
    # Find [[wikilink]] patterns
    links = re.findall(r"\[\[([^\]]+)\]\]", content)
    return set(links)


def extract_code_terms(content: str) -> set[str]:
    """Extract technical terms from code blocks and backticks."""
    # Find `code` and code block content
    inline_code = re.findall(r"`([^`]+)`", content)
    # Find content between triple backticks
    code_blocks = re.findall(r"```.*?\n(.*?)```", content, re.DOTALL)

    terms = set(inline_code)
    for block in code_blocks:
        # Extract identifiers (camelCase, snake_case, PascalCase)
        identifiers = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", block)
        terms.update(id for id in identifiers if len(id) > 3)

    return terms


def build_vault_vocabulary(vault_path: Path, max_terms: int = 200) -> list[str]:
    """Build vocabulary from vault content.

    Analyzes all markdown files in the vault and extracts:
    - Proper nouns (capitalized names)
    - Wikilinks (note titles)
    - Technical terms from code blocks

    Args:
        vault_path: Path to vault root
        max_terms: Maximum number of terms to return (sorted by frequency)

    Returns:
        List of vocabulary terms ranked by frequency
    """
    all_terms = Counter()

    # Scan all markdown files
    for md_file in vault_path.rglob("*.md"):
        # Skip system files and logs
        if md_file.name.startswith("_") or md_file.name.startswith("."):
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")

            # Extract various term types with different weights
            proper_nouns = extract_proper_nouns(content)
            all_terms.update({term: 2 for term in proper_nouns})  # Weight: 2

            wikilinks = extract_wikilinks(content)
            all_terms.update({term: 3 for term in wikilinks})  # Weight: 3 (high priority)

            code_terms = extract_code_terms(content)
            all_terms.update({term: 1.5 for term in code_terms})  # Weight: 1.5

        except Exception as e:
            print(f"Warning: Could not parse {md_file}: {e}")

    # Get top terms by weighted frequency
    top_terms = all_terms.most_common(max_terms)
    return [term for term, _count in top_terms]


def merge_with_custom_vocab(auto_vocab: list[str], custom_vocab_file: Path) -> list[str]:
    """Merge auto-generated vocabulary with custom user vocabulary.

    Args:
        auto_vocab: Auto-generated vocabulary list
        custom_vocab_file: Path to _whisper-vocab.md file

    Returns:
        Merged vocabulary list with custom vocab taking precedence
    """
    merged = dict.fromkeys(auto_vocab)  # Preserve order, remove duplicates

    # Add custom vocab with higher priority (at front)
    if custom_vocab_file.exists():
        try:
            custom_content = custom_vocab_file.read_text(encoding="utf-8")
            # Extract one term per line (ignoring markdown)
            custom_terms = [
                line.strip() for line in custom_content.split("\n") if line.strip() and not line.startswith("#")
            ]

            # Add custom terms at front
            result = custom_terms + [t for t in auto_vocab if t not in custom_terms]
            return result[:200]  # Keep reasonable limit

        except Exception as e:
            print(f"Warning: Could not read custom vocabulary: {e}")

    return auto_vocab
