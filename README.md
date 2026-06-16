# Vault Assistant

Voice-driven personal knowledge base backend for macOS. Transcribe voice queries and notes from your iPhone, retrieve answers from an Obsidian vault via RAG, and capture thoughts back to your vault—all with Siri Shortcuts.

## Features

- **Voice Transcription**: Whisper on Apple Silicon (mlx-whisper) with custom vocabulary from your vault
- **Semantic Search**: Vector embeddings via Ollama (nomic-embed-text) stored in LanceDB
- **RAG Generation**: LLM-powered answers from your vault context (Ollama)
- **Vault Indexing**: Automatic file watching and markdown-aware chunking
- **Vault Capture**: Save transcribed thoughts to daily notes or inbox
- **Text API**: Pure text endpoints for programmatic access
- **launchd Service**: Native macOS background service (no Docker)

## Prerequisites

- macOS 12+ (tested on Mac mini M4)
- Ollama installed: `brew install ollama`
- Models pulled:
  ```bash
  ollama pull nomic-embed-text
  ollama pull llama3.2
  ```
- `uv` package manager: `brew install uv`
- Obsidian vault synced to iCloud Drive (vault path must exist locally)

## Setup

```bash
cd /Volumes/1TB/Repos/vault-assistant
cp .env.example .env
# Edit .env — set VAULT_PATH to your actual vault path
uv sync
```

## Verify Installation

```bash
curl http://localhost:8765/health
```

Expected response (assuming Ollama is running):
```json
{
  "status": "ok",
  "index_ready": false,
  "indexed_chunks": 0,
  "vocab_terms": 0
}
```

The `index_ready` flag will turn true after the first full vault scan completes (usually within seconds for small vaults).

## Launch as Service

Install the launchd plist to run vault-assistant at login:

```bash
mkdir -p ~/.vault-assistant/logs
cp com.vaultassistant.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.vaultassistant.plist
```

Verify the service is running:
```bash
launchctl list | grep vault
```

View logs:
```bash
tail -f ~/.vault-assistant/logs/stdout.log
```

To stop:
```bash
launchctl unload ~/Library/LaunchAgents/com.vaultassistant.plist
```

## API Endpoints

### Health Check
```bash
GET /health
```
Response:
```json
{
  "status": "ok",
  "index_ready": bool,
  "indexed_chunks": int,
  "vocab_terms": int
}
```

### Index Status
```bash
GET /index/status
```
Response:
```json
{
  "total_files": int,
  "total_chunks": int,
  "last_updated": "2026-06-16T...",
  "pending_files": int
}
```

### Transcribe & Query
```bash
POST /transcribe-and-query
Content-Type: multipart/form-data

audio: <file>     # m4a, wav, mp3, etc.
top_k: 5          # (optional) number of context chunks to retrieve
```
Response:
```json
{
  "transcription": "what is my project timeline",
  "answer": "Your project timeline...",
  "sources": ["Projects/MyProject.md"]
}
```

### Transcribe & Capture
```bash
POST /transcribe-and-capture
Content-Type: multipart/form-data

audio: <file>      # m4a, wav, mp3, etc.
target: "daily"    # or "inbox" (optional, default "daily")
```
Response:
```json
{
  "transcription": "remember to review quarterly goals",
  "written_to": "2026-06-16.md"
}
```

### Text Query
```bash
POST /query
Content-Type: application/json

{
  "text": "what did I note about performance tuning",
  "top_k": 5
}
```
Response:
```json
{
  "answer": "You noted that...",
  "sources": ["Technical/Performance.md"]
}
```

### Text Capture
```bash
POST /capture
Content-Type: application/json

{
  "text": "update: finished the design review",
  "target": "daily"
}
```
Response:
```json
{
  "written_to": "2026-06-16.md"
}
```

## Siri Shortcuts Setup

### "Ask My Vault"

Creates a shortcut to ask questions and listen to answers.

**Steps:**

1. Open Shortcuts app → Create new shortcut
2. Add action: **Ask for Audio**
   - Set Stop Listening to "Automatically after silence"
   - Duration: 10 seconds (adjust to preference)
3. Add action: **Get Contents of URL**
   - URL: `http://[your-mac-tailscale-ip]:8765/transcribe-and-query`
   - Method: POST
   - Request Body: **Form**
   - Add field: Name = `audio`, File = the audio from step 2
4. Add action: **Get Dictionary Value**
   - Key: `answer`
   - Dictionary: result from step 3
5. Add action: **Speak Text**
   - Text: the value from step 4

**Tip**: Replace the URL with your Mac's Tailscale IP for on-the-go access. Find it via `tailscale ip` on your Mac.

### "Note to Vault"

Captures voice memos to your daily note.

**Steps:**

1. Open Shortcuts app → Create new shortcut
2. Add action: **Ask for Audio**
   - Duration: 10 seconds
3. Add action: **Get Contents of URL**
   - URL: `http://[your-mac-tailscale-ip]:8765/transcribe-and-capture`
   - Method: POST
   - Request Body: **Form**
   - Add field: Name = `audio`, File = the audio from step 2
   - Add field: Name = `target`, Text = `daily`
4. Add action: **Get Dictionary Value**
   - Key: `transcription`
   - Dictionary: result from step 3
5. Add action: **Show Notification**
   - Body: the transcription value

Both shortcuts can be pinned to Siri by setting a voice phrase. Then you can invoke them with "Hey Siri, [shortcut name]" with your phone in your pocket.

## Custom Whisper Vocabulary

To improve transcription accuracy for domain-specific terms, names, and project names:

1. Create `_whisper-vocab.md` in your vault root
2. Add one term per line:
   ```
   Kubernetes
   TypeScript
   My Project Name
   Temporal
   ```

The vocabulary is automatically refreshed when any file in the vault changes.

## Architecture Notes

### Indexing

- **Startup**: Scans vault for `.md` files, chunks each using markdown headers and paragraph boundaries
- **File Watching**: `watchdog` monitors the vault directory; changes debounced by 2 seconds per file
- **Chunking**: Splits on `##` and `###` headers; sections over 400 tokens are split on paragraphs with 50-token overlap
- **Embeddings**: Each chunk is sent to Ollama's `nomic-embed-text` model (768-dim vectors)
- **Storage**: LanceDB (embedded SQLite-like vector DB) stores metadata, text, and embeddings

### Transcription

- **Primary**: `mlx-whisper` for on-device inference on Apple Silicon
- **Fallback**: `faster-whisper` with CPU if mlx not available
- **Vocabulary**: Wikilinks, tags, aliases, proper nouns, and custom `_whisper-vocab.md` terms are passed as Whisper's `initial_prompt`

### RAG

1. User query (text or transcribed) → embed via Ollama
2. LanceDB similarity search retrieves top-k chunks
3. Ollama `/api/chat` endpoint with system prompt + context chunks + query
4. Response streamed back to client

### Vault Writing

- **Daily Notes**: `{DAILY_NOTE_FORMAT}.md` (default: `2026-06-16.md`) with timestamped entries
- **Inbox**: `{INBOX_FILE}` (default: `inbox.md`) with ISO datetime stamps

## Troubleshooting

### Index is empty
Ensure Ollama is running and models are pulled:
```bash
ollama serve  # in one terminal
ollama list   # in another; should show nomic-embed-text and your chat model
```

### Transcription fails
- Check Content-Type header from iOS Shortcuts (should be `audio/mp4`, `audio/mpeg`, etc.)
- Verify Whisper model is available: `huggingface-cli scan-cache` for mlx models
- Fallback to `faster-whisper` if mlx errors

### Service won't start
Check logs:
```bash
cat ~/.vault-assistant/logs/stderr.log
```
Common issues:
- `VAULT_PATH` doesn't exist or typo in `.env`
- Ollama not running on `OLLAMA_BASE_URL`
- LanceDB path permissions issue

### High memory usage
- LanceDB keeps the index in memory; for very large vaults (10k+ chunks), consider reducing `top_k` in API calls
- Ollama model size: `llama3.2` is ~2GB; use `phi:latest` (~1.6GB) for lighter inference

## Development

Run locally without launchd:
```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8765
```

Test endpoints:
```bash
curl -X POST http://localhost:8765/capture \
  -H "Content-Type: application/json" \
  -d '{"text": "test entry", "target": "daily"}'
```

## License

Personal use. Customize freely for your own vault.
