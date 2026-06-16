import re
from pathlib import Path
from config import Config

# Module-level cache
_vocab_cache = None


def _extract_wikilinks(text: str) -> set[str]:
    """Extract [[wikilink]] targets."""
    matches = re.findall(r"\[\[([^\]]+)\]\]", text)
    return {m.split("|")[0].strip() for m in matches}


def _extract_hashtags(text: str) -> set[str]:
    """Extract #tag values from text."""
    matches = re.findall(r"#(\w+)", text)
    return set(matches)


def _extract_aliases(metadata: dict) -> set[str]:
    """Extract aliases from YAML frontmatter."""
    aliases_str = metadata.get("aliases", "")
    if isinstance(aliases_str, str):
        return {a.strip() for a in aliases_str.split(",") if a.strip()}
    return set()


def _extract_proper_nouns(text: str) -> set[str]:
    """Extract capitalized multi-word sequences (likely proper nouns)."""
    matches = re.findall(r"\b([A-Z]\w+\s+[A-Z]\w+[\w\s]*)", text)
    return set(matches)


def build_vocab_cache() -> str:
    """Rebuild vocabulary cache from vault. Return vocab string."""
    global _vocab_cache

    vocab_terms = set()

    # Scan all .md files
    for md_file in Config.VAULT_PATH.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")

            # Extract frontmatter
            if content.startswith("---"):
                match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
                if match:
                    frontmatter_text = match.group(1)
                    metadata = {}
                    for line in frontmatter_text.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            metadata[key.strip()] = val.strip().strip('"')
                    vocab_terms.update(_extract_aliases(metadata))

            # Extract wikilinks, tags, proper nouns
            vocab_terms.update(_extract_wikilinks(content))
            vocab_terms.update(_extract_hashtags(content))
            vocab_terms.update(_extract_proper_nouns(content))

        except Exception:
            continue

    # Add custom vocab from _whisper-vocab.md if it exists
    custom_vocab_file = Config.VAULT_PATH / "_whisper-vocab.md"
    if custom_vocab_file.exists():
        try:
            custom_content = custom_vocab_file.read_text(encoding="utf-8")
            custom_terms = [line.strip() for line in custom_content.split("\n") if line.strip() and not line.startswith("#")]
            vocab_terms.update(custom_terms)
        except Exception:
            pass

    # Deduplicate, sort, truncate to 200 tokens (rough: 1 token ≈ 0.75 words)
    vocab_list = sorted(list(vocab_terms))
    vocab_str = ", ".join(vocab_list)

    # Truncate to roughly 200 tokens
    max_chars = int(200 * 4 / 1.3)  # ~150 tokens per 1000 chars as rough estimate
    if len(vocab_str) > max_chars:
        vocab_str = vocab_str[:max_chars].rsplit(",", 1)[0]

    _vocab_cache = vocab_str
    return vocab_str


def get_vocab() -> str:
    """Get cached vocabulary string."""
    global _vocab_cache
    if _vocab_cache is None:
        return build_vocab_cache()
    return _vocab_cache
