"""Logging for vault operations."""

from datetime import datetime
from pathlib import Path
from config import Config


LOG_FILE = Config.VAULT_PATH / "vault-assistant.md"


def log_pending(filename: str, source: str, text_preview: str):
    """Log when a note is added to the processing queue."""
    timestamp = datetime.now().isoformat()
    preview = text_preview[:80].replace("\n", " ")
    entry = f"- **PENDING** ({source}) `{filename}`\n  - Preview: {preview}...\n  - Time: {timestamp}\n\n"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Initialize file with header if it doesn't exist
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("# Vault Assistant Log\n\n")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def log_processed(filename: str, vault_path: str, reasoning: str = ""):
    """Log when a note is processed and moved to vault."""
    timestamp = datetime.now().isoformat()
    reasoning_str = f"\n  - Reason: {reasoning}" if reasoning else ""
    entry = f"- **PROCESSED** `{filename}`\n  - Location: [[{vault_path}]]\n  - Time: {timestamp}{reasoning_str}\n\n"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def log_error(filename: str, error: str):
    """Log when a note fails to process."""
    timestamp = datetime.now().isoformat()
    entry = f"- **ERROR** `{filename}`\n  - Error: {error}\n  - Time: {timestamp}\n\n"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
