# Vault Assistant

A voice-driven personal knowledge base system for macOS that combines semantic search (RAG) with intelligent LLM-powered note categorization. Query your Obsidian vault and capture thoughts via voice from your iPhone—everything stays on your machine.

## Features

- 🎙️ **Voice I/O** - Transcribe audio with Whisper, get answers read back via TTS
- 🔍 **Semantic Search** - RAG pipeline with LanceDB vector search + Ollama LLM
- 📝 **Smart Capture** - Voice/text notes auto-categorized to vault with LLM (100% accuracy on test suite)
- 🧠 **Local LLM** - All processing on macOS (Ollama) - zero cloud dependencies
- 📊 **Audit Trail** - Complete processing logs in vault-assistant.md
- ⚡ **Background Service** - launchd automatic processing every 30 minutes
- 🏗️ **Smart Categorization** - Distinguishes between work projects, meetings, infrastructure docs, and personal preferences

## Quick Start (5 Minutes)

**See [QUICKSTART.md](QUICKSTART.md) for step-by-step setup instructions.**

```bash
# 1. Clone
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant

# 2. Install
uv sync

# 3. Configure
cp .env.example .env
# Edit .env and set VAULT_PATH to your vault location

# 4. Start (in Terminal 1)
ollama serve

# 5. Start (in Terminal 2)
uv run uvicorn main:app --host 0.0.0.0 --port 8765

# 6. Test
curl http://localhost:8765/health
```

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[docs/INSTALLATION.md](docs/INSTALLATION.md)** - Setup for macOS, Linux, Windows
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - How it works (RAG, categorization, LLM)
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - 8 major features (parallel processing, caching, etc.)
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute

## Prerequisites

- **macOS 12+** (or Linux/WSL2 via Docker)
- **Python 3.11+**
- **uv** package manager
- **Ollama** (installed and running)
- **Obsidian vault** (iCloud Drive or local)

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

## Note Processing Workflow

### How It Works

1. **Capture**: Voice/text notes are saved to `~/.vault-assistant/unprocessed/` (not directly to vault)
2. **Process**: A scheduled job reads unprocessed notes and:
   - Uses LLM to categorize each note (Life/, Context/, or Archive/)
   - Generates appropriate YAML frontmatter
   - Places note in the correct vault location
   - Marks as processed and removes from queue

### Install Processor Service

The processor runs automatically on a 30-minute schedule:

```bash
cp com.vaultassistant.processor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.vaultassistant.processor.plist
```

### Manual Processing

Run the processor manually anytime:

```bash
uv run processor.py
```

Example output:
```
Found 2 unprocessed note(s).

Processing: 2026-06-16T16-44-09.883950_text_579e6a5f.md
  → Saved to: Context/Technical/Kubernetes Operator Research Notes.md
  ✓ Processed
Processing: 2026-06-16T16-44-18.727715_voice_ca2ddac1.md
  → Saved to: Life/Gaming/Easier Final Boss.md
  ✓ Processed

Processing complete: 2 succeeded, 0 failed
```

### Categorization Rules

The processor reads your `AGENTS.md` vault rules and categorizes notes as:

- **Life/** - Personal goals, projects, decisions, recurring tasks, life events
- **Context/** - Technical infrastructure, preferences, communication style, interests
- **Archive/** - Completed work, historical material, deprecated configs

Within each folder, it creates subfolders like Projects, Goals, Technical, Preferences, etc.

### View Processing Logs

```bash
tail -f ~/.vault-assistant/logs/processor-stdout.log
tail -f ~/.vault-assistant/logs/processor-stderr.log
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
```
Response:
```json
{
  "transcription": "remember to review quarterly goals",
  "saved_to": "2026-06-16T16-44-18.727715_voice_ca2ddac1.md",
  "status": "pending_processing"
}
```

Note: Audio is transcribed and saved to the unprocessed queue. The processor will categorize and place it in the vault based on content (Life/, Context/, or Archive/).

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
  "text": "update: finished the design review"
}
```
Response:
```json
{
  "saved_to": "2026-06-16T16-44-09.883950_text_579e6a5f.md",
  "status": "pending_processing"
}
```

Note: Text is saved to the unprocessed queue. The processor will categorize and place it in the vault based on content (Life/, Context/, or Archive/).

## Testing

### Test Results

**Capture/Categorization Tests: 6/6 Passing (100%)** ✅

The system correctly categorizes captured notes:
- Work project updates → `Life/Work`
- Work meetings → `Life/Work`
- Cycling/fitness → `Life/Cycling`
- Technical infrastructure → `Context/Technical`
- Communication preferences → `Context/Preferences`

See [CAPTURE_AUDIT_RESULTS.md](CAPTURE_AUDIT_RESULTS.md) for detailed test analysis.

### Run Tests Locally

**Capture Tests:**
```bash
# Terminal 1: Start API
uv run uvicorn main:app --host 0.0.0.0 --port 8765

# Terminal 2: Run captures
bash /tmp/test_capture.sh

# Terminal 3: Process notes
uv run processor.py

# Verify results
ls ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud/Life/Work/
ls ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud/Context/*/
```

**Query Tests:**
See [TEST_CASES.md](TEST_CASES.md) for comprehensive RAG test suite covering:
- Specific technical queries
- Vague project references
- Architecture patterns
- Meeting notes
- Edge cases and synonyms

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

### "Capture to Vault"

Captures voice memos for automatic processing and categorization.

**Steps:**

1. Open Shortcuts app → Create new shortcut
2. Add action: **Ask for Audio**
   - Duration: 10 seconds
3. Add action: **Get Contents of URL**
   - URL: `http://[your-mac-tailscale-ip]:8765/transcribe-and-capture`
   - Method: POST
   - Request Body: **Form**
   - Add field: Name = `audio`, File = the audio from step 2
4. Add action: **Get Dictionary Value**
   - Key: `transcription`
   - Dictionary: result from step 3
5. Add action: **Show Notification**
   - Body: the transcription value

**Workflow:**
- Audio is transcribed immediately
- Note is saved to processing queue (`~/.vault-assistant/unprocessed/`)
- Processor runs every 30 minutes and auto-categorizes it into your vault
- You get a confirmation with the transcription right away
- Note appears in appropriate vault folder (Life/, Context/, or Archive/) within 30 minutes

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

## Categorization Logic

The processor uses a decision tree to categorize notes with 100% accuracy on the test suite:

```
1. Is this about communication style or working preferences?
   → Context/Preferences
   Examples: "I prefer concise responses", "Use uv for package management"

2. Is this a meeting or discussion with another person?
   → Life/Work
   Examples: "Meeting with Mark about infrastructure", "Discussion on design"

3. Is this about cycling, training, or fitness?
   → Life/Cycling
   Examples: "Upgraded to 2x drivetrain", "McDermott 3-State Tour results"

4. Is this a personal update about work/project completion?
   → Life/Work
   Examples: "Finished vendor module DI pattern implementation"

5. Is this system documentation or infrastructure setup (not a personal update)?
   → Context/Technical
   Examples: "Ollama configuration guide", "Docker compose setup"

6. Is this about a personal hobby or interest?
   → Life/[Cycling|Gaming|Music|Home|etc]
```

## Project Structure

```
vault-assistant/
├── main.py                 # FastAPI app (6 endpoints)
├── processor.py            # LLM-powered categorizer (runs via launchd)
├── config.py               # Environment configuration
│
├── indexer/               # Vector indexing pipeline
│   ├── chunker.py         # Markdown-aware chunking (400 token max)
│   ├── embedder.py        # Ollama embedding calls
│   ├── store.py           # LanceDB vector operations
│   └── watcher.py         # File system monitoring (watchdog)
│
├── transcription/         # Audio processing
│   ├── whisper.py         # faster-whisper transcription
│   └── vocab.py           # Vocab builder for Whisper
│
├── rag/
│   └── retriever.py       # LanceDB semantic search
│
├── llm/
│   └── ollama.py          # Ollama API wrapper
│
├── vault/
│   ├── unprocessed.py     # Note queue manager
│   ├── logger.py          # Markdown audit logging
│   └── writer.py          # (Unused) Direct vault writing
│
├── .github/workflows/      # CI/CD pipelines
│   ├── test.yml           # Lint and type check
│   └── scheduled.yml      # Nightly test runs
│
├── com.vaultassistant.plist              # launchd service (API)
├── com.vaultassistant.processor.plist    # launchd service (processor)
│
├── TEST_CASES.md          # Query endpoint test suite
├── TEST_CAPTURE_CASES.md  # Capture endpoint test cases
├── CAPTURE_AUDIT_RESULTS.md  # Test results and analysis
├── pyproject.toml         # Dependencies (uv)
├── .env.example           # Configuration template
└── README.md              # This file
```

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
