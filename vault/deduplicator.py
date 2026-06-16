"""Detect and manage duplicate notes in vault."""

import hashlib
from pathlib import Path
from typing import Optional


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def extract_markdown_content(filepath: Path) -> str:
    """Extract just the body content (without frontmatter) from markdown file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        # Remove YAML frontmatter
        lines = content.split("\n")
        if lines and lines[0] == "---":
            # Find closing ---
            end_idx = None
            for i in range(1, len(lines)):
                if lines[i] == "---":
                    end_idx = i + 1
                    break
            if end_idx:
                return "\n".join(lines[end_idx:]).strip()
        return content.strip()
    except Exception:
        return ""


def find_duplicates(vault_path: Path) -> dict[str, list[Path]]:
    """Find duplicate notes based on content hash.

    Args:
        vault_path: Root path of vault

    Returns:
        Dictionary mapping content hash to list of duplicate file paths
    """
    hashes = {}

    for md_file in vault_path.rglob("*.md"):
        # Skip system files
        if md_file.name.startswith("_") or md_file.name.startswith("."):
            continue

        content = extract_markdown_content(md_file)
        if not content:
            continue

        content_hash = compute_content_hash(content)

        if content_hash not in hashes:
            hashes[content_hash] = []
        hashes[content_hash].append(md_file)

    # Return only hashes with duplicates (2+ files)
    duplicates = {h: files for h, files in hashes.items() if len(files) > 1}
    return duplicates


def find_similar_notes(
    vault_path: Path,
    target_file: Path,
    similarity_threshold: float = 0.8,
) -> list[tuple[Path, float]]:
    """Find notes similar to a target note based on content.

    Args:
        vault_path: Root path of vault
        target_file: File to find similar notes for
        similarity_threshold: Minimum similarity score (0.0 to 1.0)

    Returns:
        List of (filepath, similarity_score) tuples
    """
    target_content = extract_markdown_content(target_file)
    if not target_content:
        return []

    # Simple similarity: word overlap
    target_words = set(target_content.lower().split())
    similar_files = []

    for md_file in vault_path.rglob("*.md"):
        if md_file == target_file:
            continue
        if md_file.name.startswith("_") or md_file.name.startswith("."):
            continue

        content = extract_markdown_content(md_file)
        if not content:
            continue

        content_words = set(content.lower().split())

        # Jaccard similarity
        if len(target_words) > 0:
            intersection = len(target_words & content_words)
            union = len(target_words | content_words)
            similarity = intersection / union if union > 0 else 0.0

            if similarity >= similarity_threshold:
                similar_files.append((md_file, similarity))

    # Sort by similarity descending
    return sorted(similar_files, key=lambda x: x[1], reverse=True)


def get_duplicate_report(vault_path: Path) -> str:
    """Generate a report of duplicate notes in the vault.

    Args:
        vault_path: Root path of vault

    Returns:
        Formatted report string
    """
    duplicates = find_duplicates(vault_path)

    if not duplicates:
        return "No duplicate notes found."

    report = f"Found {len(duplicates)} sets of duplicate notes:\n\n"

    for i, (content_hash, files) in enumerate(duplicates.items(), 1):
        report += f"{i}. Duplicates ({len(files)} copies):\n"
        for filepath in sorted(files):
            report += f"   - {filepath.relative_to(vault_path)}\n"
        report += "\n"

    return report
