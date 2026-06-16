# Installation Guide

Complete setup instructions for macOS, Linux, and Windows.

## macOS (Recommended)

### Prerequisites

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install requirements
brew install python@3.11 uv ollama
```

### Setup

```bash
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant
uv sync

cp .env.example .env
# Edit .env - change VAULT_PATH to your vault location
```

### Run Ollama

```bash
# Terminal 1: Start Ollama
brew services start ollama
# Or manually: ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Start vault-assistant

```bash
# Terminal 2: Start API
uv run uvicorn main:app --host 0.0.0.0 --port 8765
```

### Install as macOS Service (Optional)

For automatic startup:

```bash
cp com.vaultassistant.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.vaultassistant.plist
```

View logs:
```bash
tail -f ~/.vault-assistant/logs/stdout.log
```

---

## Linux

### Prerequisites (Ubuntu/Debian)

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv curl git

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

### Setup

```bash
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant
uv sync

cp .env.example .env
# Edit .env with your vault path
```

### Run

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start vault-assistant
uv run uvicorn main:app --host 0.0.0.0 --port 8765
```

### Install as systemd Service (Optional)

Create `/etc/systemd/system/vault-assistant.service`:

```ini
[Unit]
Description=Vault Assistant
After=network.target ollama.service

[Service]
Type=simple
User=alex
WorkingDirectory=/home/alex/vault-assistant
ExecStart=/home/alex/.local/bin/uv run uvicorn main:app --host 0.0.0.0 --port 8765
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vault-assistant
sudo systemctl start vault-assistant
systemctl status vault-assistant
```

---

## Windows (WSL2 Recommended)

### Option A: WSL2 + Linux (Recommended)

```bash
# Install WSL2 if not already installed
wsl --install -d Ubuntu-22.04

# In WSL2 terminal:
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt-get update && sudo apt-get install -y python3.11 curl git

# Download Ollama for Windows from https://ollama.ai
# Or in WSL2:
curl -fsSL https://ollama.ai/install.sh | sh
```

Continue with Linux instructions above.

### Option B: Native Windows (Docker)

Use Docker Compose:

```bash
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant
docker-compose up
```

See `docker-compose.yml` for configuration.

**Note:** Native Whisper transcription may not work on Windows; use faster-whisper.

---

## Docker

**For complete Docker setup including iCloud Drive on macOS, see [DOCKER.md](./DOCKER.md).**

Quick start:

```bash
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant

# Start Ollama on host first
ollama serve

# In another terminal, start containers
docker compose up -d

# Verify
curl http://localhost:8765/health
```

Docker Compose handles:
- FastAPI API server (port 8765)
- Note processor service
- Volume mounts for vault and indexes
- Automatic restart on failure

For details on vault paths, iCloud Drive mounting, and troubleshooting, see [DOCKER.md](./DOCKER.md).

---

## Verify Installation

After setup, test everything:

```bash
# Check API is responding
curl http://localhost:8765/health

# Check Ollama has models
ollama list

# Check vault is indexed
curl http://localhost:8765/index/status

# Test a query
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"text":"Test query"}'
```

---

## Troubleshooting

### "command not found: uv"

**macOS:**
```bash
brew install uv
# Or add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

**Linux/Windows:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

### "VAULT_PATH does not exist"

Check the path:
```bash
# macOS example - these should work:
ls ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud

# Linux/Windows - verify path exists:
ls /path/to/your/vault
```

### "No module named 'config'"

Ensure you ran `uv sync`:
```bash
cd /path/to/vault-assistant
uv sync --refresh
```

### "Connection refused: http://localhost:11434"

Ollama isn't running:
```bash
# macOS
brew services restart ollama
ollama serve  # Or start in new terminal

# Linux
ollama serve

# Windows (WSL2)
ollama serve
```

### "Whisper model download fails"

Use faster-whisper instead:
```bash
# Edit .env
WHISPER_MODEL=base  # Faster-whisper model name
```

### "Vault index keeps showing as not ready"

Large vaults take time to scan (100 files = ~30 seconds):

```bash
# Wait and check status
curl http://localhost:8765/index/status

# Check for errors in logs
tail -f ~/.vault-assistant/logs/stdout.log
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores (M1/M4 Mac) |
| **RAM** | 4GB | 8GB+ |
| **Disk** | 10GB | 20GB+ (models + index) |
| **Network** | 100Mbps | 1Gbps (for updates) |

---

## Next Steps

1. See [QUICKSTART.md](../QUICKSTART.md) for first query
2. Install [Obsidian Plugin](../../vault-assistant-obsidian-plugin)
3. Set up [Siri Shortcuts](./SIRI_SHORTCUTS.md) (iPhone)
4. Read [Architecture](./ARCHITECTURE.md) to understand how it works

---

## Getting Help

- **Installation issues**: Check [Troubleshooting](#troubleshooting) above
- **Feature requests**: [GitHub Issues](https://github.com/alexkibler/vault-assistant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/alexkibler/vault-assistant/discussions)
