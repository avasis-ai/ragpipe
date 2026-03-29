from __future__ import annotations

import logging
import re
from typing import Generator
from urllib.parse import urlparse

from ragpipe.pipeline import Document

logger = logging.getLogger("ragpipe.sources.web")

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class WebSource:
    def __init__(
        self,
        urls: str | list[str],
        headers: dict | None = None,
        timeout: float = 30.0,
        follow_redirects: bool = True,
        max_depth: int = 0,
        allowed_domains: list[str] | None = None,
    ):
        if isinstance(urls, str):
            urls = [urls]
        self.urls = urls
        self.headers = headers or {
            "User-Agent": "RAGPipe/0.1.0 (https://github.com/avasis-ai/ragpipe)"
        }
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.max_depth = max_depth
        self.allowed_domains = set(allowed_domains) if allowed_domains else None
        self._visited: set[str] = set()

    def extract(self) -> Generator[Document, None, None]:
        if not HAS_HTTPX:
            raise ImportError(
                "httpx is required for WebSource. Install with: pip install ragpipe[web]"
            )

        for url in self.urls:
            yield from self._crawl(url, depth=0)

    def _crawl(self, url: str, depth: int) -> Generator[Document, None, None]:
        if url in self._visited:
            return
        if depth > self.max_depth:
            return

        parsed = urlparse(url)
        if self.allowed_domains and parsed.hostname not in self.allowed_domains:
            return

        self._visited.add(url)

        try:
            with httpx.Client(
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=self.follow_redirects,
            ) as client:
                response = client.get(url)
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                yield from self._parse_html(url, response.text, depth)
            elif "text/plain" in content_type or "text/markdown" in content_type:
                yield Document(
                    content=response.text,
                    metadata={
                        "source": "web",
                        "url": url,
                        "content_type": content_type,
                        "status_code": response.status_code,
                    },
                )
            else:
                logger.debug("Skipping non-text content at %s (%s)", url, content_type)

        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)

    def _parse_html(
        self, url: str, html: str, depth: int
    ) -> Generator[Document, None, None]:
        if not HAS_BS4:
            raise ImportError(
                "beautifulsoup4 is required for HTML parsing. Install with: pip install ragpipe[web]"
            )

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text = soup.get_text(separator="\n", strip=True)

        if not text.strip():
            return

        yield Document(
            content=text,
            metadata={
                "source": "web",
                "url": url,
                "title": title,
                "content_type": "text/html",
            },
        )

        if depth < self.max_depth:
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if href.startswith("/"):
                    href = base_url + href
                elif not href.startswith(("http://", "https://")):
                    continue
                yield from self._crawl(href, depth + 1)
