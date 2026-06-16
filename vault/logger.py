"""Logging for vault operations."""

from datetime import datetime
from pathlib import Path
from config import Config


LOG_FILE = Config.VAULT_PATH / "vault-assistant.log"


def log_pending(filename: str, source: str, text_preview: str):
    """Log when a note is added to the processing queue."""
    timestamp = datetime.now().isoformat()
    preview = text_preview[:80].replace("\n", " ")
    entry = f"[{timestamp}] PENDING ({source}): {filename}\n  Preview: {preview}...\n\n"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def log_processed(filename: str, vault_path: str, reasoning: str = ""):
    """Log when a note is processed and moved to vault."""
    timestamp = datetime.now().isoformat()
    reasoning_str = f"\n  Reason: {reasoning}" if reasoning else ""
    entry = f"[{timestamp}] PROCESSED: {filename}\n  → {vault_path}{reasoning_str}\n\n"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def log_error(filename: str, error: str):
    """Log when a note fails to process."""
    timestamp = datetime.now().isoformat()
    entry = f"[{timestamp}] ERROR: {filename}\n  Error: {error}\n\n"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
