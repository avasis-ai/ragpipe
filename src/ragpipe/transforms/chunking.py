from __future__ import annotations

import logging
import re
from typing import Any

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.transforms.chunking")

SEPARATORS = [
    "\n\n\n",
    "\n\n",
    "\n",
    ". ",
    "? ",
    "! ",
    "; ",
    ", ",
    " ",
    "",
]


class RecursiveChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list[str] | None = None,
        min_chunk_size: int = 10,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or SEPARATORS
        self.min_chunk_size = min_chunk_size

    def transform(self, doc: Document) -> list[Document]:
        chunks = self._split_text(doc.content)

        result = []
        for i, chunk_text in enumerate(chunks):
            if len(chunk_text.strip()) < self.min_chunk_size:
                continue
            chunk_meta = dict(doc.metadata)
            chunk_meta.update(
                {
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                    "chunk_type": "recursive",
                    "chunk_size": len(chunk_text),
                }
            )
            result.append(Document(content=chunk_text, metadata=chunk_meta))

        logger.debug(
            "RecursiveChunker: %s -> %d chunks",
            doc.metadata.get("path", "?"),
            len(result),
        )
        return result

    def _split_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        for sep in self.separators:
            if sep == "":
                return self._split_by_chars(text)
            if sep in text:
                splits = text.split(sep)
                return self._merge_splits(splits, sep)

        return self._split_by_chars(text)

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        chunks: list[str] = []
        current = ""
        for split in splits:
            candidate = current + separator + split if current else split
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = split

        if current:
            chunks.append(current)

        merged: list[str] = []
        for chunk in chunks:
            if merged and self.chunk_overlap > 0:
                prev = merged[-1]
                overlap = (
                    prev[-self.chunk_overlap :]
                    if len(prev) > self.chunk_overlap
                    else prev
                )
                chunk = overlap + separator + chunk
            merged.append(chunk)

        return merged

    def _split_by_chars(self, text: str) -> list[str]:
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunk = text[i : i + self.chunk_size]
            if i + self.chunk_size < len(text) and self.chunk_overlap:
                chunk = text[max(0, i - self.chunk_overlap) : i + self.chunk_size]
            chunks.append(chunk)
        return chunks


class FixedSizeChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separator: str = "\n",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def transform(self, doc: Document) -> list[Document]:
        text = doc.content
        chunks = []

        if self.separator:
            splits = text.split(self.separator)
        else:
            splits = [text]

        current_parts: list[str] = []
        current_len = 0

        for part in splits:
            part_len = len(part) + len(self.separator) if current_parts else len(part)

            if current_len + part_len > self.chunk_size and current_parts:
                chunks.append(self.separator.join(current_parts))
                if self.chunk_overlap > 0:
                    overlap_parts: list[str] = []
                    overlap_len = 0
                    for p in reversed(current_parts):
                        if overlap_len + len(p) > self.chunk_overlap:
                            break
                        overlap_parts.insert(0, p)
                        overlap_len += len(p)
                    current_parts = overlap_parts
                    current_len = overlap_len
                else:
                    current_parts = []
                    current_len = 0

            current_parts.append(part)
            current_len += part_len

        if current_parts:
            chunks.append(self.separator.join(current_parts))

        result = []
        for i, chunk_text in enumerate(chunks):
            chunk_meta = dict(doc.metadata)
            chunk_meta.update(
                {
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                    "chunk_type": "fixed",
                    "chunk_size": len(chunk_text),
                }
            )
            result.append(Document(content=chunk_text, metadata=chunk_meta))

        return result


class SemanticChunker:
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        percentile_threshold: float = 85.0,
        embedding_model: str | None = None,
        embedding_api_key: str | None = None,
        embedding_base_url: str | None = None,
    ):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.percentile_threshold = percentile_threshold
        self.embedding_model = embedding_model
        self.embedding_api_key = embedding_api_key
        self.embedding_base_url = embedding_base_url

    def transform(self, doc: Document) -> list[Document]:
        sentences = self._split_sentences(doc.content)
        if len(sentences) <= 1:
            return [
                Document(
                    content=doc.content,
                    metadata={
                        **doc.metadata,
                        "chunk_index": 0,
                        "chunk_total": 1,
                        "chunk_type": "semantic",
                    },
                )
            ]

        embeddings = self._embed_sentences(sentences)

        if not embeddings:
            logger.warning(
                "SemanticChunker: no embeddings, falling back to sentence-level chunks"
            )
            text = " ".join(sentences)
            return [
                Document(
                    content=text,
                    metadata={
                        **doc.metadata,
                        "chunk_index": 0,
                        "chunk_total": 1,
                        "chunk_type": "semantic",
                    },
                )
            ]

        distances = self._compute_distances(embeddings)

        import statistics

        if distances:
            threshold = (
                statistics.quantiles(distances, n=100)[
                    int(self.percentile_threshold) - 1
                ]
                if len(distances) >= 100
                else statistics.quantiles(distances, n=max(2, len(distances)))[-1]
            )
        else:
            threshold = 0.5

        chunks = self._group_by_threshold(sentences, distances, threshold)

        result = []
        for i, chunk_text in enumerate(chunks):
            chunk_meta = dict(doc.metadata)
            chunk_meta.update(
                {
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                    "chunk_type": "semantic",
                    "chunk_size": len(chunk_text),
                }
            )
            result.append(Document(content=chunk_text, metadata=chunk_meta))

        return result

    def _split_sentences(self, text: str) -> list[str]:
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _embed_sentences(self, sentences: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI

            client_kwargs: dict[str, Any] = {}
            if self.embedding_api_key:
                client_kwargs["api_key"] = self.embedding_api_key
            if self.embedding_base_url:
                client_kwargs["base_url"] = self.embedding_base_url

            client = OpenAI(**client_kwargs)
            model = self.embedding_model or "text-embedding-3-small"
            response = client.embeddings.create(input=sentences, model=model)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning("Embedding failed in SemanticChunker: %s", e)
            return []

    def _compute_distances(self, embeddings: list[list[float]]) -> list[float]:
        from math import sqrt

        distances = []
        for i in range(len(embeddings) - 1):
            a, b = embeddings[i], embeddings[i + 1]
            dist = sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
            distances.append(dist)
        return distances

    def _group_by_threshold(
        self,
        sentences: list[str],
        distances: list[float],
        threshold: float,
    ) -> list[str]:
        chunks: list[str] = []
        current = sentences[0]

        for i, dist in enumerate(distances):
            next_sentence = sentences[i + 1]
            candidate = current + " " + next_sentence

            if dist > threshold or len(candidate) > self.max_chunk_size:
                chunks.append(current)
                current = next_sentence
            else:
                current = candidate

        chunks.append(current)

        merged: list[str] = []
        for chunk in chunks:
            if merged and len(merged[-1]) < self.min_chunk_size:
                merged[-1] += " " + chunk
            else:
                merged.append(chunk)

        return merged
