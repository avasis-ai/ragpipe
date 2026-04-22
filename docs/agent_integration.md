# Agent Integration with RAGPipe

RAGPipe is designed to be perfect for AI agents that need to access and understand large knowledge bases. This guide shows how to integrate RAGPipe into your agent workflows.

## Quick Start

```python
import ragpipe

# Ingest your knowledge base
ragpipe.ingest(
    "./docs",
    sink="qdrant",
    collection="my-knowledge"
)

# Query from your agent
def ask_agent(question: str) -> str:
    results = ragpipe.query(
        question,
        sink="qdrant",
        collection="my-knowledge",
        top_k=3
    )

    context = "\n\n".join([r.content for r in results])

    # Send to your LLM with context
    prompt = f"""
    Context:
    {context}

    Question: {question}
    """

    return llm.complete(prompt)
```

## Use Cases for Agents

### 1. Codebase Understanding

Agents can query your entire codebase to understand context before making changes:

```python
# Index your code
ragpipe.ingest(
    "./src",
    transforms=[
        ragpipe.RecursiveChunker(chunk_size=512),
        ragpipe.AutoEmbed()
    ],
    sink="qdrant"
)

# Agent queries before making changes
context = ragpipe.query("How does authentication work?", top_k=5)
# Agent uses this context to understand existing patterns
```

### 2. Documentation Assistant

Build agents that can answer questions about your docs:

```python
# Ingest all documentation
ragpipe.ingest(
    ragpipe.GitSource("https://github.com/owner/repo"),
    transforms=[
        ragpipe.HTMLCleaner(),
        ragpipe.RecursiveChunker(chunk_size=768),
        ragpipe.AutoEmbed()
    ],
    sink="qdrant"
)

# Agent answers user questions
def answer_docs_question(question: str) -> str:
    results = ragpipe.query(question, top_k=3)

    response = f"""
    Based on the documentation:

    {''.join([f"- {r.content}\n" for r in results])}

    In summary: {summarize(results, question)}
    """

    return response
```

### 3. Continuous Learning

Agents can continuously update their knowledge base:

```python
def on_new_data(file_path: str):
    # Ingest new data immediately
    ragpipe.ingest(
        file_path,
        sink="qdrant",
        collection="live-knowledge"
    )

    # Agent now knows about this data
    print("Knowledge base updated. Agent is smarter now.")
```

### 4. Multi-Agent Coordination

Multiple agents can share a knowledge base:

```python
# Shared knowledge index
ragpipe.ingest(
    "./shared-knowledge",
    sink="qdrant",
    collection="team-knowledge"
)

# All agents query the same knowledge base
def expert_agent(question: str, expertise: str):
    results = ragpipe.query(
        f"{question} (focus on {expertise})",
        sink="qdrant",
        collection="team-knowledge",
        top_k=5
    )

    # Specialized agent reasoning
    return specialized_reasoning(results, expertise)
```

## Agent-Friendly Features

### Zero Configuration

```python
# Just works - no setup needed
ragpipe.ingest("./docs")
ragpipe.query("How do I deploy?")
```

### Fast Queries

```python
# Sub-second queries for real-time agent responses
results = ragpipe.query(question, top_k=3)
# Typical: 50-200ms on Qdrant with 100K docs
```

### Multiple Embedding Models

```python
# Use different models for different use cases

# Fast for chat agents
ragpipe.ingest(
    "./docs",
    embed_model="sentence-transformers/all-MiniLM-L6-v2"  # Fast
)

# Accurate for code agents
ragpipe.ingest(
    "./src",
    embed_model="jinaai/jina-embeddings-v2-base-code"  # Code-aware
)
```

### Incremental Updates

```python
# Agents can update knowledge incrementally
ragpipe.ingest(
    "./new-docs",
    sink="qdrant",
    collection="my-knowledge",
    mode="append"  # Don't re-index everything
)
```

## Integration Patterns

### Pattern 1: Context-Enhanced Generation

```python
def agent_with_rag(query: str) -> str:
    # 1. Retrieve relevant context
    context = ragpipe.query(query, top_k=5)

    # 2. Build prompt with context
    prompt = f"""
    You are an AI assistant with access to a knowledge base.

    RELEVANT CONTEXT:
    {format_context(context)}

    USER QUESTION:
    {query}

    Answer based on the context above. If the context doesn't contain enough information, say so.
    """

    # 3. Generate response
    return llm.complete(prompt)
```

### Pattern 2: Fact-Checking Agent

```python
def fact_check_agent(statement: str) -> dict:
    # Retrieve facts
    facts = ragpipe.query(extract_key_terms(statement), top_k=10)

    # Verify statement against facts
    verification = verify_against_facts(statement, facts)

    return {
        "statement": statement,
        "is_factual": verification.is_accurate,
        "confidence": verification.confidence,
        "supporting_evidence": [f.content for f in verification.supporting_facts]
    }
```

### Pattern 3: Exploration Agent

```python
def exploration_agent(topic: str) -> list[str]:
    # Explore related topics
    related = ragpipe.query(topic, top_k=20)

    # Extract key themes
    themes = extract_themes(related)

    # Return exploration paths
    return [f"{theme} - explore this topic" for theme in themes]
```

## Performance Tips for Agents

### 1. Use Efficient Chunk Sizes

```python
# For chat agents: smaller chunks, more context
ragpipe.ingest(
    docs,
    transforms=[ragpipe.RecursiveChunker(chunk_size=256)]
)

# For code agents: larger chunks, less noise
ragpipe.ingest(
    code,
    transforms=[ragpipe.RecursiveChunker(chunk_size=1024)]
)
```

### 2. Cache Common Queries

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(question: str) -> list:
    return ragpipe.query(question, top_k=5)
```

### 3. Batch Queries

```python
# Agent can retrieve multiple contexts at once
def agent_research(questions: list[str]) -> dict[str, list]:
    return {q: ragpipe.query(q) for q in questions}
```

## Full Example: Autonomous Documentation Agent

```python
import ragpipe
from some_llm_library import LLM

class DocumentationAgent:
    def __init__(self, docs_path: str):
        # Initialize knowledge base
        ragpipe.ingest(
            docs_path,
            transforms=[
                ragpipe.HTMLCleaner(),
                ragpipe.RecursiveChunker(chunk_size=768),
                ragpipe.AutoEmbed()
            ],
            sink="qdrant"
        )

        self.llm = LLM(model="gpt-4")

    def ask(self, question: str) -> str:
        # Retrieve context
        context = ragpipe.query(question, top_k=5)

        # Generate response
        prompt = self._build_prompt(question, context)
        response = self.llm.complete(prompt)

        return response

    def _build_prompt(self, question: str, context: list) -> str:
        return f"""
        You are a documentation assistant.

        RELEVANT DOCS:
        {self._format_context(context)}

        QUESTION:
        {question}

        Provide a helpful answer based on the documentation above.
        Include code examples if relevant.
        """

    def _format_context(self, context: list) -> str:
        return "\n\n".join([f"- {doc.content}" for doc in context])

# Usage
agent = DocumentationAgent("./docs")
print(agent.ask("How do I deploy to production?"))
```

## Next Steps

- See [Examples](../examples/) for more patterns
- Check [Pipeline API](pipeline.md) for advanced usage
- Review [Sources](sources.md), [Transforms](transforms.md), and [Sinks](sinks.md)
