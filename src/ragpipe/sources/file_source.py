from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Generator

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.sources.file")


class FileSource:
    def __init__(
        self,
        paths: str | list[str],
        recursive: bool = True,
        file_extensions: list[str] | None = None,
        encoding: str = "utf-8",
    ):
        if isinstance(paths, str):
            paths = [paths]
        self.paths = [Path(p) for p in paths]
        self.recursive = recursive
        self.file_extensions = set(ext.lower() for ext in (file_extensions or []))
        self.encoding = encoding

    def extract(self) -> Generator[Document, None, None]:
        for base_path in self.paths:
            if not base_path.exists():
                logger.warning("Path does not exist: %s", base_path)
                continue

            if base_path.is_file():
                yield from self._read_file(base_path)
            elif base_path.is_dir():
                yield from self._read_dir(base_path)

    def _read_dir(self, directory: Path) -> Generator[Document, None, None]:
        walk = (
            os.walk(directory)
            if self.recursive
            else [(directory, [], os.listdir(directory))]
        )
        for root, _dirs, files in walk:
            for fname in sorted(files):
                fpath = Path(root) / fname
                if (
                    self.file_extensions
                    and fpath.suffix.lower() not in self.file_extensions
                ):
                    continue
                if not fpath.is_file():
                    continue
                yield from self._read_file(fpath)

    def _read_file(self, fpath: Path) -> Generator[Document, None, None]:
        try:
            content = fpath.read_text(encoding=self.encoding, errors="ignore")
            if not content.strip():
                return
            yield Document(
                content=content,
                metadata={
                    "source": "file",
                    "path": str(fpath.absolute()),
                    "filename": fpath.name,
                    "extension": fpath.suffix.lower(),
                    "size_bytes": fpath.stat().st_size,
                },
            )
        except Exception as e:
            logger.warning("Failed to read %s: %s", fpath, e)
