from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ragpipe.pipeline import Document, Pipeline
from ragpipe.sinks import JSONSink
from ragpipe.sources import FileSource, GitSource, WebSource
from ragpipe.transforms import AutoEmbed, HTMLCleaner, PIIRemover, RecursiveChunker

logger = logging.getLogger("ragpipe")


def _detect_source(source: str):
    if source.startswith(("http://", "https://")):
        if "github.com" in source:
            return GitSource(repo_url=source)
        return WebSource(urls=[source])
    return FileSource(paths=[source])


def ingest(
    source: str,
    sink: str = "json",
    sink_path: str = "./ragpipe_output.json",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    clean_html: bool = True,
    remove_pii: bool = False,
    embed: bool = False,
    embed_model: str | None = None,
    embed_base_url: str | None = None,
    **kwargs: Any,
) -> dict[str, int]:
    src = _detect_source(source)

    transforms: list[Any] = []
    if clean_html:
        transforms.append(HTMLCleaner())
    if remove_pii:
        transforms.append(PIIRemover())
    transforms.append(RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    if embed:
        transforms.append(AutoEmbed(model=embed_model, base_url=embed_base_url))

    sinks: list[Any] = []
    if sink == "json":
        sinks.append(JSONSink(output_path=sink_path, include_embeddings=embed))
    elif sink == "qdrant":
        from ragpipe.sinks import QdrantSink

        sinks.append(
            QdrantSink(
                collection_name=kwargs.get("collection", "ragpipe"),
                url=kwargs.get("qdrant_url", "http://localhost:6333"),
                api_key=kwargs.get("qdrant_api_key"),
                vector_size=kwargs.get("vector_size", 384),
            )
        )
    elif sink == "pinecone":
        from ragpipe.sinks import PineconeSink

        sinks.append(
            PineconeSink(
                index_name=kwargs.get("index", "ragpipe"),
                api_key=kwargs["pinecone_api_key"],
                dimension=kwargs.get("dimension", 384),
            )
        )
    else:
        raise ValueError(f"Unknown sink: {sink}. Use 'json', 'qdrant', or 'pinecone'")

    pipeline = Pipeline(source=src, transforms=transforms, sinks=sinks)
    return pipeline.run()


def query(
    text: str,
    collection: str = "ragpipe",
    sink: str = "json",
    sink_path: str = "./ragpipe_output.json",
    top_k: int = 5,
    embed_model: str | None = None,
    embed_base_url: str | None = None,
    **kwargs: Any,
) -> list[Document]:
    embedder = AutoEmbed(model=embed_model, base_url=embed_base_url)
    query_embedding = embedder.embed_single(text)
    if query_embedding is None:
        raise RuntimeError("Failed to generate query embedding")

    if sink == "json":
        import json

        data = json.loads(Path(sink_path).read_text())
        scored: list[tuple[float, dict]] = []
        for item in data:
            emb = item.get("embedding")
            if emb is None:
                continue
            score = _cosine_sim(query_embedding, emb)
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, item in scored[:top_k]:
            results.append(
                Document(
                    content=item["content"],
                    metadata={**item.get("metadata", {}), "score": score},
                )
            )
        return results
    elif sink == "qdrant":
        from ragpipe.sinks import QdrantSink
        from qdrant_client import QdrantClient
        from qdrant_client.models import NamedVector

        client = QdrantClient(
            url=kwargs.get("qdrant_url", "http://localhost:6333"),
            api_key=kwargs.get("qdrant_api_key"),
        )
        hits = client.query_points(
            collection_name=collection,
            points=[query_embedding],
            limit=top_k,
        ).points
        return [
            Document(
                content=hit.payload.get("content", ""),
                metadata={
                    **{k: v for k, v in (hit.payload or {}).items() if k != "content"},
                    "score": hit.score,
                },
            )
            for hit in hits
        ]
    else:
        raise ValueError(f"Query not supported for sink: {sink}")


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
