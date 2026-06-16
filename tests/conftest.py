"""Pytest fixtures and configuration."""

import pytest
from pathlib import Path
import tempfile
import json
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def temp_vault():
    """Create temporary vault directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        for folder in ["Life", "Context", "Archive"]:
            (vault_path / folder).mkdir()
            for subfolder in ["Work", "Projects", "Cycling"]:
                (vault_path / folder / subfolder).mkdir(exist_ok=True)
        yield vault_path


@pytest.fixture
def temp_unprocessed():
    """Create temporary unprocessed notes directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_notes():
    """Sample test notes with expected categorizations."""
    return [
        {
            "text": "Just finished implementing the vendor module DI pattern. It's clean and each vendor can now register its own services independently. Need to test with Priovant next.",
            "expected_category": "Life",
            "expected_folder": "Work",
            "name": "vendor_module",
        },
        {
            "text": "Meeting with Mark about infrastructure improvements. Discussed containerizing the background services and running them on the M4 mini instead of cloud VMs. Could save on costs.",
            "expected_category": "Life",
            "expected_folder": "Work",
            "name": "infrastructure_meeting",
        },
        {
            "text": "Thinking about upgrading to a 2x drivetrain for more climbing gear options. But the current 1x11 mullet is so dialed. Need to weigh pros and cons.",
            "expected_category": "Life",
            "expected_folder": "Cycling",
            "name": "drivetrain_upgrade",
        },
        {
            "text": "Crushed the McDermott 3-State Tour today. Average speed was better than last time, and the new tire setup definitely helped with grip on gravel sections.",
            "expected_category": "Life",
            "expected_folder": "Cycling",
            "name": "mcdermott_training",
        },
        {
            "text": "Configured Ollama to run with 8GB limit in OrbStack to prevent OOM issues. Set OLLAMA_NUM_KEEP=64 for context caching. Performance is much better now.",
            "expected_category": "Context",
            "expected_folder": "Technical",
            "name": "ollama_config",
        },
        {
            "text": "I prefer concise, direct responses. No fluff. Skip the preamble and get to the point. I also like when decisions include the reasoning.",
            "expected_category": "Context",
            "expected_folder": "Preferences",
            "name": "communication_preference",
        },
    ]


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing."""
    client = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def mock_lancedb():
    """Mock LanceDB for testing."""
    db = MagicMock()
    table = MagicMock()
    db.open_table = MagicMock(return_value=table)
    return db


@pytest.fixture
def mock_config(temp_vault, temp_unprocessed):
    """Mock configuration with temp paths."""
    with patch("config.Config") as config:
        config.VAULT_PATH = temp_vault
        config.LANCEDB_PATH = temp_vault / ".lancedb"
        config.OLLAMA_BASE_URL = "http://localhost:11434"
        config.OLLAMA_EMBED_MODEL = "nomic-embed-text"
        config.OLLAMA_CHAT_MODEL = "llama3.1:8b"
        yield config
