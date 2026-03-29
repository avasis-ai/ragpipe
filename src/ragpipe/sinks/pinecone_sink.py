from __future__ import annotations

import logging
from typing import Any

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.sinks.pinecone")

try:
    from pinecone import Pinecone

    HAS_PINECONE = True
except ImportError:
    HAS_PINECONE = False


class PineconeSink:
    def __init__(
        self,
        index_name: str,
        api_key: str,
        namespace: str = "",
        dimension: int = 1536,
        metric: str = "cosine",
        batch_size: int = 100,
        create_index: bool = True,
    ):
        if not HAS_PINECONE:
            raise ImportError(
                "pinecone-client is required for PineconeSink. "
                "Install with: pip install ragpipe[pinecone]"
            )

        self.index_name = index_name
        self.namespace = namespace
        self.dimension = dimension
        self.metric = metric
        self.batch_size = batch_size
        self.create_index = create_index

        self.pc = Pinecone(api_key=api_key)
        self._index = None

    def _get_index(self):
        if self._index is not None:
            return self._index

        if self.index_name not in [i.name for i in self.pc.list_indexes()]:
            if self.create_index:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
                )
                logger.info("Created Pinecone index %s", self.index_name)
            else:
                raise ValueError(f"Index {self.index_name} does not exist")

        self._index = self.pc.Index(self.index_name)
        return self._index

    def write(self, docs: list[Document]) -> int:
        index = self._get_index()
        vectors = []
        written = 0

        for doc in docs:
            if doc.embedding is None:
                continue

            vectors.append(
                {
                    "id": doc.id,
                    "values": doc.embedding,
                    "metadata": {
                        "content": doc.content,
                        **doc.metadata,
                    },
                }
            )

            if len(vectors) >= self.batch_size:
                kwargs: dict[str, Any] = {"vectors": vectors}
                if self.namespace:
                    kwargs["namespace"] = self.namespace
                index.upsert(**kwargs)
                written += len(vectors)
                vectors = []

        if vectors:
            kwargs: dict[str, Any] = {"vectors": vectors}
            if self.namespace:
                kwargs["namespace"] = self.namespace
            index.upsert(**kwargs)
            written += len(vectors)

        logger.info("Wrote %d vectors to %s", written, self.index_name)
        return written
