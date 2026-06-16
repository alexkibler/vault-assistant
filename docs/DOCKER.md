# Docker Setup

Run vault-assistant in Docker containers. Ollama and Whisper remain on your host machine for hardware acceleration.

## Architecture

```
Host Machine
├── Ollama (GPU accelerated)
├── Whisper (hardware accelerated, mlx-whisper on Apple Silicon)
└── Vault (iCloud Drive or local folder)

Docker Network
├── vault-assistant-api (FastAPI server, port 8765)
└── vault-assistant-processor (note categorization service)
```

**Why this setup?**
- Ollama needs GPU access (CUDA, AMD ROCm, Apple Metal)
- Whisper benefits from hardware acceleration (mlx on Apple Silicon)
- Vault stays on host for seamless Obsidian integration
- All vault-assistant code runs in containers for isolation and repeatability

## Prerequisites

### 1. Ollama on Host

```bash
# Install Ollama if not already installed
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve  # Start Ollama (runs on port 11434)
```

Pull required models in another terminal:

```bash
ollama pull nomic-embed-text  # Required for embeddings
ollama pull llama3.2          # Or phi, mistral, etc.
```

### 2. Whisper on Host (Optional)

If you want voice transcription, install on your machine:

```bash
# macOS with Apple Silicon (mlx-whisper for hardware acceleration)
pip install mlx-whisper
# OR faster-whisper (CPU fallback)
pip install faster-whisper
```

### 3. Docker & Docker Compose

```bash
# macOS: Install Docker Desktop
# https://www.docker.com/products/docker-desktop

# Linux/WSL2
apt-get install docker.io docker-compose
systemctl start docker
```

### 4. Vault Location

Your Obsidian vault can be:
- **iCloud Drive** (macOS): `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/iCloud`
- **Local folder**: Anywhere on your machine
- **Network share**: NFS/SMB mounted locally

## Setup

### 1. Create .env File

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
# Required: your vault path
VAULT_PATH=/Users/alex/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud

# Optional: where to find Ollama (default: host.docker.internal:11434 on Docker Desktop)
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### 2. Build Docker Images

```bash
docker compose build
```

### 3. Start Services

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f api
docker compose logs -f processor
```

### 4. Verify Setup

```bash
# Health check
curl http://localhost:8765/health

# Should return:
# {"status": "ok", "index_ready": false, "indexed_chunks": 0, "vocab_terms": 0}

# Wait ~30 seconds for vault indexing...
curl http://localhost:8765/index/status
```

## Vault Path Setup

### macOS with iCloud Drive

The tricky part: iCloud Drive syncing and Docker file access.

**Safe approach:** Read-only vault access in API container, write access in processor only.

```bash
# .env
VAULT_PATH=/Users/alex/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud
```

**Why only processor writes?**
- API only reads vault for searching (read-only in docker-compose.yml)
- Processor writes new categorized notes
- Reduces iCloud sync conflicts from multiple processes

**If you get permission errors:**

```bash
# Grant Docker Desktop file sharing permission:
# Docker Desktop → Preferences → Resources → File Sharing
# Add: /Users/alex/Library/Mobile Documents/iCloud~md~obsidian
```

### Local Vault Folder

Simplest for testing:

```bash
# Create a local vault
mkdir -p ~/my-vault/Life ~/my-vault/Context ~/my-vault/Archive

# .env
VAULT_PATH=/Users/alex/my-vault
```

### Network Vault (NFS/SMB)

If vault is on a NAS or server:

```bash
# Mount locally first (macOS example)
mkdir -p /Volumes/vault-share
mount_nfs -o resvport nserver.local:/share/vault /Volumes/vault-share

# .env
VAULT_PATH=/Volumes/vault-share
```

## Running

### One-Time Setup

```bash
# Start services
docker compose up -d

# View API logs
docker compose logs -f api

# View processor logs
docker compose logs -f processor
```

### Daily Usage

Services run in background automatically:

```bash
# Check status
docker compose ps

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

### Query the API

```bash
# Health check
curl http://localhost:8765/health

# Text query
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What did I note about Kubernetes?",
    "top_k": 5,
    "mode": "vault"
  }'

# Transcribe audio (from Siri Shortcut or curl)
curl -X POST http://localhost:8765/transcribe-and-query \
  -F "audio=@voice-note.m4a" \
  -F "mode=vault"
```

## iCloud Drive Considerations

### The Problem

iCloud Drive on macOS:
- Syncs files in background
- Optimizes storage (some files offline)
- Can conflict if multiple processes access simultaneously

### The Solution

1. **API container** (queries): Read-only mount
   - Searches vault files
   - No writes, no sync conflicts

2. **Processor container** (writes): Read-write mount
   - Adds new categorized notes
   - Separate from query operations

3. **Host Obsidian**: Direct filesystem access
   - Edits notes normally
   - iCloud syncs seamlessly

### Troubleshooting iCloud Issues

**"Permission denied" errors:**
```bash
# Grant Docker Desktop file sharing permission
# Docker Desktop → Preferences → Resources → File Sharing
# Add your vault's parent directory

# Example: if vault is at ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/iCloud
# Grant access to: ~/Library/Mobile Documents/
```

**"File not found" (offline files):**
```bash
# Force iCloud to download vault files
# macOS: System Preferences → iCloud → Options... → Optimize Mac Storage (OFF)
# Or: iCloud menu → Download Now for vault folder
```

**Sync conflicts / duplicate files:**
```bash
# Monitor iCloud status
ls -la ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud/ | grep conflicted

# Clean up if needed, then restart processor:
docker compose restart processor
```

## Advanced Options

### Logs Volume

Processor logs are saved to a Docker volume:

```bash
# View processor logs
docker compose logs processor

# Or access volume directly
docker inspect vault-assistant-logs
```

### Custom Ollama Endpoint

If Ollama runs on a different machine:

```bash
# .env
OLLAMA_BASE_URL=http://192.168.1.50:11434
```

### Linux / WSL2 Specifics

On WSL2, `host.docker.internal` maps to the Windows host:

```bash
# If Ollama runs on Windows host
OLLAMA_BASE_URL=http://host.docker.internal:11434

# If Ollama runs inside WSL2 Linux container
OLLAMA_BASE_URL=http://ollama:11434  # Requires docker network setup
```

### Resource Limits

By default, Docker uses available system resources. Customize in docker-compose.yml:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 4G
        reservations:
          cpus: "2"
          memory: 2G
```

## Troubleshooting

### "Cannot connect to Ollama"

```bash
# Verify Ollama is running on host
ollama list

# Check if API can reach it
docker compose exec api curl http://host.docker.internal:11434/api/tags
```

### "Permission denied: /vault"

```bash
# Grant Docker file sharing (macOS)
# Docker Desktop → Preferences → Resources → File Sharing
# Or give full disk access to Docker Desktop
# System Preferences → Security & Privacy → Full Disk Access → Docker.app
```

### "LanceDB index corrupted"

```bash
# Rebuild index
docker volume rm vault-assistant-lancedb
docker compose restart api
# Wait ~30 seconds for re-indexing
```

### "Processor not saving notes"

```bash
# Check processor logs
docker compose logs processor

# Check vault permissions
ls -la /vault/Life/

# Verify vault path in .env
grep VAULT_PATH .env
```

## Clean Up

```bash
# Stop and remove containers
docker compose down

# Remove all data (volumes)
docker compose down -v

# Remove images
docker rmi vault-assistant
```

## Next Steps

- See [QUICKSTART.md](../QUICKSTART.md) for usage examples
- See [INSTALLATION.md](./INSTALLATION.md) for non-Docker setup
- See [ARCHITECTURE.md](./ARCHITECTURE.md) for how it works internally
