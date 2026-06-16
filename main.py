import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

from config import Config
from indexer.chunker import chunk_markdown
from indexer.embedder import embed_text
from indexer.store import (
    upsert_chunks,
    delete_chunks,
    get_chunk_count,
    get_file_mtime,
)
from indexer.watcher import start_watcher
from transcription.vocab import build_vocab_cache, get_vocab
from transcription.whisper import transcribe_audio
from rag.retriever import retrieve
from llm.ollama import chat_completion
from vault.writer import write_to_vault

# Global state
index_ready = False
observer = None
last_index_update = None
total_files = 0
pending_files = 0


async def _perform_full_index_scan():
    """Perform full scan of vault and index all markdown files."""
    global index_ready, last_index_update, total_files

    print("Starting full vault index scan...")
    total_files = 0
    indexed_count = 0

    for md_file in Config.VAULT_PATH.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue

        total_files += 1
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            modified_at = md_file.stat().st_mtime

            # Check if already indexed and unchanged
            old_mtime = await get_file_mtime(md_file)
            if old_mtime == modified_at:
                indexed_count += 1
                continue

            # Chunk and embed
            chunks = chunk_markdown(md_file, content)
            if not chunks:
                indexed_count += 1
                continue

            embeddings = [await embed_text(chunk["text"]) for chunk in chunks]
            await upsert_chunks(md_file, chunks, embeddings, modified_at)
            indexed_count += 1

        except Exception as e:
            print(f"Error indexing {md_file}: {e}")

    last_index_update = datetime.now().isoformat()
    index_ready = True
    print(f"Index scan complete: {indexed_count}/{total_files} files indexed")


async def _on_vault_file_change(file_path: Path):
    """Handle vault file change event."""
    global last_index_update

    try:
        if not file_path.exists():
            # File was deleted
            await delete_chunks(file_path)
        else:
            # File was created or modified
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            modified_at = file_path.stat().st_mtime

            chunks = chunk_markdown(file_path, content)
            if chunks:
                embeddings = [await embed_text(chunk["text"]) for chunk in chunks]
                await upsert_chunks(file_path, chunks, embeddings, modified_at)
            else:
                await delete_chunks(file_path)

        # Rebuild vocab cache
        build_vocab_cache()
        last_index_update = datetime.now().isoformat()

    except Exception as e:
        print(f"Error processing vault change {file_path}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup and shutdown."""
    global observer, index_ready

    # Startup
    Config.validate()
    print(f"Vault path: {Config.VAULT_PATH}")
    print(f"LanceDB path: {Config.LANCEDB_PATH}")

    # Start full index scan in background
    asyncio.create_task(_perform_full_index_scan())

    # Start watchdog observer
    observer = start_watcher(_on_vault_file_change)
    print("Vault watcher started")

    yield

    # Shutdown
    if observer:
        observer.stop()
        observer.join()
    print("Vault watcher stopped")


app = FastAPI(
    title="Vault Assistant",
    description="Voice-driven personal knowledge base backend",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    chunk_count = await get_chunk_count()
    vocab_terms = len(get_vocab().split(",")) if get_vocab() else 0
    return {
        "status": "ok",
        "index_ready": index_ready,
        "indexed_chunks": chunk_count,
        "vocab_terms": vocab_terms,
    }


@app.get("/index/status")
async def index_status():
    """Get indexing status."""
    chunk_count = await get_chunk_count()
    return {
        "total_files": total_files,
        "total_chunks": chunk_count,
        "last_updated": last_index_update,
        "pending_files": pending_files,
    }


@app.post("/transcribe-and-query")
async def transcribe_and_query(audio: UploadFile = File(...), top_k: int = Form(5)):
    """Transcribe audio and query the vault for answers."""
    try:
        audio_bytes = await audio.read()
        content_type = audio.content_type or "audio/mp4"

        # Transcribe
        transcription = await transcribe_audio(audio_bytes, content_type)

        # Retrieve context
        context_chunks = await retrieve(transcription, top_k)

        # Generate answer
        system_prompt = (
            "You are a personal assistant with access to the user's private knowledge base. "
            "Answer based on the retrieved context below. Be concise — the user is listening "
            "via AirPods. Keep responses under 3 sentences unless the user explicitly asks "
            "for detail. If the context does not contain the answer, say so briefly."
        )
        answer = await chat_completion(system_prompt, transcription, context_chunks)

        sources = [chunk["file_path"] for chunk in context_chunks]

        return {
            "transcription": transcription,
            "answer": answer,
            "sources": sources,
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/transcribe-and-capture")
async def transcribe_and_capture(
    audio: UploadFile = File(...),
    target: str = Form("daily"),
):
    """Transcribe audio and write to vault."""
    try:
        audio_bytes = await audio.read()
        content_type = audio.content_type or "audio/mp4"

        # Transcribe
        transcription = await transcribe_audio(audio_bytes, content_type)

        # Write to vault
        written_path = await write_to_vault(transcription, target)

        return {
            "transcription": transcription,
            "written_to": written_path,
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/query")
async def query(text: str, top_k: int = 5):
    """Query the vault (text-only)."""
    try:
        # Retrieve context
        context_chunks = await retrieve(text, top_k)

        # Generate answer
        system_prompt = (
            "You are a personal assistant with access to the user's private knowledge base. "
            "Answer based on the retrieved context below. Be concise — the user is listening "
            "via AirPods. Keep responses under 3 sentences unless the user explicitly asks "
            "for detail. If the context does not contain the answer, say so briefly."
        )
        answer = await chat_completion(system_prompt, text, context_chunks)

        sources = [chunk["file_path"] for chunk in context_chunks]

        return {
            "answer": answer,
            "sources": sources,
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/capture")
async def capture(text: str, target: str = "daily"):
    """Capture text to vault (no processing)."""
    try:
        written_path = await write_to_vault(text, target)
        return {"written_to": written_path}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=Config.SERVICE_HOST,
        port=Config.SERVICE_PORT,
    )
