from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Generator

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.sources.git")


class GitSource:
    def __init__(
        self,
        repo_url: str,
        branch: str = "main",
        file_patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
        token: str | None = None,
        shallow: bool = True,
    ):
        self.repo_url = repo_url
        self.branch = branch
        self.file_patterns = file_patterns or []
        self.ignore_patterns = set(
            ignore_patterns
            or [".git", "__pycache__", "node_modules", ".next", "dist", "build"]
        )
        self.token = token
        self.shallow = shallow

        if self.token and "@" not in self.repo_url:
            from urllib.parse import urlparse

            parsed = urlparse(self.repo_url)
            if parsed.hostname in ("github.com", "api.github.com"):
                self.repo_url = self.repo_url.replace("://", f"://{self.token}@")

    def extract(self) -> Generator[Document, None, None]:
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "repo"
            cmd = ["git", "clone"]
            if self.shallow:
                cmd.extend(["--depth", "1", "--branch", self.branch])
            cmd.append(self.repo_url)
            cmd.append(str(clone_path))

            logger.info(
                "Cloning %s (branch=%s, shallow=%s)",
                self.repo_url,
                self.branch,
                self.shallow,
            )
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error("Clone failed: %s", result.stderr)
                return

            if not clone_path.exists():
                return

            text_extensions = {
                ".py",
                ".js",
                ".ts",
                ".tsx",
                ".jsx",
                ".rs",
                ".go",
                ".java",
                ".c",
                ".cpp",
                ".h",
                ".hpp",
                ".md",
                ".txt",
                ".rst",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".cfg",
                ".ini",
                ".sh",
                ".bash",
                ".zsh",
                ".fish",
                ".sql",
                ".html",
                ".css",
                ".scss",
                ".less",
                ".xml",
                ".csv",
                ".tf",
                ".hcl",
                ".proto",
                ".graphql",
            }

            for root, dirs, files in os.walk(clone_path):
                dirs[:] = [d for d in dirs if d not in self.ignore_patterns]

                for fname in sorted(files):
                    fpath = Path(root) / fname
                    rel_path = fpath.relative_to(clone_path)

                    if self.file_patterns:
                        matches = any(rel_path.match(p) for p in self.file_patterns)
                        if not matches:
                            continue

                    if fpath.suffix.lower() not in text_extensions:
                        continue

                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        if not content.strip():
                            continue

                        yield Document(
                            content=content,
                            metadata={
                                "source": "git",
                                "repo": self.repo_url.split("//")[-1].split("@")[-1],
                                "branch": self.branch,
                                "path": str(rel_path),
                                "filename": fname,
                                "extension": fpath.suffix.lower(),
                            },
                        )
                    except Exception as e:
                        logger.warning("Failed to read %s: %s", rel_path, e)
