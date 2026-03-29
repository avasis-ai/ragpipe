from __future__ import annotations

import logging
from typing import Any

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.transforms.auto_embed")


class AutoEmbed:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        fallback: bool = True,
    ):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.fallback = fallback
        self._backend: str | None = None
        self._client: Any = None
        self._resolved_model: str | None = None

    def _init_backend(self):
        if self._backend:
            return

        if self.fallback:
            for backend_name, check_fn, init_fn in [
                ("ollama", self._check_ollama, self._init_ollama),
                ("openai", self._check_openai, self._init_openai),
                ("sentence_transformers", self._check_st, self._init_st),
            ]:
                if check_fn():
                    init_fn()
                    self._backend = backend_name
                    logger.info(
                        "AutoEmbed: using %s backend (model=%s)", backend_name, self._resolved_model
                    )
                    return

        if self.base_url or self.api_key:
            self._init_openai()
            self._backend = "openai"
            logger.info(
                "AutoEmbed: using openai-compatible backend (model=%s)", self._resolved_model
            )
            return

        raise RuntimeError(
            "No embedding backend found. Install one of:\n"
            "  pip install openai          # OpenAI or compatible API\n"
            "  pip install sentence-transformers  # Local CPU/GPU embeddings\n"
            "  # Or run Ollama locally:    ollama pull nomic-embed-text\n"
            "  # Then set base_url=http://localhost:11434/v1"
        )

    def _check_openai(self) -> bool:
        try:
            import openai
            import os

            if not self.base_url and not os.environ.get("OPENAI_API_KEY"):
                return False
            return True
        except ImportError:
            return False

    def _init_openai(self):
        from openai import OpenAI

        kwargs: dict[str, Any] = {}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = OpenAI(**kwargs)
        self._resolved_model = self.model or "text-embedding-3-small"

    def _check_ollama(self) -> bool:
        try:
            import httpx

            resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                embed_models = [m for m in models if "embed" in m.lower()]
                if embed_models:
                    self._ollama_model = embed_models[0]
                    return True
                if models:
                    self._ollama_model = models[0]
                    return True
        except Exception:
            pass
        return False

    def _init_ollama(self):
        import httpx

        self._base_url_ollama = "http://localhost:11434"
        self._resolved_model = self.model or getattr(self, "_ollama_model", "nomic-embed-text")
        self._client = httpx.Client(base_url=self._base_url_ollama, timeout=60.0)
        self._backend = "ollama"

    def _check_st(self) -> bool:
        try:
            from sentence_transformers import SentenceTransformer

            return True
        except ImportError:
            return False

    def _init_st(self):
        from sentence_transformers import SentenceTransformer

        self._resolved_model = self.model or "all-MiniLM-L6-v2"
        self._st_model = SentenceTransformer(self._resolved_model)
        self._backend = "sentence_transformers"

    def transform(self, doc: Document) -> list[Document]:
        emb = self.embed_single(doc.content)
        if emb is None:
            return [doc]
        return [
            Document(
                content=doc.content,
                metadata={**doc.metadata, "embedding_model": self._resolved_model},
                embedding=emb,
            )
        ]

    def embed_single(self, text: str) -> list[float] | None:
        self._init_backend()
        if self._backend == "openai":
            resp = self._client.embeddings.create(input=[text], model=self._resolved_model)
            return resp.data[0].embedding
        elif self._backend == "ollama":
            resp = self._client.post(
                "/api/embeddings", json={"model": self._resolved_model, "prompt": text}
            )
            resp.raise_for_status()
            return resp.json()["embedding"]
        elif self._backend == "sentence_transformers":
            return self._st_model.encode(text).tolist()
        return None

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        self._init_backend()
        if self._backend == "openai":
            resp = self._client.embeddings.create(input=texts, model=self._resolved_model)
            return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
        elif self._backend == "ollama":
            results = []
            for text in texts:
                resp = self._client.post(
                    "/api/embeddings", json={"model": self._resolved_model, "prompt": text}
                )
                resp.raise_for_status()
                results.append(resp.json()["embedding"])
            return results
        elif self._backend == "sentence_transformers":
            return [e.tolist() for e in self._st_model.encode(texts)]
        return [None] * len(texts)
