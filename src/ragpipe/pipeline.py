from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Generator, Protocol, runtime_checkable

logger = logging.getLogger("ragpipe")


class Document:
    __slots__ = ("content", "metadata", "embedding", "id", "_char_count")

    def __init__(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        id: str = "",
    ):
        self.content = content
        self.metadata = metadata if metadata is not None else {}
        self.embedding = embedding
        self._char_count = len(content)

        if not id:
            import hashlib

            raw = f"{content[:512]}:{sorted(self.metadata.items())}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def char_count(self) -> int:
        return self._char_count

    def __repr__(self) -> str:
        preview = self.content[:50].replace("\n", " ")
        return f"Document(id={self.id!r}, chars={self._char_count}, preview={preview!r}...)"


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
        self.transforms: list[Transform] = transforms or []
        self.sinks: list[Sink] = sinks or []

    def add_source(self, source: Source) -> Pipeline:
        self.source = source
        return self

    def add_transform(self, transform: Transform) -> Pipeline:
        self.transforms.append(transform)
        return self

    def add_sink(self, sink: Sink) -> Pipeline:
        self.sinks.append(sink)
        return self

    def run(self) -> dict[str, int]:
        if not self.source:
            raise ValueError("Pipeline requires a Source. Use .add_source() or .pipe()")

        stats = {"extracted": 0, "transformed": 0, "written": 0}

        all_docs: list[Document] = []
        for doc in self.source.extract():
            stats["extracted"] += 1
            batch: list[Document] = [doc]
            for t in self.transforms:
                next_batch: list[Document] = []
                for d in batch:
                    next_batch.extend(t.transform(d))
                batch = next_batch
            all_docs.extend(batch)
            stats["transformed"] += len(batch)

        for sink in self.sinks:
            stats["written"] += sink.write(all_docs)

        logger.info("Pipeline done: %s", stats)
        return stats

    def dry_run(self) -> list[Document]:
        if not self.source:
            raise ValueError("Pipeline requires a Source")

        all_docs: list[Document] = []
        for doc in self.source.extract():
            batch: list[Document] = [doc]
            for t in self.transforms:
                next_batch: list[Document] = []
                for d in batch:
                    next_batch.extend(t.transform(d))
                batch = next_batch
            all_docs.extend(batch)
        return all_docs
