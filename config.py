import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration loader with validation."""

    # Vault paths
    VAULT_PATH = (
        Path(os.getenv("VAULT_PATH", "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/MyVault"))
        .expanduser()
        .resolve()
    )
    LANCEDB_PATH = Path(os.getenv("LANCEDB_PATH", "~/.vault-assistant/lancedb")).expanduser().resolve()

    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")

    # Whisper
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
    WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")

    # Vault write targets
    DAILY_NOTE_FORMAT = os.getenv("DAILY_NOTE_FORMAT", "%Y-%m-%d")
    INBOX_FILE = os.getenv("INBOX_FILE", "inbox.md")

    # Service
    SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
    SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8765"))

    # RAG Optimization
    # Strategy: "basic", "expansion", "reranking", "hybrid", "optimized"
    RAG_STRATEGY = os.getenv("RAG_STRATEGY", "optimized")
    # Enable query expansion (2-3 related queries)
    RAG_QUERY_EXPANSION = os.getenv("RAG_QUERY_EXPANSION", "true").lower() == "true"
    # Enable reranking (LLM filters results by relevance)
    RAG_RERANKING = os.getenv("RAG_RERANKING", "true").lower() == "true"
    # Enable hybrid search (keyword + vector)
    RAG_HYBRID_SEARCH = os.getenv("RAG_HYBRID_SEARCH", "true").lower() == "true"

    @classmethod
    def validate(cls):
        """Validate critical configuration at startup."""
        if not cls.VAULT_PATH.exists():
            raise ValueError(f"VAULT_PATH does not exist: {cls.VAULT_PATH}")

        # Ensure LanceDB path exists
        cls.LANCEDB_PATH.mkdir(parents=True, exist_ok=True)

        # Ensure logs directory exists
        logs_path = Path("~/.vault-assistant/logs").expanduser()
        logs_path.mkdir(parents=True, exist_ok=True)
