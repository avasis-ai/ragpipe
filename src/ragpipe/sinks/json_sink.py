from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.sinks.json")


class JSONSink:
    def __init__(
        self,
        output_path: str,
        indent: int = 2,
        include_embeddings: bool = False,
        append: bool = False,
    ):
        self.output_path = Path(output_path)
        self.indent = indent
        self.include_embeddings = include_embeddings
        self.append = append

    def write(self, docs: list[Document]) -> int:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        existing: list[dict[str, Any]] = []
        if self.append and self.output_path.exists():
            try:
                existing = json.loads(self.output_path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not read existing JSON: %s", e)

        serialized: list[dict[str, Any]] = []
        for doc in docs:
            entry: dict[str, Any] = {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
            }
            if self.include_embeddings and doc.embedding is not None:
                entry["embedding"] = doc.embedding
            serialized.append(entry)

        existing.extend(serialized)

        self.output_path.write_text(
            json.dumps(existing, indent=self.indent, ensure_ascii=False)
        )

        logger.info("Wrote %d documents to %s", len(serialized), self.output_path)
        return len(serialized)
