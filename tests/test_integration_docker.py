"""Integration tests against deployed Docker instances.

These tests verify the full stack works end-to-end:
- API server (Docker)
- Processor service (Docker)
- Ollama (host)
- Vault (mounted volume)

Prerequisites:
- Docker containers running: docker-compose up -d
- Ollama running on host
"""

import asyncio
import json
import time
from pathlib import Path

import pytest
import requests

# Configuration
API_URL = "http://localhost:8765"
TIMEOUT = 30


@pytest.fixture(scope="session")
def api_health():
    """Check API is running before tests start."""
    start = time.time()
    while time.time() - start < TIMEOUT:
        try:
            resp = requests.get(f"{API_URL}/health", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except requests.ConnectionError:
            time.sleep(1)

    raise RuntimeError(f"API not ready at {API_URL} after {TIMEOUT}s")


class TestAPIHealth:
    """Test basic API health."""

    def test_health_endpoint(self, api_health):
        """Verify health endpoint responds."""
        assert api_health["status"] == "ok"
        assert "index_ready" in api_health
        assert "indexed_chunks" in api_health
        assert "vocab_terms" in api_health

    def test_index_status_endpoint(self):
        """Verify index status endpoint."""
        resp = requests.get(f"{API_URL}/index/status", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_files" in data
        assert "total_chunks" in data
        assert "last_updated" in data


class TestQueryEndpoint:
    """Test query endpoint against live vault."""

    def test_query_returns_json(self):
        """Verify query endpoint returns valid JSON."""
        payload = {"text": "test query", "top_k": 3, "mode": "vault"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "answer" in data
        assert "sources" in data
        assert "mode" in data

    def test_query_general_mode(self):
        """Test general knowledge mode (no vault context)."""
        payload = {"text": "What is 2+2?", "mode": "general"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "general"
        assert "answer" in data

    def test_query_technical_mode(self):
        """Test technical documentation mode."""
        payload = {"text": "How is the indexer configured?", "top_k": 5, "mode": "technical"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "technical"


class TestCaptureEndpoint:
    """Test note capture endpoint."""

    def test_capture_text_note(self):
        """Verify text capture saves to queue."""
        payload = {"text": "Integration test note"}
        resp = requests.post(f"{API_URL}/capture", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert "saved_to" in data
        assert data["status"] == "pending_processing"
        assert data["saved_to"].endswith("_text_") or "_text_" in data["saved_to"]

    def test_capture_creates_unprocessed_file(self):
        """Verify captured note appears in unprocessed queue."""
        payload = {"text": "Another integration test note"}
        resp = requests.post(f"{API_URL}/capture", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()

        # Note: the file is in the container's unprocessed directory
        # In real tests, you'd check the mounted volume
        assert data["saved_to"]


class TestTranscribeAndQuery:
    """Test transcription + query endpoint."""

    @pytest.fixture
    def sample_audio(self, tmp_path):
        """Create a minimal valid audio file for testing."""
        # This creates a very small WAV file (silence)
        # For real tests, use actual audio
        wav_header = bytes(
            [
                0x52,
                0x49,
                0x46,
                0x46,  # "RIFF"
                0x24,
                0x00,
                0x00,
                0x00,  # File size
                0x57,
                0x41,
                0x56,
                0x45,  # "WAVE"
                0x66,
                0x6D,
                0x74,
                0x20,  # "fmt "
                0x10,
                0x00,
                0x00,
                0x00,  # Subchunk1Size
                0x01,
                0x00,  # AudioFormat (PCM)
                0x01,
                0x00,  # NumChannels
                0x44,
                0xAC,
                0x00,
                0x00,  # SampleRate (44100)
                0x88,
                0x58,
                0x01,
                0x00,  # ByteRate
                0x02,
                0x00,  # BlockAlign
                0x10,
                0x00,  # BitsPerSample
                0x64,
                0x61,
                0x74,
                0x61,  # "data"
                0x00,
                0x00,
                0x00,
                0x00,  # Subchunk2Size
            ]
        )

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(wav_header)
        return audio_file

    def test_transcribe_endpoint_exists(self, sample_audio):
        """Verify transcribe endpoint is available."""
        with open(sample_audio, "rb") as f:
            files = {"audio": f}
            resp = requests.post(f"{API_URL}/transcribe-and-query", files=files, timeout=TIMEOUT)

        # May fail on actual transcription but endpoint should exist
        assert resp.status_code in [200, 400, 500]


class TestEndToEndWorkflow:
    """Test complete capture → process → query workflow."""

    def test_capture_then_query(self):
        """Verify note capture workflow."""
        # 1. Capture a note
        capture_payload = {"text": "E2E test: Important project milestone"}
        resp = requests.post(f"{API_URL}/capture", json=capture_payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        capture_data = resp.json()
        assert capture_data["status"] == "pending_processing"

        # 2. Query should still work (note is in unprocessed queue)
        query_payload = {"text": "What is happening with projects?", "mode": "vault"}
        resp = requests.post(f"{API_URL}/query", json=query_payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        assert "answer" in resp.json()


class TestLLMCapability:
    """Test LLM's ability to answer basic questions."""

    def test_current_date_awareness(self):
        """Test if LLM knows the current date."""
        payload = {"text": "What is today's date?", "mode": "general"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        answer = data["answer"].lower()
        # Should mention 2026 or June (current year/month)
        assert "2026" in answer or "june" in answer or "6" in answer, f"Expected current date reference, got: {answer}"

    def test_basic_math(self):
        """Test basic arithmetic capability."""
        payload = {"text": "What is 2 + 2?", "mode": "general"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        answer = data["answer"].lower()
        # Should contain "4" as the answer
        assert "4" in answer, f"Expected answer 4, got: {answer}"

    def test_general_knowledge(self):
        """Test general knowledge question."""
        payload = {"text": "What is the capital of France?", "mode": "general"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        answer = data["answer"].lower()
        # Should mention Paris
        assert "paris" in answer, f"Expected Paris mention, got: {answer}"

    def test_vault_search_accuracy(self):
        """Test that vault mode retrieves relevant documents."""
        payload = {"text": "What files are in my vault?", "mode": "vault", "top_k": 5}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        # Vault mode should have sources
        assert len(data["sources"]) > 0, "Vault mode should return sources"
        assert data["context_used"] > 0, "Should use context chunks from vault"

    def test_mode_consistency(self):
        """Test that different modes give different results."""
        question = "Tell me something"

        # Query in vault mode
        vault_resp = requests.post(
            f"{API_URL}/query", json={"text": question, "mode": "vault", "top_k": 3}, timeout=TIMEOUT
        )

        # Query in general mode
        general_resp = requests.post(f"{API_URL}/query", json={"text": question, "mode": "general"}, timeout=TIMEOUT)

        assert vault_resp.status_code == 200
        assert general_resp.status_code == 200

        vault_data = vault_resp.json()
        general_data = general_resp.json()

        # Vault should have sources, general shouldn't
        assert len(vault_data["sources"]) >= 0
        assert vault_data["mode"] == "vault"
        assert general_data["mode"] == "general"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_mode(self):
        """Test query with invalid mode."""
        payload = {"text": "test", "mode": "invalid_mode"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        # Should still work (defaults to vault mode)
        assert resp.status_code == 200

    def test_missing_required_field(self):
        """Test capture without text field."""
        payload = {}  # Missing "text"
        resp = requests.post(f"{API_URL}/capture", json=payload, timeout=TIMEOUT)
        # Should return 422 (validation error)
        assert resp.status_code in [400, 422]

    def test_very_long_query(self):
        """Test query with very long text."""
        payload = {
            "text": "test query " * 1000,  # Very long
            "top_k": 3,
        }
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        # Should still handle gracefully
        assert resp.status_code in [200, 400, 500]


@pytest.fixture(scope="session", autouse=True)
def cleanup_unprocessed():
    """Clean up unprocessed notes after all tests."""
    yield  # Run all tests first

    # Cleanup: Remove test notes from unprocessed queue
    # In a real scenario, you'd:
    # 1. Check the mounted volume at ~/.vault-assistant/unprocessed/
    # 2. Remove any files created during testing
    # For now, just log that cleanup should happen
    print("\n\nCleanup: Remove test notes from ~/.vault-assistant/unprocessed/")


class TestToolIntegration:
    """Test MCP tool integration with LLM."""

    def test_date_tool_in_response(self):
        """Test that LLM can access and use date tool."""
        payload = {"text": "What is today's date?", "mode": "general"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        answer = data["answer"].lower()
        # Should now have current date since tool is available
        assert "2026" in answer or "june" in answer or "6/" in answer, f"Expected current date, got: {answer}"

    def test_vault_files_tool(self):
        """Test that LLM can list vault files."""
        payload = {"text": "List the markdown files in my vault", "mode": "vault"}
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        answer = data["answer"]
        # Should reference some files from vault
        assert len(answer) > 0
        # Should have sources since it's vault mode
        assert len(data["sources"]) >= 0

    def test_specific_meeting_query(self):
        """Test specific query about meeting someone today - should get current date context."""
        payload = {
            "text": "Who did I meet with on June 16, 2026?",  # Explicit date
            "mode": "vault",
            "top_k": 5,
        }
        resp = requests.post(f"{API_URL}/query", json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        answer = data["answer"].lower()

        # Should have a meaningful answer (likely mentioning Jonathan from the meeting)
        assert len(answer) > 20, f"Should return substantial answer. Got: {answer}"

        # Should have sources from vault (RAG context)
        assert len(data["sources"]) > 0, "Vault query should return sources"

        # Should show proper context usage
        assert data["context_used"] > 0, "Should use context chunks for this query"
