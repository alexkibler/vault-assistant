#!/usr/bin/env python3
"""
Process unprocessed notes and categorize them into the vault.
Run via launchd or manually: uv run processor.py
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path

from config import Config
from llm.ollama import chat_completion
from vault.unprocessed import get_unprocessed_notes, delete_processed
from vault.logger import log_processed, log_error


CATEGORIZATION_PROMPT = """Categorize this note into the vault structure.

CATEGORY CHOICES: Choose exactly ONE
- "Life" if about personal goals, projects, decisions, health, work, life events, hobbies, training, fitness
- "Context" if about technical infrastructure documentation, system preferences, communication style, learning interests
- "Archive" if about completed historical projects

CRITICAL DOMAIN RULES (DO NOT IGNORE):
- "Cycling" folder: ONLY for bikes, rides, training, fitness, cycling equipment, gravel bikes, drivetrain
- "Gaming" folder: ONLY for video games, board games, gaming preferences - NEVER for other hobbies
- "Work" folder: work projects, meetings, implementation details, professional decisions
- "Technical" (Context): infrastructure documentation, system configs, architecture - NOT personal preferences
- "Preferences" (Context): personal communication style, tool preferences, working habits - NOT infrastructure

FOLDER CHOICES: Choose exactly ONE
- For Life: Goals, Projects, Health, Work, Family, Gaming, Cycling, Music, Home, Homelab, Other
- For Context: Technical, Preferences, Identity, Interests, Home, Other
- For Archive: Completed Projects, Old Configs, Other

FILENAME: A short descriptive title (max 5 words) ending with .md

DECISION TREE:
1. Is this about cycling, bikes, or training? → Life/Cycling
2. Is this about work/professional? → Life/Work
3. Is this a personal meeting/discussion note? → Life/Work (not Context/Technical)
4. Is this about infrastructure config/setup documentation? → Context/Technical
5. Is this about preferences (how you like to work/communicate)? → Context/Preferences
6. Is this about a personal hobby/interest (non-work)? → Life/{appropriate hobby folder}

Return ONLY valid JSON with no markdown or explanation:
{{
  "category": "Life",
  "folder": "Cycling",
  "filename": "Trek Checkpoint Setup.md",
  "reasoning": "specific domain and reasoning"
}}

Note to categorize:
---
{note_text}
---"""


FORMATTING_PROMPT = """Add YAML frontmatter to this note and return the complete formatted note.

Category: {category}
Folder: {folder}

Use this frontmatter format:
---
title: "{filename}"
type: personal-reference
updated: 2026-06-16
---

Then include the note content below the frontmatter.

Original note:
{note_text}

Return ONLY the formatted note (frontmatter + content), with no markdown code blocks or extra explanation."""


async def categorize_note(note_text: str) -> dict:
    """Use LLM to categorize a note."""
    import json

    system_prompt = (
        "You are an expert at vault organization. Respond with ONLY valid JSON, no markdown or explanation."
    )
    prompt = CATEGORIZATION_PROMPT.format(note_text=note_text)

    response = await chat_completion(system_prompt, prompt)

    # Try to extract JSON from response
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        # Find JSON object boundaries if not starting with {
        if "{" in json_str and "}" in json_str:
            start = json_str.index("{")
            end = json_str.rindex("}") + 1
            json_str = json_str[start:end]

        result = json.loads(json_str)
        return result
    except Exception as e:
        print(f"Error parsing categorization response: {e}")
        print(f"Response was: {repr(response[:300])}")
        # Fallback to Life/Projects
        return {
            "category": "Life",
            "folder": "Projects",
            "filename": f"Uncategorized {datetime.now().strftime('%Y-%m-%d %H:%M')}.md",
            "reasoning": "Failed to categorize, defaulting to Life/Projects",
        }


async def format_note(note_text: str, category: str, folder: str, filename: str) -> str:
    """Use LLM to format note with appropriate frontmatter."""
    system_prompt = "You are an expert at formatting personal notes. Return only the formatted note with frontmatter."
    prompt = FORMATTING_PROMPT.format(
        note_text=note_text,
        category=category,
        folder=folder,
        filename=filename,
    )

    return await chat_completion(system_prompt, prompt)


async def process_note(filepath: Path, note_data: dict) -> bool:
    """
    Process a single unprocessed note.
    Returns True if successfully processed, False otherwise.
    """
    try:
        # Extract text content (remove frontmatter)
        content = note_data["content"]
        match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
        note_text = match.group(1) if match else content

        print(f"Processing: {note_data['filename']}")

        # Categorize
        category_info = await categorize_note(note_text)
        category = category_info["category"]
        folder = category_info["folder"]
        filename = category_info["filename"]

        # Ensure filename is safe and unique
        target_dir = Config.VAULT_PATH / category / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / filename
        if target_path.exists():
            base, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            counter = 1
            while target_path.exists():
                new_name = f"{base} ({counter}).{ext}" if ext else f"{base} ({counter})"
                target_path = target_dir / new_name
                counter += 1

        # Format note with frontmatter
        formatted = await format_note(note_text, category, folder, filename)

        # Write to vault
        target_path.write_text(formatted, encoding="utf-8")
        relative_path = target_path.relative_to(Config.VAULT_PATH)
        print(f"  → Saved to: {relative_path}")

        # Log to vault
        log_processed(
            note_data["filename"],
            str(relative_path),
            category_info.get("reasoning", "")
        )

        # Mark as processed and delete
        delete_processed(note_data["filename"])
        print(f"  ✓ Processed")

        return True

    except Exception as e:
        error_msg = str(e)
        print(f"  ✗ Error processing {filepath}: {error_msg}")
        log_error(note_data["filename"], error_msg)
        return False


async def process_all_unprocessed():
    """Process all unprocessed notes."""
    notes = get_unprocessed_notes()

    if not notes:
        print("No unprocessed notes found.")
        return

    print(f"Found {len(notes)} unprocessed note(s).")
    print()

    success = 0
    failed = 0

    for note in notes:
        if await process_note(note["path"], note):
            success += 1
        else:
            failed += 1

    print()
    print(f"Processing complete: {success} succeeded, {failed} failed")


if __name__ == "__main__":
    Config.validate()
    asyncio.run(process_all_unprocessed())
