from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from ragpipe.pipeline import Pipeline
from ragpipe.sources import FileSource, GitSource, WebSource
from ragpipe.transforms import (
    AutoEmbed,
    FixedSizeChunker,
    HTMLCleaner,
    PIIRemover,
    RecursiveChunker,
    SemanticChunker,
)
from ragpipe.sinks import JSONSink

logger = logging.getLogger("ragpipe.config")

TRANSFORM_REGISTRY: dict[str, type] = {
    "recursive_chunker": RecursiveChunker,
    "fixed_size_chunker": FixedSizeChunker,
    "semantic_chunker": SemanticChunker,
    "html_cleaner": HTMLCleaner,
    "pii_remover": PIIRemover,
    "auto_embed": AutoEmbed,
    "embed": AutoEmbed,
}

SINK_REGISTRY: dict[str, type] = {
    "json": JSONSink,
}


def load_pipeline(path: str | Path) -> Pipeline:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    pipeline = Pipeline()

    source_cfg = config.get("source", {})
    source_type = source_cfg.get("type", "file")
    if source_type == "git":
        pipeline.add_source(GitSource(**_strip_type(source_cfg)))
    elif source_type == "web":
        pipeline.add_source(WebSource(**_strip_type(source_cfg)))
    elif source_type == "file":
        pipeline.add_source(FileSource(**_strip_type(source_cfg)))
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    for t_cfg in config.get("transforms", []):
        t_type = t_cfg.get("type")
        if t_type not in TRANSFORM_REGISTRY:
            raise ValueError(f"Unknown transform: {t_type}. Available: {list(TRANSFORM_REGISTRY)}")
        cls = TRANSFORM_REGISTRY[t_type]
        pipeline.add_transform(cls(**_strip_type(t_cfg)))

    for s_cfg in config.get("sinks", []):
        s_type = s_cfg.get("type")
        if s_type == "qdrant":
            from ragpipe.sinks import QdrantSink

            pipeline.add_sink(QdrantSink(**_strip_type(s_cfg)))
        elif s_type == "pinecone":
            from ragpipe.sinks import PineconeSink

            pipeline.add_sink(PineconeSink(**_strip_type(s_cfg)))
        elif s_type in SINK_REGISTRY:
            pipeline.add_sink(SINK_REGISTRY[s_type](**_strip_type(s_cfg)))
        else:
            raise ValueError(f"Unknown sink: {s_type}")

    return pipeline


def _strip_type(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k != "type"}
