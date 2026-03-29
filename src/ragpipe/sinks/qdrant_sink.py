from __future__ import annotations

import logging
from typing import Any

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.sinks.qdrant")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False


class QdrantSink:
    def __init__(
        self,
        collection_name: str,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
        vector_size: int = 1536,
        distance: str = "cosine",
        batch_size: int = 100,
        upsert: bool = True,
    ):
        if not HAS_QDRANT:
            raise ImportError(
                "qdrant-client is required for QdrantSink. "
                "Install with: pip install ragpipe[qdrant]"
            )

        self.collection_name = collection_name
        self.url = url
        self.api_key = api_key
        self.vector_size = vector_size
        self.distance = distance
        self.batch_size = batch_size
        self.upsert = upsert

        distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT,
        }
        self._distance = distance_map.get(distance.lower(), Distance.COSINE)

    def _get_client(self) -> "QdrantClient":
        kwargs: dict[str, Any] = {"url": self.url}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        return QdrantClient(**kwargs)

    def write(self, docs: list[Document]) -> int:
        client = self._get_client()

        try:
            collections = client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
        except Exception:
            exists = False

        if not exists:
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=self._distance,
                ),
            )
            logger.info("Created collection %s", self.collection_name)

        written = 0
        for i in range(0, len(docs), self.batch_size):
            batch = docs[i : i + self.batch_size]
            points = []

            for j, doc in enumerate(batch):
                if doc.embedding is None:
                    logger.debug("Skipping doc %s — no embedding", doc.id)
                    continue

                point = PointStruct(
                    id=doc.id,
                    vector=doc.embedding,
                    payload={
                        "content": doc.content,
                        **doc.metadata,
                    },
                )
                points.append(point)

            if not points:
                continue

            if self.upsert:
                client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
            else:
                client.upload_points(
                    collection_name=self.collection_name,
                    points=points,
                )

            written += len(points)

        logger.info("Wrote %d points to %s", written, self.collection_name)
        return written
