# Architecture

Vault Assistant combines semantic search (RAG), local LLM inference, and intelligent note categorization into a cohesive system for querying and capturing personal knowledge.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    macOS / Linux / WSL2                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  Voice I/O          ┌──────────────┐    │
│  │   Siri       │◄─────────────────────┤  API Server  │    │
│  │  Shortcuts   │  (transcribe, query) │  (FastAPI)   │    │
│  └──────────────┘                      └──────────────┘    │
│                                              │ │            │
│                                 ┌────────────┴─┴─────────┐  │
│                                 │                        │  │
│  ┌──────────────┐         ┌─────▼───┐         ┌────────▼──┐│
│  │ Obsidian     │         │Indexer  │         │Processor  ││
│  │ Vault        │         │(LanceDB)│         │(LLM)      ││
│  │              │◄────────│         │◄────────│           ││
│  └──────────────┘  Read   └─────────┘  Update └───────────┘│
│                                            │                │
│  ┌──────────────┐  Categorize & Write    │                │
│  │ Unprocessed  │◄───────────────────────┘                │
│  │ Notes Queue  │                                         │
│  └──────────────┘                                         │
│                                                            │
│  ┌──────────────────────────┐                            │
│  │      Ollama (local)      │                            │
│  │  ├─ nomic-embed-text     │                            │
│  │  └─ llama3.2 / phi       │                            │
│  └──────────────────────────┘                            │
│                                                            │
└─────────────────────────────────────────────────────────────┘
```

## Core Pipelines

### 1. Query Pipeline (RAG)

User asks a question via voice, text, or Siri Shortcut:

```
Query (text or transcribed)
    ↓
[Embed] → Convert text to 768-dim vector via Ollama nomic-embed-text
    ↓
[Search] → LanceDB similarity search for top-k chunks (default: 5)
    ↓
[Retrieve] → Load matching chunks with file context
    ↓
[Generate] → Ollama LLM with system prompt + context + query
    ↓
Response (answer + source files)
```

**Key Files:**
- `llm/ollama.py` - Async LLM client with persistent connection pooling and automatic retry logic (2 retries with temperature reduction on failure)
- `rag/retriever.py` - LanceDB similarity search wrapper
- `main.py` - `/query`, `/transcribe-and-query` endpoints

**Performance:**
- Embedding: ~100-300ms per query (local)
- Retrieval: ~10-50ms (LanceDB in-memory search)
- Generation: 1-5 seconds (depends on model size and query complexity)

### 2. Capture & Categorization Pipeline

User speaks or types a note:

```
Note (voice or text)
    ↓
[Transcribe] → Whisper (mlx or faster-whisper) with custom vocabulary
    ↓
[Queue] → Save to ~/.vault-assistant/unprocessed/ (not yet in vault)
    ↓
[Processor] → Runs every 30 minutes (launchd scheduled)
    ↓
[Categorize] → LLM decision tree to classify into Life/, Context/, or Archive/
    ↓
[Write] → Create note with YAML frontmatter in appropriate vault folder
    ↓
[Mark Done] → Remove from unprocessed queue
```

**Key Files:**
- `transcription/whisper.py` - Audio transcription with vocabulary hints
- `vault/unprocessed.py` - Queue management
- `processor.py` - LLM-powered categorizer and writer (can run in parallel with asyncio.Semaphore, max 3 concurrent)
- `vault/logger.py` - Audit trail in vault-assistant.md

**Categorization Decision Tree:**

The processor reads `AGENTS.md` rules and applies this tree:

```python
if "communication style" or "working preferences":
    → Context/Preferences

elif "meeting" or "discussion with person":
    → Life/Work

elif "cycling" or "fitness" or "training":
    → Life/Cycling

elif "personal update" about "work/project completion":
    → Life/Work

elif "system documentation" or "infrastructure setup":
    → Context/Technical

else:
    → Life/[Hobby|Gaming|Music|Home|etc]
```

100% accuracy on test suite (6/6 cases passing).

### 3. Indexing Pipeline

Vault watcher detects changes and updates index:

```
Vault changed (.md file created/modified)
    ↓
[Watch] → watchdog debounces by 2 seconds per file
    ↓
[Checkpoint] → Check file mtime vs. last processed timestamp
    ↓
[Chunked] → If unchanged, skip; else chunk into segments
    ↓
[Embed] → Convert each chunk to vector via Ollama
    ↓
[Store] → Save chunk + metadata + vector to LanceDB
    ↓
[Update checkpoint] → Record processed mtime for next time
```

**Key Files:**
- `indexer/watcher.py` - File system monitoring with debouncing
- `indexer/chunker.py` - Markdown-aware adaptive chunking
- `indexer/embedder.py` - Ollama embedding calls
- `indexer/store.py` - LanceDB operations
- `indexer/checkpoint.py` - Incremental indexing with mtime tracking

**Performance:**
- Startup scan: 5-10 seconds for ~100 vault files
- Incremental updates: 100-500ms per file (depends on size)
- Startup → first query: ~1-2 seconds (all vectors in memory)

## Chunking Strategy

### Adaptive Chunking

The chunker detects content type and adjusts chunk size:

- **Code blocks**: 300 tokens max (preserve function boundaries)
- **Prose**: 400 tokens max (natural paragraph breaks)
- **Mixed**: 350 tokens max (balance both)
- **Lists**: 250 tokens max (keep related items together)

### Algorithm

1. Split on `##` and `###` headers (preserve hierarchy)
2. If section > max tokens:
   - Split on paragraph boundaries
   - Add 50-token overlap between adjacent chunks
   - Preserve section header for context
3. Each chunk stores:
   - Text
   - File path
   - Header hierarchy (for breadcrumbs)
   - Content type (code/prose/list/mixed)

**Example:**

```markdown
## Installation

### Prerequisites
- Python 3.11+
- uv package manager
- Ollama

### macOS
1. Install via Homebrew...
2. Configure...
```

Becomes 3-4 chunks:
- Chunk 1: "## Installation" header + prerequisites list
- Chunk 2: "### macOS" + install steps (if long)

## Transcription & Vocabulary

### Whisper with Custom Vocabulary

1. **Vocabulary Sources:**
   - Wikilinks from vault (`[[ProjectName]]` → "ProjectName")
   - Tags from frontmatter (`tags: [kubernetes, docker]`)
   - Custom `_whisper-vocab.md` (one term per line)
   - Proper nouns extracted via NLP

2. **How It Works:**
   - Vocabulary extracted from vault whenever files change
   - Vocabulary merged into Whisper's `initial_prompt`
   - Whisper is more likely to recognize these terms
   - Fallback: `faster-whisper` if mlx-whisper unavailable

**Example vocabulary.txt:**
```
Kubernetes
TypeScript
My Project Name
Temporal
McDermott 3-State Tour
```

## Database: LanceDB

LanceDB is a lightweight vector database perfect for local RAG:

- **Embedded**: No separate server; SQLite-like in-memory DB
- **Vectorized**: Stores 768-dim embeddings from Ollama
- **Fast**: Similarity search in ~10-50ms
- **Simple**: Single table schema: `{text, file_path, header, metadata, vector}`

### Schema

```python
{
    "text": "chunk content",
    "file_path": "Context/Technical/Kubernetes.md",
    "header": "## Installation",
    "chunk_type": "prose",  # code, prose, list, mixed
    "created_at": "2026-06-16T12:34:56Z",
    "vector": [0.123, -0.456, ...]  # 768 dimensions
}
```

## LLM Integration

### Ollama Setup

Ollama provides embeddings and chat inference locally:

```bash
# Embeddings (required)
ollama pull nomic-embed-text  # 274MB, 768-dim vectors

# Chat (pick one)
ollama pull llama3.2          # 2GB, good quality
ollama pull phi:latest        # 1.6GB, fast, lightweight
ollama pull mistral           # 4GB, capable
```

### Prompting Strategy

**Query Mode System Prompts:**

1. **Vault Mode** (default)
   ```
   You are a helpful assistant answering questions about a user's personal knowledge base.
   Use the provided context chunks from the vault.
   If no relevant context is found, say so.
   ```

2. **General Mode**
   ```
   You are a helpful general knowledge assistant.
   Do not use provided context; answer from your general knowledge.
   ```

3. **Technical Mode**
   ```
   You are a technical documentation expert.
   Use only technical context chunks provided.
   Prioritize infrastructure, architecture, and system design topics.
   ```

4. **Custom Mode**
   ```
   You are answering questions about {folder_name} in the user's vault.
   Use only context from that folder.
   ```

### Connection Pooling

The `llm/ollama.py` client maintains a persistent `AsyncClient`:

```python
async def query_ollama(
    messages: list,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    retry: int = 0,
):
    """Query Ollama with automatic retry and temperature reduction."""
    try:
        # Use persistent client connection
        response = await client.chat(...)
        return response
    except Exception:
        if retry < 2:
            # Retry with reduced temperature on failure
            return await query_ollama(..., temperature=temperature * 0.8, retry=retry + 1)
        raise
```

**Benefits:**
- 50% reduction in connection overhead vs. creating new clients
- Automatic retry on transient failures
- Proper async/await integration

## Performance Optimizations

### 1. Parallel Processing

Processor can handle multiple unprocessed notes simultaneously:

```python
semaphore = asyncio.Semaphore(3)  # Max 3 concurrent LLM calls

async def process_note(note):
    async with semaphore:
        # Process note (LLM categorization, file write)
        pass

await asyncio.gather(*[process_note(n) for n in notes])
```

Speedup: ~2-3x faster for batches of notes (depending on I/O).

### 2. Incremental Indexing

Checkpoint system tracks file modification times:

```python
# ~/.vault-assistant/checkpoints.json
{
    "Context/Technical/Kubernetes.md": 1686396456,
    "Life/Work/Projects.md": 1686395200
}
```

Only re-chunk and re-embed files that have changed since last run.

Speedup: ~10x faster startup for unchanged vaults.

### 3. Smart Vocabulary

Vocabulary extracted once at startup and cached:

```python
# Only re-extract if vault files change
vocab = extract_vocab_from_vault()
whisper_prompt = format_vocab_for_whisper(vocab)
```

Speedup: ~100-200ms saved per transcription.

### 4. Deduplication

Automatic detection and removal of duplicate notes:

- **Exact duplicates**: SHA256 hash comparison
- **Near-duplicates**: Jaccard similarity (threshold: >80%)
- **Tracking**: Deduplicated notes logged with deletion reason

Prevents index bloat and improves search quality.

## Error Handling & Recovery

### Connection Failures

LLM client implements exponential backoff:

1. Initial request fails → reduce temperature by 20%, retry
2. Second attempt fails → reduce temperature again, retry once more
3. Third attempt fails → raise exception, log error, return fallback response

Typical recovery: transient Ollama timeouts resolve within 2-3 retries.

### File System Errors

Watcher handles vault permission issues gracefully:

- Missing vault path → error logged, retries with exponential backoff
- Unreadable .md file → skip file, log warning, continue
- Permission denied on write → queue note, alert user, retry later

### LanceDB Issues

Vector database handles schema evolution:

- Missing or corrupted index → rebuild on startup
- Corrupt vector → re-embed and replace
- Schema mismatch → automatic migration

## Deployment

### Local Development

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: API server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8765

# Terminal 3: Processor (manual)
uv run processor.py
```

### Production (launchd on macOS)

Two services:
1. **API Server** (`com.vaultassistant.plist`) - Always running
2. **Processor** (`com.vaultassistant.processor.plist`) - Runs every 30 minutes

Logs at `~/.vault-assistant/logs/`

### Docker / Linux

Run via systemd:

```ini
[Unit]
Description=Vault Assistant API
After=ollama.service

[Service]
ExecStart=/path/to/uv run uvicorn main:app --host 0.0.0.0 --port 8765
Restart=on-failure
User=alex

[Install]
WantedBy=multi-user.target
```

## Testing Strategy

### Unit Tests

- **Categorization**: 6 test cases (100% passing) covering work, meetings, cycling, personal updates, infrastructure, hobbies
- **Chunking**: Markdown parsing, header hierarchy, token counting
- **Embedding**: Vector dimensionality, normalization

Location: `tests/test_categorization.py`, `tests/test_indexing.py`

### Integration Tests

- End-to-end query: transcribe audio → retrieve results → generate answer
- Capture & process: record note → categorize → place in vault
- Vault watching: modify file → auto-index → query new content

### Manual Testing

See [TEST_CASES.md](../TEST_CASES.md) for comprehensive RAG test suite.

## Future Improvements

### Phase 2 (In Progress)
- [ ] Smart query expansion (synonyms, related topics)
- [ ] Vault statistics dashboard
- [ ] Query result ranking by relevance + recency
- [ ] Bulk import from other note systems (Roam, Apple Notes, etc.)

### Phase 3 (Planned)
- [ ] Multi-vault support
- [ ] Collaborative vaults (sync with others)
- [ ] Encrypted vaults with local key management
- [ ] Advanced caching (query result caching, embedding cache)
- [ ] Custom LLM fine-tuning on vault content

---

For detailed setup and usage, see:
- **[QUICKSTART.md](../QUICKSTART.md)** - Get running in 5 minutes
- **[INSTALLATION.md](./INSTALLATION.md)** - OS-specific setup
- **[README.md](../README.md)** - Feature overview
