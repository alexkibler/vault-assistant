# Vault Assistant - Quick Start

Get up and running in 5 minutes.

## Prerequisites

- **macOS** (Monterey or later) or Linux/WSL2
- **Ollama** installed and running
- **Python 3.11+**
- **uv** package manager (`brew install uv`)

## Step 1: Check Prerequisites

```bash
# Check Python
python3 --version    # Should be 3.11+

# Check uv
uv --version

# Check Ollama is running
curl http://localhost:11434/api/tags
# Should return list of available models

# If Ollama isn't running:
ollama serve
```

## Step 2: Clone & Install

```bash
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant
uv sync
```

## Step 3: Configure

```bash
cp .env.example .env
```

Edit `.env` and set:
```bash
VAULT_PATH=~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud
# Or wherever YOUR Obsidian vault is located
```

That's it. Everything else has sensible defaults.

## Step 4: Ensure Ollama Models

```bash
ollama pull nomic-embed-text
ollama pull llama3.1:8b
```

## Step 5: Start the API

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8765
```

You'll see:
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8765
```

## Step 6: Test It Works

In another terminal:
```bash
curl http://localhost:8765/health
```

Should return:
```json
{
  "status": "ok",
  "index_ready": true,
  "indexed_chunks": 123,
  "vocab_terms": 456
}
```

## Step 7: Query Your Vault

```bash
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"text": "What is my cycling setup?", "mode": "vault"}'
```

Response:
```json
{
  "answer": "You ride a Trek Checkpoint ALR 4 with...",
  "sources": ["Life/Cycling/Cycling.md"],
  "mode": "vault",
  "context_used": 2
}
```

## Use It

### Option A: Siri Shortcuts (iPhone)
See [Siri Integration Guide](docs/SIRI_SHORTCUTS.md)

### Option B: Obsidian Plugin (Desktop)
1. Clone [vault-assistant-obsidian-plugin](../vault-assistant-obsidian-plugin)
2. `npm install && npm run build`
3. Copy to `~/.obsidian/plugins/vault-assistant`
4. Enable in Obsidian settings
5. Point to `http://localhost:8765`

### Option C: Command Line
```bash
# Query with different modes
curl http://localhost:8765/query -d '{"text":"...", "mode":"vault"}' -H "Content-Type: application/json"
curl http://localhost:8765/query -d '{"text":"...", "mode":"general"}' -H "Content-Type: application/json"
curl http://localhost:8765/query -d '{"text":"...", "mode":"technical"}' -H "Content-Type: application/json"
```

## Common Issues

### "VAULT_PATH does not exist"
- Check the path in `.env` is correct
- Use full path: `~/Library/Mobile Documents/...` (with spaces/tildes expanded)
- Not a symlink

### "No models found"
```bash
ollama list
# If empty:
ollama pull nomic-embed-text
ollama pull llama3.1:8b
```

### "Connection refused: http://localhost:11434"
- Ollama not running
- Start it: `ollama serve`
- Or check port isn't already in use

### "Index is empty / index_ready: false"
- Wait 10-30 seconds for initial scan
- Check: `curl http://localhost:8765/index/status`
- Verify vault files exist and are readable

## Next Steps

1. **Set up Siri Shortcuts** for voice queries from iPhone
2. **Install Obsidian plugin** for desktop integration
3. **Read** [Architecture Guide](docs/ARCHITECTURE.md) to understand how it works
4. **Explore** query modes: `vault` (your notes), `general` (world knowledge), `technical` (docs)

## Need Help?

- **Issues**: https://github.com/alexkibler/vault-assistant/issues
- **Setup Problems**: See [Installation Guide](docs/INSTALLATION.md)
- **Advanced Config**: See [Configuration](docs/CONFIGURATION.md)

---

**That's it!** You now have a RAG system querying your personal knowledge base.
