"""Incremental indexing with checkpoints for faster startup."""

import json
from pathlib import Path
from datetime import datetime


class IndexCheckpoint:
    """Manage incremental indexing checkpoints."""

    def __init__(self, checkpoint_file: Path):
        """Initialize checkpoint manager.

        Args:
            checkpoint_file: Path to store checkpoint data
        """
        self.checkpoint_file = checkpoint_file
        self.data = self._load()

    def _load(self) -> dict:
        """Load checkpoint from disk."""
        if not self.checkpoint_file.exists():
            return {"last_full_scan": None, "files": {}, "version": 1}

        try:
            with open(self.checkpoint_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load checkpoint: {e}")
            return {"last_full_scan": None, "files": {}, "version": 1}

    def _save(self) -> None:
        """Save checkpoint to disk."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.checkpoint_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save checkpoint: {e}")

    def mark_file_indexed(self, filepath: Path, mtime: float) -> None:
        """Record that a file has been indexed.

        Args:
            filepath: Path to indexed file
            mtime: File modification time
        """
        filepath_str = str(filepath)
        self.data["files"][filepath_str] = {"mtime": mtime, "indexed_at": datetime.now().isoformat()}
        self._save()

    def mark_file_deleted(self, filepath: Path) -> None:
        """Record that a file has been deleted.

        Args:
            filepath: Path to deleted file
        """
        filepath_str = str(filepath)
        if filepath_str in self.data["files"]:
            del self.data["files"][filepath_str]
        self._save()

    def mark_full_scan(self) -> None:
        """Mark that a full index scan has been completed."""
        self.data["last_full_scan"] = datetime.now().isoformat()
        self._save()

    def needs_reindexing(self, filepath: Path, current_mtime: float) -> bool:
        """Check if a file needs reindexing based on checkpoint.

        Args:
            filepath: Path to check
            current_mtime: Current file modification time

        Returns:
            True if file needs reindexing, False otherwise
        """
        filepath_str = str(filepath)
        if filepath_str not in self.data["files"]:
            return True  # New file

        checkpoint_mtime = self.data["files"][filepath_str].get("mtime")
        return checkpoint_mtime != current_mtime

    def get_files_needing_reindex(self, vault_path: Path) -> list[Path]:
        """Get list of files that need reindexing.

        Compares checkpoint records with actual vault files.

        Args:
            vault_path: Root path of vault

        Returns:
            List of files needing reindexing
        """
        files_to_reindex = []

        # Check existing files
        for md_file in vault_path.rglob("*.md"):
            if md_file.name.startswith("_") or md_file.name.startswith("."):
                continue

            try:
                mtime = md_file.stat().st_mtime
                if self.needs_reindexing(md_file, mtime):
                    files_to_reindex.append(md_file)
            except Exception:
                # File might have been deleted, skip
                pass

        # Check for deleted files (in checkpoint but not in vault)
        checkpoint_files = set(self.data["files"].keys())
        vault_files = {str(f) for f in vault_path.rglob("*.md")}
        for deleted_file_str in checkpoint_files - vault_files:
            self.mark_file_deleted(Path(deleted_file_str))

        return files_to_reindex

    def reset(self) -> None:
        """Reset checkpoint (force full reindex on next scan)."""
        self.data = {"last_full_scan": None, "files": {}, "version": 1}
        self._save()

    def get_stats(self) -> dict:
        """Get checkpoint statistics.

        Returns:
            Dictionary with stats about indexed files
        """
        return {
            "total_indexed_files": len(self.data["files"]),
            "last_full_scan": self.data["last_full_scan"],
            "checkpoint_version": self.data["version"],
        }
