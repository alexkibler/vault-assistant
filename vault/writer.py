from datetime import datetime
from pathlib import Path
from config import Config


async def write_to_vault(
    text: str,
    target: str = "daily",
) -> str:
    """Write text to vault. Return relative file path written."""
    if target == "daily":
        return await _write_daily_note(text)
    elif target == "inbox":
        return await _write_inbox(text)
    else:
        raise ValueError(f"Unknown target: {target}")


async def _write_daily_note(text: str) -> str:
    """Write to daily note. Return relative path."""
    today = datetime.now().strftime(Config.DAILY_NOTE_FORMAT)
    file_path = Config.VAULT_PATH / f"{today}.md"

    # Ensure file exists with header
    if not file_path.exists():
        file_path.write_text(f"# {today}\n\n", encoding="utf-8")

    # Append entry
    current = file_path.read_text(encoding="utf-8")
    time_str = datetime.now().strftime("%H:%M")
    new_entry = f"- {time_str} {text}\n"
    file_path.write_text(current + new_entry, encoding="utf-8")

    return today + ".md"


async def _write_inbox(text: str) -> str:
    """Write to inbox. Return relative path."""
    file_path = Config.VAULT_PATH / Config.INBOX_FILE

    # Ensure file exists with header
    if not file_path.exists():
        file_path.write_text("# Inbox\n\n", encoding="utf-8")

    # Append entry
    current = file_path.read_text(encoding="utf-8")
    iso_time = datetime.now().isoformat()
    new_entry = f"- {iso_time} {text}\n"
    file_path.write_text(current + new_entry, encoding="utf-8")

    return Config.INBOX_FILE
