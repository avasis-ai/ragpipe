from __future__ import annotations

import logging
from typing import Any

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.transforms.embeddings")

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class EmbeddingTransform:
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        base_url: str | None = None,
        batch_size: int = 64,
        dimensions: int | None = None,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.batch_size = batch_size
        self.dimensions = dimensions
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

    def transform(self, doc: Document) -> list[Document]:
        embedding = self._embed_single(doc.content)
        if embedding is None:
            return [doc]

        new_meta = dict(doc.metadata)
        new_meta["embedding_model"] = self.model
        if self.dimensions:
            new_meta["embedding_dimensions"] = self.dimensions

        return [Document(content=doc.content, metadata=new_meta, embedding=embedding)]

    def embed_batch(self, docs: list[Document]) -> list[Document]:
        texts = [doc.content for doc in docs]
        all_embeddings = self._embed_batch(texts)

        result = []
        for doc, embedding in zip(docs, all_embeddings):
            if embedding is not None:
                new_meta = dict(doc.metadata)
                new_meta["embedding_model"] = self.model
                result.append(
                    Document(
                        content=doc.content, metadata=new_meta, embedding=embedding
                    )
                )
            else:
                result.append(doc)

        return result

    def _embed_single(self, text: str) -> list[float] | None:
        embeddings = self._embed_batch([text])
        return embeddings[0] if embeddings else None

    def _embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        all_embeddings: list[list[float] | None] = [None] * len(texts)

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            embeddings = self._call_api(batch)
            all_embeddings[i : i + len(batch)] = embeddings

        return all_embeddings

    def _call_api(self, texts: list[str]) -> list[list[float] | None]:
        if not HAS_HTTPX:
            logger.error("httpx is required for EmbeddingTransform")
            return [None] * len(texts)

        url = f"{(self.base_url or 'https://api.openai.com').rstrip('/')}/v1/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        if self.dimensions:
            body["dimensions"] = self.dimensions

        for attempt in range(self.retry_attempts):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, json=body, headers=headers)
                    response.raise_for_status()
                    data = response.json()

                result: list[list[float] | None] = []
                for item in data.get("data", []):
                    result.append(item.get("embedding"))
                return result

            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    import time

                    time.sleep(self.retry_delay * (attempt + 1))
                    logger.warning(
                        "Embedding API attempt %d failed: %s", attempt + 1, e
                    )
                else:
                    logger.error(
                        "Embedding API failed after %d attempts: %s",
                        self.retry_attempts,
                        e,
                    )
                    return [None] * len(texts)

        return [None] * len(texts)
