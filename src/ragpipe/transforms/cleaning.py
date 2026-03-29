from __future__ import annotations

import logging
import re
from typing import Generator

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.transforms.cleaning")

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class HTMLCleaner:
    def __init__(
        self,
        remove_tags: list[str] | None = None,
        keep_tags: list[str] | None = None,
        strip_attributes: bool = True,
        min_text_length: int = 5,
    ):
        self.remove_tags = remove_tags or [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "noscript",
        ]
        self.keep_tags = keep_tags
        self.strip_attributes = strip_attributes
        self.min_text_length = min_text_length

    def transform(self, doc: Document) -> list[Document]:
        content = doc.content

        if "<" not in content and ">" not in content:
            return [doc]

        if not HAS_BS4:
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()
            return [Document(content=content, metadata=doc.metadata)]

        soup = BeautifulSoup(content, "html.parser")

        if self.remove_tags:
            for tag_name in self.remove_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()

        if self.strip_attributes:
            for tag in soup.find_all(True):
                tag.attrs = {
                    k: v
                    for k, v in tag.attrs.items()
                    if k in ("href", "src", "alt", "title")
                }

        cleaned = soup.get_text(separator="\n", strip=True)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        if len(cleaned) < self.min_text_length:
            return []

        meta = dict(doc.metadata)
        meta["cleaned"] = True
        meta["original_length"] = len(doc.content)

        return [Document(content=cleaned, metadata=meta)]


class PIIRemover:
    DEFAULT_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "ipv6": r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
    }

    def __init__(
        self,
        patterns: dict[str, str] | None = None,
        redact_char: str = "[REDACTED]",
        custom_patterns: list[tuple[str, str]] | None = None,
        keep_fields: list[str] | None = None,
    ):
        self.patterns = patterns or dict(self.DEFAULT_PATTERNS)
        self.redact_char = redact_char
        self.keep_fields = set(keep_fields or [])
        self._compiled: dict[str, re.Pattern] = {}
        self._counts: dict[str, int] = {}

        if custom_patterns:
            for name, pattern in custom_patterns:
                self.patterns[name] = pattern

    def transform(self, doc: Document) -> list[Document]:
        content = doc.content
        counts: dict[str, int] = {}

        for name, pattern in self.patterns.items():
            if name in self.keep_fields:
                continue
            if name not in self._compiled:
                self._compiled[name] = re.compile(pattern)
            matches = self._compiled[name].findall(content)
            if matches:
                counts[name] = len(matches)
                content = self._compiled[name].sub(self.redact_char, content)

        self._counts = counts

        if counts:
            logger.debug("PIIRemover found: %s", counts)

        meta = dict(doc.metadata)
        meta["pii_removed"] = counts

        return [Document(content=content, metadata=meta)]
