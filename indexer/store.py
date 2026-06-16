import asyncio
import hashlib
import lancedb
import pyarrow as pa
from pathlib import Path
from config import Config


# Global database reference
_db = None
_table = None


def _get_db():
    """Get or initialize LanceDB connection (sync context)."""
    global _db, _table
    if _db is None:
        _db = lancedb.connect(str(Config.LANCEDB_PATH))

        # Create table if not exists
        if "vault_chunks" not in _db.table_names():
            schema = pa.schema(
                [
                    pa.field("id", pa.string()),
                    pa.field("file_path", pa.string()),
                    pa.field("title", pa.string()),
                    pa.field("chunk_text", pa.string()),
                    pa.field("chunk_index", pa.int32()),
                    pa.field("modified_at", pa.float64()),
                    pa.field("embedding", pa.list_(pa.float32(), 768)),
                ]
            )
            _table = _db.create_table("vault_chunks", schema=schema)
        else:
            _table = _db.open_table("vault_chunks")

    return _db, _table


async def get_table():
    """Get LanceDB table (async wrapper)."""
    return await asyncio.get_event_loop().run_in_executor(None, _get_db)


def _generate_chunk_id(file_path: str, chunk_index: int) -> str:
    """Generate deterministic chunk ID."""
    return hashlib.sha256(f"{file_path}:{chunk_index}".encode()).hexdigest()


async def upsert_chunks(
    file_path: Path, chunks: list[dict], embeddings: list[list[float]], modified_at: float
) -> int:
    """Delete old chunks for file_path, insert new ones. Return count inserted."""

    def _upsert():
        _, table = _get_db()

        # Delete existing chunks for this file
        relative_path = str(file_path.relative_to(Config.VAULT_PATH))
        try:
            table.delete(f'file_path = "{relative_path}"')
        except Exception:
            pass  # Table may be empty

        # Build rows for insertion
        rows = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = _generate_chunk_id(relative_path, chunk["index"])
            rows.append(
                {
                    "id": chunk_id,
                    "file_path": relative_path,
                    "title": chunk["title"],
                    "chunk_text": chunk["text"],
                    "chunk_index": chunk["index"],
                    "modified_at": modified_at,
                    "embedding": embedding,
                }
            )

        # Add rows
        if rows:
            table.add(rows)

        return len(rows)

    return await asyncio.get_event_loop().run_in_executor(None, _upsert)


async def delete_chunks(file_path: Path) -> int:
    """Delete all chunks for a file. Return count deleted."""

    def _delete():
        _, table = _get_db()
        relative_path = str(file_path.relative_to(Config.VAULT_PATH))
        try:
            table.delete(f'file_path = "{relative_path}"')
            return 1
        except Exception:
            return 0

    return await asyncio.get_event_loop().run_in_executor(None, _delete)


async def get_chunk_count() -> int:
    """Get total chunks in database."""

    def _count():
        _, table = _get_db()
        return len(table.search().limit(1).to_list()) if table else 0

    return await asyncio.get_event_loop().run_in_executor(None, _count)


async def search_chunks(embedding: list[float], top_k: int = 5) -> list[dict]:
    """Search for similar chunks."""

    def _search():
        _, table = _get_db()
        results = table.search(embedding).limit(top_k).to_list()
        return [
            {
                "file_path": r["file_path"],
                "title": r["title"],
                "chunk_text": r["chunk_text"],
                "score": r["_distance"],
            }
            for r in results
        ]

    return await asyncio.get_event_loop().run_in_executor(None, _search)


async def get_file_mtime(file_path: Path) -> float:
    """Get recorded mtime for a file from index, or 0 if not indexed."""

    def _get():
        _, table = _get_db()
        relative_path = str(file_path.relative_to(Config.VAULT_PATH))
        try:
            result = table.search().where(f'file_path = "{relative_path}"').limit(1).to_list()
            if result:
                return result[0]["modified_at"]
        except Exception:
            pass
        return 0.0

    return await asyncio.get_event_loop().run_in_executor(None, _get)
