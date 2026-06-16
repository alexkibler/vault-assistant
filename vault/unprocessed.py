import uuid
from datetime import datetime
from pathlib import Path
from vault.logger import log_pending

UNPROCESSED_DIR = Path("~/.vault-assistant/unprocessed").expanduser()


def save_unprocessed_note(text: str, source: str = "voice") -> str:
    """
    Save a note to the unprocessed folder.
    Returns the relative filename saved.

    Args:
        text: The note content
        source: "voice", "text", "query_answer", etc.
    """
    UNPROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp and UUID for uniqueness
    timestamp = datetime.now().isoformat().replace(":", "-")
    note_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{source}_{note_id}.md"

    filepath = UNPROCESSED_DIR / filename

    # Write with minimal frontmatter
    content = f"""---
source: {source}
created: {datetime.now().isoformat()}
processed: false
---

{text}
"""

    filepath.write_text(content, encoding="utf-8")

    # Log to vault
    log_pending(filename, source, text)

    return filename


def get_unprocessed_notes() -> list[dict]:
    """Get all unprocessed notes with their content."""
    if not UNPROCESSED_DIR.exists():
        return []

    notes = []
    for filepath in sorted(UNPROCESSED_DIR.glob("*.md")):
        try:
            content = filepath.read_text(encoding="utf-8")
            notes.append(
                {
                    "filename": filepath.name,
                    "path": filepath,
                    "content": content,
                }
            )
        except Exception:
            continue

    return notes


def mark_processed(filename: str):
    """Mark a note as processed by adding a timestamp."""
    filepath = UNPROCESSED_DIR / filename
    if not filepath.exists():
        return

    content = filepath.read_text(encoding="utf-8")
    # Update processed flag in frontmatter
    content = content.replace("processed: false", f"processed: {datetime.now().isoformat()}", 1)
    filepath.write_text(content, encoding="utf-8")


def delete_processed(filename: str):
    """Delete a processed note."""
    filepath = UNPROCESSED_DIR / filename
    filepath.unlink(missing_ok=True)
