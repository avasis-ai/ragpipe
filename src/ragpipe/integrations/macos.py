from __future__ import annotations

import logging
import os
import subprocess
import sys

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ragpipe import Document

logger = logging.getLogger(__name__)

_TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".mjs",
        ".cjs",
        ".jsx",
        ".tsx",
        ".md",
        ".txt",
        ".rst",
        ".csv",
        ".log",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".less",
        ".xml",
        ".svg",
        ".sql",
        ".graphql",
        ".env",
        ".gitignore",
        ".dockerignore",
    }
)


def is_macos() -> bool:
    return sys.platform == "darwin"


def _require_macos() -> None:
    if not is_macos():
        raise RuntimeError("This function is only available on macOS")


def _is_text_file(path: str) -> bool:
    _, ext = os.path.splitext(path)
    if ext.lower() not in _TEXT_EXTENSIONS:
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            f.read(4096)
        return True
    except (OSError, UnicodeDecodeError):
        return False


def _read_file_content(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return ""


def spotlight_search(query: str, path: str = "/") -> list[Document]:
    _require_macos()

    from ragpipe import Document

    logger.info("Running Spotlight search: query=%r path=%s", query, path)

    try:
        result = subprocess.run(
            ["mdfind", "-name", query, "-onlyin", path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.error("mdfind command failed: %s", exc)
        return []

    if result.returncode != 0:
        logger.error(
            "mdfind returned non-zero exit code %d: %s", result.returncode, result.stderr.strip()
        )
        return []

    file_paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    documents: list[Document] = []
    for file_path in file_paths:
        if not os.path.isfile(file_path):
            continue
        if not _is_text_file(file_path):
            logger.debug("Skipping binary file: %s", file_path)
            continue

        content = _read_file_content(file_path)
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": "spotlight",
                    "query": query,
                    "path": file_path,
                    "search_root": path,
                },
            )
        )

    logger.info("Spotlight search returned %d documents", len(documents))
    return documents


def spotlight_index(path: str, name: str | None = None) -> list[Document]:
    _require_macos()

    from ragpipe import Document

    label = name or os.path.basename(os.path.abspath(path))
    logger.info("Running Spotlight index: path=%s name=%s", path, label)

    query = "kMDItemFSName == '*.{{py,js,ts,md,txt,json,yaml,yml,toml}}'"

    try:
        result = subprocess.run(
            ["mdfind", query, "-onlyin", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.error("mdfind command failed: %s", exc)
        return []

    if result.returncode != 0:
        logger.error(
            "mdfind returned non-zero exit code %d: %s", result.returncode, result.stderr.strip()
        )
        return []

    file_paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    documents: list[Document] = []
    for file_path in file_paths:
        if not os.path.isfile(file_path):
            continue
        if not _is_text_file(file_path):
            logger.debug("Skipping binary file: %s", file_path)
            continue

        content = _read_file_content(file_path)
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": "spotlight_index",
                    "index_name": label,
                    "path": file_path,
                    "index_root": path,
                },
            )
        )

    logger.info("Spotlight index returned %d documents", len(documents))
    return documents


def quick_look(path: str) -> str | None:
    _require_macos()

    if not os.path.exists(path):
        logger.warning("Path does not exist: %s", path)
        return None

    logger.info("Getting Quick Look metadata for: %s", path)

    try:
        result = subprocess.run(
            [
                "mdls",
                "-name",
                "kMDItemKind",
                "-name",
                "kMDItemFSSize",
                "-name",
                "kMDItemContentModificationDate",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.error("mdls command failed: %s", exc)
        return None

    if result.returncode != 0:
        logger.error(
            "mdls returned non-zero exit code %d: %s", result.returncode, result.stderr.strip()
        )
        return None

    output = result.stdout.strip()
    if not output:
        return None

    metadata: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"')
        friendly_key = {
            "kMDItemKind": "Kind",
            "kMDItemFSSize": "Size",
            "kMDItemContentModificationDate": "Modified",
        }.get(key, key)
        metadata[friendly_key] = value

    if not metadata:
        return output

    lines = [f"Quick Look: {os.path.basename(path)}"]
    for key, value in metadata.items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)
