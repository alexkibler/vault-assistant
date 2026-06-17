import asyncio
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
from rag.retriever import retrieve, retrieve_optimized
from rag.query_decomposer import decompose_query, retrieve_with_decomposition
from llm.ollama import chat_completion, close_ollama_client
from llm.conversation import (
    create_conversation,
    add_message,
    get_conversation_history,
    get_conversation_context,
    cleanup_old_conversations,
)
from vault.unprocessed import save_unprocessed_note


# Request models
class QueryRequest(BaseModel):
    text: str
    top_k: int = 5
    mode: str = "vault"  # "vault" (RAG), "general" (no context), "technical", "custom"
    context_folder: str | None = None  # For "custom" mode
    conversation_id: str | None = None  # Track conversation thread
    is_followup: bool = False  # Mark as follow-up question


class CaptureRequest(BaseModel):
    text: str
    target: str = "daily"


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

    # Start watchdog observer with current event loop
    loop = asyncio.get_event_loop()
    observer = start_watcher(_on_vault_file_change, loop)
    print("Vault watcher started")

    yield

    # Shutdown
    if observer:
        observer.stop()
        observer.join()
    print("Vault watcher stopped")

    # Close Ollama client connection pool
    await close_ollama_client()
    print("Ollama client closed")


app = FastAPI(
    title="Vault Assistant",
    description="Voice-driven personal knowledge base backend",
    lifespan=lifespan,
)

# Add CORS middleware to allow requests from Obsidian plugin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


def _is_compound_question(query: str) -> bool:
    """Detect if query has multiple parts (who AND what, etc)."""
    compound_patterns = [
        r"\band\b",  # "who and what"
        r"\bthen\b",  # "first do this then"
        r",\s*and\s",  # "X, and Y"
        r"\?.*\?",  # "question? question?"
    ]
    return len(query) > 40 and any(re.search(p, query.lower()) for p in compound_patterns)


async def _query_vault(
    query_text: str,
    top_k: int = 5,
    mode: str = "vault",
    context_folder: str | None = None,
    conversation_history: dict | None = None,
) -> dict:
    """Shared logic for querying with different modes.

    Args:
        query_text: User's query
        top_k: Number of context chunks to retrieve
        mode: Query mode - "vault" (RAG), "general" (no context), "technical", "custom"
        context_folder: For "custom" mode, which vault folder to search
        conversation_history: Dict with conversation_id for follow-up context

    Returns:
        Dictionary with answer and sources
    """
    # Detect compound questions and increase context
    is_compound = _is_compound_question(query_text)
    effective_top_k = top_k * 2 if is_compound else top_k  # Double context for compound Q

    # Determine system prompt based on mode
    if mode == "general":
        system_prompt = (
            "You are a helpful AI assistant with general knowledge. "
            "Provide accurate, concise answers. Keep responses under 3 sentences unless "
            "the user asks for more detail."
        )
        context_chunks = []

    elif mode == "technical":
        system_prompt = (
            "You are a technical assistant with access to the user's technical documentation. "
            "Answer based on the technical context. Be precise and include implementation details. "
            "If context is missing, say so."
        )
        context_chunks = await retrieve(query_text, top_k)
        # Filter to technical context only (optional enhancement)

    elif mode == "custom" and context_folder:
        system_prompt = (
            f"You are an assistant with access to the user's {context_folder} notes. "
            "Answer based on the retrieved context. Be concise."
        )
        context_chunks = await retrieve(query_text, top_k)
        # In production, filter to context_folder (requires retriever enhancement)

    else:  # mode == "vault" (default)
        # Enhanced synthesis for compound questions
        if is_compound:
            system_prompt = (
                "You are a personal assistant synthesizing information from multiple notes. "
                "The user is asking about multiple topics. Answer ALL parts of their question. "
                "Use the retrieved context to comprehensively address each part. "
                "Be clear about what you found for each part. Keep total response under 4 sentences unless more detail requested."
            )
        else:
            system_prompt = (
                "You are a personal assistant with access to the user's private knowledge base. "
                "Answer based on the retrieved context below. Be concise — the user is listening "
                "via AirPods. Keep responses under 3 sentences unless the user explicitly asks "
                "for detail. If the context does not contain the answer, say so briefly."
            )

        # Use decomposition for compound questions
        if is_compound:
            try:
                decomp_result = await retrieve_with_decomposition(query_text, retrieve_optimized, top_k=effective_top_k)
                context_chunks = decomp_result["results"]
                # Add decomposition info to system prompt for better synthesis
                system_prompt += f"\n\n[Note: Question decomposed into: {', '.join(decomp_result['sub_questions'])}]"
            except Exception as e:
                print(f"Decomposition retrieval failed: {e}, using optimized retrieval")
                try:
                    context_chunks = await retrieve_optimized(query_text, effective_top_k)
                except Exception as e2:
                    print(f"Optimized retrieval also failed: {e2}, falling back to basic")
                    context_chunks = await retrieve(query_text, effective_top_k)
        else:
            # Use optimized retrieval for simple questions
            try:
                context_chunks = await retrieve_optimized(query_text, top_k)
            except Exception as e:
                # Fallback to basic retrieval if optimization fails
                print(f"Optimized retrieval failed: {e}, falling back to basic retrieval")
                context_chunks = await retrieve(query_text, top_k)

    # Inject conversation context if follow-up
    final_user_message = query_text
    if conversation_history:
        conv_context = get_conversation_context(conversation_history.get("conversation_id", ""))
        if conv_context:
            final_user_message = f"{conv_context}\n\nNew question: {query_text}"

    answer = await chat_completion(system_prompt, final_user_message, context_chunks)
    sources = [chunk["file_path"] for chunk in context_chunks] if context_chunks else []

    # Store message in conversation history
    conversation_id = conversation_history.get("conversation_id") if conversation_history else None
    if conversation_id:
        add_message(conversation_id, "user", query_text, metadata={"sources": sources})
        add_message(
            conversation_id,
            "assistant",
            answer,
            metadata={"sources": sources, "context_used": len(context_chunks)},
        )
    else:
        # Create new conversation for tracking
        conversation_id = create_conversation()
        add_message(conversation_id, "user", query_text, metadata={"sources": sources})
        add_message(
            conversation_id,
            "assistant",
            answer,
            metadata={"sources": sources, "context_used": len(context_chunks)},
        )

    return {
        "answer": answer,
        "sources": sources,
        "mode": mode,
        "context_used": len(context_chunks),
        "conversation_id": conversation_id,  # Return for follow-ups
    }


async def _capture_note(text: str, source: str = "text") -> dict:
    """Shared logic for capturing notes to the unprocessed queue."""
    filename = save_unprocessed_note(text, source=source)
    return {
        "saved_to": filename,
        "status": "pending_processing",
    }


@app.post("/transcribe-and-query")
async def transcribe_and_query(
    audio: UploadFile = File(...),
    top_k: int = Form(5),
    mode: str = Form("vault"),
    context_folder: str | None = Form(None),
):
    """Transcribe audio and query the vault for answers.

    Args:
        audio: Audio file to transcribe
        top_k: Number of context chunks (for vault/technical modes)
        mode: Query mode - "vault" (RAG), "general", "technical", "custom"
        context_folder: For "custom" mode, which vault folder to search
    """
    try:
        audio_bytes = await audio.read()
        content_type = audio.content_type or "audio/mp4"

        # Transcribe
        transcription = await transcribe_audio(audio_bytes, content_type)

        # Query vault
        query_result = await _query_vault(transcription, top_k, mode, context_folder)

        return {
            "transcription": transcription,
            **query_result,
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/transcribe-and-capture")
async def transcribe_and_capture(
    audio: UploadFile = File(...),
):
    """Transcribe audio and save to unprocessed notes."""
    try:
        audio_bytes = await audio.read()
        content_type = audio.content_type or "audio/mp4"

        # Transcribe
        transcription = await transcribe_audio(audio_bytes, content_type)

        # Capture note
        capture_result = await _capture_note(transcription, source="voice")

        return {
            "transcription": transcription,
            **capture_result,
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/query")
async def query(req: QueryRequest):
    """Query with different modes (text-only).

    Query modes:
    - vault: RAG queries against your knowledge base (default)
    - general: General knowledge without vault context
    - technical: Technical documentation queries
    - custom: Specific folder queries (specify context_folder)

    Conversation support:
    - conversation_id: ID for multi-turn conversation (returned in response)
    - is_followup: Mark as follow-up to use previous context

    Example:
        {"text": "How do I configure Ollama?", "mode": "technical", "top_k": 5}
        Follow-up: {"text": "And what about that setting?", "conversation_id": "uuid", "is_followup": true}
    """
    try:
        conversation_info = None
        if req.conversation_id or req.is_followup:
            conversation_info = {
                "conversation_id": req.conversation_id or create_conversation(),
                "is_followup": req.is_followup,
            }

        return await _query_vault(
            req.text,
            req.top_k,
            req.mode,
            req.context_folder,
            conversation_history=conversation_info,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/capture")
async def capture(req: CaptureRequest):
    """Capture text to unprocessed notes."""
    try:
        return await _capture_note(req.text, source="text")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=Config.SERVICE_HOST,
        port=Config.SERVICE_PORT,
    )
