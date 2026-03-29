# RAGPipe

Declarative RAG data pipeline library for Python. Connect **Sources** to **Transforms** to **Sinks** with a clean, composable API.

```
Source → Transform → Transform → ... → Sink
```

## Features

- **Sources**: Git repos (GitHub API), local files, web scraping with crawling
- **Transforms**: Recursive/semantic/fixed-size chunking, HTML cleaning, PII redaction, embeddings
- **Sinks**: Qdrant, Pinecone, local JSON
- **Declarative API**: Chain sources, transforms, and sinks into pipelines
- **Dry run**: Preview output without writing to any sink
- **Zero magic**: Pure Python, no hidden state, fully inspectable

## Install

```bash
pip install ragpipe

# With extras
pip install ragpipe[web]          # WebSource (beautifulsoup4)
pip install ragpipe[qdrant]       # QdrantSink
pip install ragpipe[pinecone]     # PineconeSink
pip install ragpipe[embeddings]   # SemanticChunker with OpenAI embeddings
pip install ragpipe[all]          # Everything
```

## Quick Start

### Ingest a Git repo into Qdrant

```python
from ragpipe import Pipeline, GitSource, RecursiveChunker, EmbeddingTransform, QdrantSink

pipeline = (
    Pipeline()
    .add_source(GitSource(
        repo_url="https://github.com/owner/repo",
        branch="main",
        file_patterns=["src/**/*.py", "docs/**/*.md"],
    ))
    .add_transform(RecursiveChunker(chunk_size=512, chunk_overlap=64))
    .add_transform(EmbeddingTransform(
        model="text-embedding-3-small",
        api_key="sk-...",
    ))
    .add_sink(QdrantSink(
        collection_name="my-repo",
        url="http://localhost:6333",
        vector_size=1536,
    ))
)

stats = pipeline.run()
print(stats)  # {'extracted': 47, 'transformed': 312, 'written': 312}
```

### Scrape a website and save to JSON

```python
from ragpipe import Pipeline, WebSource, HTMLCleaner, RecursiveChunker, JSONSink

pipeline = (
    Pipeline()
    .add_source(WebSource(
        urls=["https://example.com/docs"],
        max_depth=1,
    ))
    .add_transform(HTMLCleaner())
    .add_transform(RecursiveChunker(chunk_size=1024))
    .add_sink(JSONSink(output_path="./output.json", append=True))
)

pipeline.run()
```

### Ingest local files with PII removal

```python
from ragpipe import Pipeline, FileSource, PIIRemover, RecursiveChunker, JSONSink

pipeline = (
    Pipeline()
    .add_source(FileSource(
        paths=["./documents/"],
        file_extensions=[".pdf", ".txt", ".md"],
        recursive=True,
    ))
    .add_transform(PIIRemover())
    .add_transform(RecursiveChunker(chunk_size=256))
    .add_sink(JSONSink(output_path="./cleaned_chunks.json"))
)

pipeline.run()
```

### Semantic chunking

```python
from ragpipe import Pipeline, FileSource, SemanticChunker, QdrantSink

pipeline = (
    Pipeline()
    .add_source(FileSource(paths=["./long_document.txt"]))
    .add_transform(SemanticChunker(
        min_chunk_size=100,
        max_chunk_size=1000,
        embedding_model="text-embedding-3-small",
        api_key="sk-...",
    ))
    .add_sink(QdrantSink(collection_name="docs", vector_size=1536))
)

pipeline.run()
```

### Dry run (preview without writing)

```python
from ragpipe import Pipeline, GitSource, RecursiveChunker

pipeline = (
    Pipeline()
    .add_source(GitSource(repo_url="https://github.com/owner/repo"))
    .add_transform(RecursiveChunker(chunk_size=256))
)

docs = pipeline.dry_run()
for doc in docs:
    print(f"[{doc.metadata['path']}] ({doc.char_count} chars)")
    print(doc.content[:100] + "...")
```

## API Reference

### Sources

| Source | Description |
|--------|-------------|
| `GitSource(repo_url, branch, file_patterns, token, shallow)` | Clone a git repo and extract text files |
| `FileSource(paths, recursive, file_extensions)` | Read local files and directories |
| `WebSource(urls, max_depth, allowed_domains)` | Scrape web pages with optional crawling |

### Transforms

| Transform | Description |
|-----------|-------------|
| `RecursiveChunker(chunk_size, chunk_overlap)` | Split text using hierarchical separators |
| `FixedSizeChunker(chunk_size, chunk_overlap, separator)` | Split by fixed token/char count |
| `SemanticChunker(min_chunk_size, max_chunk_size, embedding_model)` | Split by semantic similarity of sentences |
| `HTMLCleaner(remove_tags, strip_attributes)` | Strip HTML to clean text |
| `PIIRemover(patterns, redact_char)` | Detect and redact PII (email, phone, SSN, etc.) |
| `EmbeddingTransform(model, api_key, base_url)` | Generate embeddings via OpenAI-compatible API |

### Sinks

| Sink | Description |
|------|-------------|
| `JSONSink(output_path, append, include_embeddings)` | Write documents to a JSON file |
| `QdrantSink(collection_name, url, vector_size)` | Write to Qdrant vector database |
| `PineconeSink(index_name, api_key, dimension)` | Write to Pinecone vector database |

### Document

Every document flowing through the pipeline is a `Document`:

```python
@dataclass
class Document:
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None
    id: str  # auto-generated SHA-256 hash
```

## Pipeline

```python
pipeline = Pipeline()
pipeline.add_source(source)
pipeline.add_transform(transform)
pipeline.add_sink(sink)

stats = pipeline.run()       # Execute and write to sinks
docs = pipeline.dry_run()    # Preview without writing
```

Returns `{"extracted": N, "transformed": N, "written": N}`.

## Configuration

### Embedding providers

`EmbeddingTransform` and `SemanticChunker` support any OpenAI-compatible API:

```python
# OpenAI
EmbeddingTransform(model="text-embedding-3-small", api_key="sk-...")

# Ollama (local)
EmbeddingTransform(model="nomic-embed-text", base_url="http://localhost:11434/v1")

# Any OpenAI-compatible endpoint
EmbeddingTransform(
    model="bge-large-en",
    api_key="...",
    base_url="https://your-endpoint/v1",
)
```

### Qdrant

```python
QdrantSink(
    collection_name="my-data",
    url="http://localhost:6333",        # or cloud URL
    api_key="...",                       # optional, for cloud
    vector_size=1536,
    distance="cosine",                   # cosine, euclidean, dot
)
```

### Pinecone

```python
PineconeSink(
    index_name="my-data",
    api_key="...",
    dimension=1536,
    metric="cosine",
    create_index=True,                  # auto-create if missing
)
```

## License

This project uses the **Business Source License 1.1 (BSL 1.1)**. See [LICENSE](./LICENSE) for full terms.

**Non-competing use is licensed under Apache 2.0.** If you are not using RAGPipe to compete with avasis-ai's products or services, you may use it under the Apache 2.0 license.
