from __future__ import annotations

import json
import logging
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("ragpipe.server")

_JSON_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

_OPTIONS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _parse_query(path: str) -> tuple[str, dict[str, str]]:
    parsed = urlparse(path)
    query: dict[str, str] = {}
    for part in (parsed.query or "").split("&"):
        if "=" in part:
            key, val = part.split("=", 1)
            query[key] = val
        elif part:
            query[part] = ""
    return parsed.path.rstrip("/"), query


def _keyword_search(chunks: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
    tokens = re.findall(r"\w+", query.lower())
    if not tokens:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        content = (chunk.get("content") or "").lower()
        metadata_str = json.dumps(chunk.get("metadata", {}), default=str).lower()
        combined = content + " " + metadata_str
        score = sum(1 for t in tokens if t in combined)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


class _Handler(BaseHTTPRequestHandler):
    data_path: str
    _data: dict[str, Any] = {}
    _chunks: list[dict[str, Any]] = []

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(format, *args)

    def _json_response(self, code: int, body: Any) -> None:
        payload = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        for k, v in _JSON_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _load_data(self) -> dict[str, Any]:
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._data = data
            self._chunks = data.get("chunks", [])
            return data
        except FileNotFoundError:
            logger.error("Data file not found: %s", self.data_path)
            return {"error": f"Data file not found: {self.data_path}"}
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", self.data_path, exc)
            return {"error": f"Invalid JSON in data file: {exc}"}

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        for k, v in _OPTIONS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        path, query = _parse_query(self.path)

        if path == "":
            files = self._data.get("files_indexed", 0)
            total = len(self._chunks)
            self._json_response(
                200,
                {
                    "status": "ok",
                    "files_indexed": files,
                    "total_chunks": total,
                },
            )

        elif path == "/health":
            self._json_response(200, {"status": "ok"})

        elif path == "/search":
            q = query.get("q", "")
            top_k = int(query.get("top_k", "5"))
            if not q:
                self._json_response(400, {"error": "Missing query parameter 'q'"})
                return
            results = _keyword_search(self._chunks, q, top_k)
            self._json_response(200, {"query": q, "results": results, "count": len(results)})

        elif path == "/chunks":
            listing = [
                {
                    "id": c.get("id"),
                    "file": c.get("file"),
                    "index": c.get("index"),
                    "metadata": c.get("metadata", {}),
                }
                for c in self._chunks
            ]
            self._json_response(200, {"chunks": listing, "count": len(listing)})

        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path, _ = _parse_query(self.path)

        if path == "/reindex":
            data = self._load_data()
            if "error" in data:
                self._json_response(500, data)
            else:
                self._json_response(200, {"status": "reindexed", "total_chunks": len(self._chunks)})

        else:
            self._json_response(404, {"error": "Not found"})


def serve(
    data_path: str = "./ragpipe_output.json",
    host: str = "127.0.0.1",
    port: int = 7642,
) -> None:
    _Handler.data_path = data_path  # type: ignore[attr-defined]

    _Handler._load_data(_Handler)  # type: ignore[attr-defined]

    server = HTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}"
    print(f"RAGPipe server running at {url}")
    print(f"  GET /        — status")
    print(f"  GET /search  — keyword search")
    print(f"  GET /health  — health check")
    print(f"  GET /chunks  — list all chunks")
    print(f"  POST /reindex — reload data from disk")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.server_close()
        print("Server stopped")
