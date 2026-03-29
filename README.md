<div align="center">

<img src="https://raw.githubusercontent.com/avasis-ai/ragpipe/main/.github/banner.svg" alt="RAGPipe" width="400">

**RAG in 3 functions.**

[![GitHub stars](https://img.shields.io/github/stars/avasis-ai/ragpipe?style=social)](https://github.com/avasis-ai/ragpipe)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-BSL_1.1-green.svg)](LICENSE)

*Sources → Transforms → Sinks for vector databases.*

Zero config. Works with Ollama, OpenAI, Qdrant, Pinecone, or just a JSON file.

</div>

---

## What is RAG?

**RAG (Retrieval-Augmented Generation)** is how you give an AI access to your own data. Instead of guessing answers, the AI first searches your documents, finds the relevant parts, and then generates an answer based on what it found.

The problem? Getting your data into a searchable format is painful. You need to:

1. **Extract** text from files, websites, code repos
2. **Chunk** it into smaller pieces (AI can't read a 100-page PDF at once)
3. **Embed** each chunk into numbers (so similar text gets similar numbers)
4. **Store** those embeddings in a vector database
5. **Search** when someone asks a question

RAGPipe does all 5 steps in one pipeline. You tell it where your data is and where it should go. That's it.

## Architecture

<img src="https://raw.githubusercontent.com/avasis-ai/ragpipe/main/.github/architecture.svg" alt="RAGPipe Architecture" width="600">

**How it works:** Your data flows through three stages — Sources pull data in, Transforms process it (clean, chunk, embed), and Sinks store the results in a vector database. When you query, RAGPipe searches the stored embeddings and returns the most relevant chunks.

---

## Install

```bash
pip install ragpipe[cli]
```

## The 3 functions

```python
import ragpipe

# 1. Ingest anything — files, git repos, web pages
ragpipe.ingest("./docs", sink="json", sink_path="./my_data.json")

# 2. Query your data
results = ragpipe.query("What is the refund policy?", sink_path="./my_data.json")
print(results[0].content)

# 3. Pipe — full control with the Pipeline API
pipeline = ragpipe.Pipeline()
pipeline.add_source(ragpipe.GitSource("https://github.com/owner/repo"))
pipeline.add_transform(ragpipe.RecursiveChunker(chunk_size=512))
pipeline.add_transform(ragpipe.AutoEmbed())
pipeline.add_sink(ragpipe.QdrantSink("my-repo"))
pipeline.run()
```

**That's it.** No boilerplate, no frameworks, no config files (unless you want them).

---

## CLI

```bash
# Create a starter pipeline config
ragpipe init

# Ingest a directory
ragpipe ingest ./docs

# Ingest a GitHub repo
ragpipe ingest https://github.com/owner/repo --embed

# Scrape a website
ragpipe ingest https://docs.example.com

# Query your data
ragpipe query "How does auth work?"

# Run a YAML pipeline
ragpipe run pipeline.yaml
```

### Smart-index any codebase

```bash
# Auto-detect language, ignore node_modules/.git/etc, chunk and store
ragpipe index .

# Watch for changes and auto-reindex
ragpipe watch . --chunk-size 256

# Start a local API server (for VSCode, curl, any tool)
ragpipe serve --port 7642
```

### Search with fzf

```bash
ragpipe search --fzf
```

### Git hooks — auto-index on every commit

```bash
ragpipe git hook .              # install
ragpipe git remove .            # remove
ragpipe git list .              # list installed
```

### VSCode integration

```bash
ragpipe vscode tasks .          # generates .vscode/tasks.json
ragpipe vscode settings         # generates .vscode/settings.json
```

### macOS — Spotlight integration

```bash
ragpipe macos spotlight "python files" --path ~/code
ragpipe macos index ~/projects/my-app
```

### Linux — systemd services

```bash
ragpipe linux service --install     # install as systemd service
ragpipe linux timer . --daily        # auto-index on schedule
```

### With embeddings (auto-detects Ollama → OpenAI → sentence-transformers)

```bash
ragpipe ingest ./docs --embed --sink qdrant --collection my-kb
ragpipe query "What features are in v2?" --sink qdrant
```

---

## YAML Pipelines

Drop a `pipeline.yaml` in your project and run it with one command:

```yaml
source:
  type: git
  repo_url: https://github.com/owner/repo
  file_patterns:
    - "src/**/*.py"
    - "docs/**/*.md"

transforms:
  - type: html_cleaner
  - type: recursive_chunker
    chunk_size: 512
    chunk_overlap: 64
  - type: auto_embed

sinks:
  - type: qdrant
    collection_name: my-repo
    url: http://localhost:6333
    vector_size: 384
```

```bash
ragpipe run pipeline.yaml
```

---

## Embedding Backends

`AutoEmbed` tries each backend in order and uses the first available:

| Priority | Backend | Setup |
|----------|---------|-------|
| 1 | **Ollama** (local) | `ollama pull nomic-embed-text` |
| 2 | **OpenAI** | Set `OPENAI_API_KEY` |
| 3 | **sentence-transformers** (local) | `pip install ragpipe[local]` |

Or point to any OpenAI-compatible API:

```python
ragpipe.ingest("./docs", embed=True, embed_base_url="http://localhost:11434/v1", embed_model="nomic-embed-text")
```

---

## Sources

| Source | Example | Description |
|--------|---------|-------------|
| `FileSource` | `FileSource("./docs")` | Local files and directories |
| `GitSource` | `GitSource("https://github.com/owner/repo")` | Clone git repos |
| `WebSource` | `WebSource("https://example.com")` | Scrape web pages |

## Transforms

| Transform | Description |
|-----------|-------------|
| `RecursiveChunker(chunk_size=512, chunk_overlap=64)` | Split text using hierarchical separators |
| `FixedSizeChunker(chunk_size=512)` | Split by fixed size |
| `SemanticChunker(embedding_model=...)` | Split by semantic similarity |
| `HTMLCleaner()` | Strip HTML to clean text |
| `PIIRemover()` | Redact emails, phones, SSN, etc. |
| `AutoEmbed()` | Zero-config embeddings (Ollama → OpenAI → ST) |
| `EmbeddingTransform(model=..., api_key=...)` | Explicit OpenAI-compatible embeddings |

## Sinks

| Sink | Example |
|------|---------|
| `JSONSink(path="./out.json")` | Write to JSON file |
| `QdrantSink("collection", url="...", vector_size=384)` | Write to Qdrant |
| `PineconeSink("index", api_key="...", dimension=384)` | Write to Pinecone |

---

## Advanced Pipeline

```python
import ragpipe

pipeline = (
    ragpipe.Pipeline()
    .add_source(ragpipe.WebSource(
        urls=["https://docs.example.com"],
        max_depth=1,
        allowed_domains=["example.com"],
    ))
    .add_transform(ragpipe.HTMLCleaner())
    .add_transform(ragpipe.PIIRemover())
    .add_transform(ragpipe.RecursiveChunker(chunk_size=1024, chunk_overlap=128))
    .add_transform(ragpipe.AutoEmbed())
    .add_sink(ragpipe.QdrantSink(
        collection_name="example-docs",
        url="http://localhost:6333",
        vector_size=384,
    ))
)

stats = pipeline.run()
# {'extracted': 47, 'transformed': 312, 'written': 312}
```

### Dry run (preview without writing)

```python
docs = pipeline.dry_run()
for doc in docs:
    print(f"[{doc.metadata.get('path', '?')}] {doc.char_count} chars")
```

---

## Why RAGPipe?

- **3 functions.** `ingest()`, `query()`, `pipe()`. That's the whole API.
- **Zero config.** Auto-detects files, auto-embeds with whatever you have installed.
- **YAML pipelines.** Declarative configs like `docker-compose` for RAG.
- **Beautiful CLI.** Rich progress bars, tables, and status spinners.
- **Any source.** Files, git repos, web pages — one interface.
- **Any vector DB.** Qdrant, Pinecone, or just a JSON file.
- **Local-first.** Works with Ollama and sentence-transformers. No API keys needed.
- **Typed.** Full type annotations, mypy-friendly.

---

## License

Business Source License 1.1 (BSL 1.1). **Non-competing use is Apache 2.0.** See [LICENSE](./LICENSE).

---

<div align="center">

Built by [avasis-ai](https://github.com/avasis-ai)

</div>
