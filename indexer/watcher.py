import asyncio
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import Config


class VaultEventHandler(FileSystemEventHandler):
    """Handle vault file changes with debouncing."""

    def __init__(self, on_change_callback, event_loop):
        self.on_change_callback = on_change_callback
        self.event_loop = event_loop
        self.pending_timers = {}

    def _schedule_update(self, file_path: Path):
        """Debounce file updates (2 second delay)."""
        if file_path in self.pending_timers:
            self.pending_timers[file_path].cancel()

        def trigger():
            asyncio.run_coroutine_threadsafe(self.on_change_callback(file_path), self.event_loop)

        # Use threading.Timer since we're in a different thread
        timer = threading.Timer(2.0, trigger)
        timer.daemon = True
        timer.start()
        self.pending_timers[file_path] = timer

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        self._schedule_update(Path(event.src_path))

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        self._schedule_update(Path(event.src_path))

    def on_deleted(self, event):
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        self._schedule_update(Path(event.src_path))


def start_watcher(on_change_callback, event_loop):
    """Start watchdog observer on vault directory."""
    handler = VaultEventHandler(on_change_callback, event_loop)
    observer = Observer()
    observer.schedule(handler, str(Config.VAULT_PATH), recursive=True)
    observer.start()
    return observer
