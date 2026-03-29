from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generator, Protocol, runtime_checkable

logger = logging.getLogger("ragpipe")


@dataclass
class Document:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = field(default=None, repr=False)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            raw = f"{self.content[:1024]}:{self.metadata}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def char_count(self) -> int:
        return len(self.content)


@runtime_checkable
class Source(Protocol):
    def extract(self) -> Generator[Document, None, None]: ...


@runtime_checkable
class Transform(Protocol):
    def transform(self, doc: Document) -> list[Document]: ...


@runtime_checkable
class Sink(Protocol):
    def write(self, docs: list[Document]) -> int: ...


class Pipeline:
    def __init__(
        self,
        source: Source | None = None,
        transforms: list[Transform] | None = None,
        sinks: list[Sink] | None = None,
    ):
        self.source = source
        self.transforms = transforms or []
        self.sinks = sinks or []
        self._stats: dict[str, int] = {
            "extracted": 0,
            "transformed": 0,
            "written": 0,
        }

    def add_source(self, source: Source) -> "Pipeline":
        self.source = source
        return self

    def add_transform(self, transform: Transform) -> "Pipeline":
        self.transforms.append(transform)
        return self

    def add_sink(self, sink: Sink) -> "Pipeline":
        self.sinks.append(sink)
        return self

    def run(self) -> dict[str, int]:
        if not self.source:
            raise ValueError("Pipeline requires at least one Source")

        start = datetime.now()
        logger.info("Pipeline started at %s", start.isoformat())

        all_docs: list[Document] = []

        for doc in self.source.extract():
            self._stats["extracted"] += 1
            current: list[Document] = [doc]

            for transform in self.transforms:
                next_batch: list[Document] = []
                for d in current:
                    next_batch.extend(transform.transform(d))
                current = next_batch

            all_docs.extend(current)
            self._stats["transformed"] += len(current)

        for sink in self.sinks:
            written = sink.write(all_docs)
            self._stats["written"] += written

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            "Pipeline finished in %.2fs — extracted=%d, transformed=%d, written=%d",
            elapsed,
            self._stats["extracted"],
            self._stats["transformed"],
            self._stats["written"],
        )

        return dict(self._stats)

    def dry_run(self) -> list[Document]:
        if not self.source:
            raise ValueError("Pipeline requires at least one Source")

        all_docs: list[Document] = []

        for doc in self.source.extract():
            current: list[Document] = [doc]
            for transform in self.transforms:
                next_batch: list[Document] = []
                for d in current:
                    next_batch.extend(transform.transform(d))
                current = next_batch
            all_docs.extend(current)

        return all_docs
