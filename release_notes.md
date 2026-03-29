RAG in 3 functions. Ingest any data source into vector databases.

## Install
```bash
pip install ragpipe-ai
```

## Quick Start
```python
import ragpipe

ragpipe.ingest("./docs")
results = ragpipe.query("How does auth work?")
```

## Features
- **3-function API**: `ragpipe.ingest()`, `ragpipe.query()`, `ragpipe.Pipeline()`
- **AutoEmbed**: Zero-config embeddings (Ollama → OpenAI → sentence-transformers)
- **YAML pipelines**: Config-driven RAG with `ragpipe run pipeline.yaml`
- **Typer + Rich CLI**: 12 commands with beautiful terminal output
- **Smart indexer**: Auto-detects project type, language-aware ignore patterns
- **REST API**: Built-in search server on port 7642
- **Git hooks**: Post-commit auto-indexing
- **fzf integration**: Fuzzy search through indexed code
