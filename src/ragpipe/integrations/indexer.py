from __future__ import annotations

import logging
import os
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.integrations.indexer")

MARKER_FILES: dict[str, list[str]] = {
    "python": ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
    "node": ["package.json", "tsconfig.json"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "java": ["pom.xml", "build.gradle"],
    "ruby": ["Gemfile"],
}

IGNORE_PATTERNS: dict[str, list[str]] = {
    "python": [
        "__pycache__",
        ".venv",
        "venv",
        "*.pyc",
        ".eggs",
        "dist",
        "build",
        "*.egg-info",
        ".mypy_cache",
        ".tox",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".coverage",
        "htmlcov",
        ".hypothesis",
    ],
    "node": [
        "node_modules",
        ".next",
        "dist",
        "build",
        ".cache",
        ".turbo",
        ".nuxt",
        ".output",
        "coverage",
        ".vercel",
        ".netlify",
    ],
    "rust": ["target/"],
    "go": ["vendor/"],
    "java": [".gradle", "target/", "build/", ".idea", "*.class"],
    "ruby": ["vendor/", ".bundle/"],
}

ALWAYS_IGNORE: list[str] = [
    ".git",
    ".hg",
    ".svn",
    ".DS_Store",
    "Thumbs.db",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.lock",
    "*.log",
    ".env",
    ".env.*",
    "*.tar.gz",
    "*.zip",
    "*.whl",
]

TEXT_EXTENSIONS: set[str] = {
    ".py",
    ".pyi",
    ".pyx",
    ".pxd",
    ".txt",
    ".md",
    ".rst",
    ".cfg",
    ".ini",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".less",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".scala",
    ".rb",
    ".erb",
    ".haml",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".cxx",
    ".hxx",
    ".cs",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    ".sql",
    ".graphql",
    ".gql",
    ".proto",
    ".thrift",
    ".dockerfile",
    ".makefile",
    ".cmake",
    ".tf",
    ".hcl",
    ".vault",
    ".lua",
    ".vim",
    ".el",
    ".clj",
    ".cljs",
    ".ex",
    ".exs",
    ".hs",
    ".ml",
    ".mli",
    ".swift",
    ".dart",
    ".zig",
    ".r",
    ".R",
    ".jl",
    ".nim",
    ".v",
    ".sv",
    ".vhd",
    ".pyproject",
    ".gitignore",
    ".editorconfig",
    ".pre-commit-config",
    ".env",
    ".properties",
    ".gradle",
    ".sln",
    ".csproj",
    ".lock",
    ".cfg",
    ".conf",
    ".service",
}


def detect_project_type(path: str) -> str:
    root = Path(path).resolve()
    detected: dict[str, bool] = {}

    for proj_type, markers in MARKER_FILES.items():
        for marker in markers:
            if (root / marker).is_file():
                detected[proj_type] = True
                break

    if not detected and (root / ".git").is_dir():
        return "unknown"

    types = list(detected.keys())
    if len(types) == 1:
        return types[0]
    if len(types) > 1:
        return "mixed"
    return "unknown"


def _build_ignore_set(project_type: str, ignore_extra: list[str] | None) -> set[str]:
    patterns: list[str] = list(ALWAYS_IGNORE)
    if project_type in IGNORE_PATTERNS:
        patterns.extend(IGNORE_PATTERNS[project_type])
    if ignore_extra:
        patterns.extend(ignore_extra)
    return set(patterns)


def _is_ignored(name: str, ignore_set: set[str]) -> bool:
    return any(fnmatch(name, pat) for pat in ignore_set)


def _extension_to_language(ext: str) -> str:
    mapping: dict[str, str] = {
        ".py": "python",
        ".pyi": "python",
        ".pyx": "python",
        ".pxd": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".kt": "kotlin",
        ".scala": "scala",
        ".rb": "ruby",
        ".erb": "ruby",
        ".c": "c",
        ".h": "c",
        ".cpp": "c++",
        ".hpp": "c++",
        ".cc": "c++",
        ".cxx": "c++",
        ".hxx": "c++",
        ".cs": "c#",
        ".swift": "swift",
        ".dart": "dart",
        ".lua": "lua",
        ".hs": "haskell",
        ".ml": "ocaml",
        ".mli": "ocaml",
        ".clj": "clojure",
        ".cljs": "clojure",
        ".ex": "elixir",
        ".exs": "elixir",
        ".jl": "julia",
        ".nim": "nim",
        ".zig": "zig",
        ".r": "r",
        ".R": "r",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".fish": "shell",
        ".sql": "sql",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".vue": "vue",
        ".svelte": "svelte",
    }
    return mapping.get(ext.lower(), "unknown")


def _read_file_safe(fpath: Path, max_size: int) -> str | None:
    try:
        if fpath.stat().st_size > max_size:
            logger.debug("Skipping %s: exceeds max_file_size (%d)", fpath, max_size)
            return None
        return fpath.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        logger.warning("Failed to read %s: %s", fpath, e)
        return None


def index_project(
    path: str,
    ignore_extra: list[str] | None = None,
    max_file_size: int = 100_000,
) -> list[Document]:
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {path}")

    start = time.monotonic()
    project_type = detect_project_type(path)
    ignore_set = _build_ignore_set(project_type, ignore_extra)

    logger.info(
        "Indexing project at %s (detected: %s, ignore rules: %d)",
        root,
        project_type,
        len(ignore_set),
    )

    documents: list[Document] = []
    total_chars = 0
    languages_found: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_ignored(d, ignore_set)
            and not d.startswith(".")
            or d in {".github", ".vscode", ".idea"}
        ]

        for fname in sorted(filenames):
            if _is_ignored(fname, ignore_set):
                continue

            fpath = Path(dirpath) / fname
            ext = fpath.suffix

            if ext and ext.lower() not in TEXT_EXTENSIONS and not fname.startswith("."):
                continue

            content = _read_file_safe(fpath, max_file_size)
            if content is None or not content.strip():
                continue

            rel_path = fpath.relative_to(root)
            language = _extension_to_language(ext) if ext else "unknown"
            lines = content.count("\n") + 1
            size_bytes = fpath.stat().st_size

            languages_found.add(language)
            total_chars += len(content)

            metadata: dict[str, Any] = {
                "source": "index",
                "project_type": project_type,
                "language": language,
                "path": str(rel_path),
                "filename": fname,
                "extension": ext,
                "lines": lines,
                "size_bytes": size_bytes,
            }

            documents.append(Document(content=content, metadata=metadata))

    elapsed = time.monotonic() - start
    logger.info(
        "Index complete: %d files, %d chars, languages: %s, %.2fs",
        len(documents),
        total_chars,
        sorted(languages_found),
        elapsed,
    )

    return documents
