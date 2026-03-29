from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger("ragpipe.watcher")

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    _HAS_WATCHDOG = True
except ImportError:
    _HAS_WATCHDOG = False

try:
    from rich.console import Console

    _console = Console()
except ImportError:
    _console = None


def _print_status(msg: str) -> None:
    if _console is not None:
        _console.print(f"[bold cyan][watcher][/bold cyan] {msg}")
    else:
        print(f"[watcher] {msg}")


def _should_include(path: str, extensions: list[str] | None) -> bool:
    if extensions is None:
        return True
    return any(path.endswith(ext) for ext in extensions)


if _HAS_WATCHDOG:

    class _DebouncedHandler(FileSystemEventHandler):
        def __init__(
            self,
            on_change: Callable[[str, str], None] | None,
            debounce: float,
            extensions: list[str] | None,
        ) -> None:
            super().__init__()
            self._on_change = on_change
            self._debounce = debounce
            self._extensions = extensions
            self._timer: threading.Timer | None = None
            self._pending: list[tuple[str, str]] = []
            self._lock = threading.Lock()

        def _record(self, event_type: str, src_path: str) -> None:
            if event_type == "deleted" or Path(src_path).is_file():
                if not _should_include(src_path, self._extensions):
                    return
                with self._lock:
                    self._pending.append((event_type, src_path))
                    if self._timer is not None:
                        self._timer.cancel()
                    self._timer = threading.Timer(self._debounce, self._flush)
                    self._timer.start()

        def _flush(self) -> None:
            with self._lock:
                items = list(self._pending)
                self._pending.clear()
                self._timer = None
            for event_type, src_path in items:
                logger.info("File %s: %s", event_type, src_path)
                if self._on_change is not None:
                    self._on_change(event_type, src_path)

        def on_created(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self._record("created", event.src_path)

        def on_modified(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self._record("modified", event.src_path)

        def on_deleted(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self._record("deleted", event.src_path)


def watch(
    path: str,
    on_change: Callable[[str, str], None] | None = None,
    debounce: float = 2.0,
    extensions: list[str] | None = None,
) -> None:
    if not _HAS_WATCHDOG:
        print("watchdog is required for file watching. Install it with: pip install watchdog")
        return

    abs_path = str(Path(path).resolve())
    if not Path(abs_path).is_dir():
        print(f"Path does not exist or is not a directory: {abs_path}")
        return

    ext_info = f" (filtering: {', '.join(extensions)})" if extensions else ""
    _print_status(f"Watching {abs_path}{ext_info} with {debounce}s debounce")

    observer = Observer()
    handler = _DebouncedHandler(on_change, debounce, extensions)
    observer.schedule(handler, abs_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _print_status("Stopping watcher...")
    finally:
        observer.stop()
        observer.join()
        _print_status("Watcher stopped")
