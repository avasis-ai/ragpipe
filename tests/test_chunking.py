from ragpipe.transforms.chunking import RecursiveChunker, FixedSizeChunker
from ragpipe.pipeline import Document


def test_recursive_chunker_small_text():
    doc = Document(content="Short text.", metadata={"path": "test.py"})
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=0)
    result = chunker.transform(doc)
    assert len(result) == 1
    assert result[0].content == "Short text."
    assert result[0].metadata["chunk_type"] == "recursive"


def test_recursive_chunker_splits():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    doc = Document(content=text)
    chunker = RecursiveChunker(chunk_size=30, chunk_overlap=0)
    result = chunker.transform(doc)
    assert len(result) >= 2
    for r in result:
        assert "chunk_type" in r.metadata
        assert r.metadata["chunk_type"] == "recursive"


def test_recursive_chunker_overlap():
    text = "A" * 200
    doc = Document(content=text)
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=20)
    result = chunker.transform(doc)
    assert len(result) >= 2


def test_fixed_size_chunker():
    text = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8"
    doc = Document(content=text)
    chunker = FixedSizeChunker(chunk_size=20, chunk_overlap=0, separator="\n")
    result = chunker.transform(doc)
    assert len(result) >= 2
    for r in result:
        assert r.metadata["chunk_type"] == "fixed"


def test_fixed_size_chunker_with_overlap():
    text = "\n".join([f"line {i}" for i in range(20)])
    doc = Document(content=text)
    chunker = FixedSizeChunker(chunk_size=30, chunk_overlap=10, separator="\n")
    result = chunker.transform(doc)
    assert len(result) >= 1


def test_chunker_preserves_metadata():
    doc = Document(content="Test content here.", metadata={"source": "git", "path": "main.py"})
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=0)
    result = chunker.transform(doc)
    assert result[0].metadata["source"] == "git"
    assert result[0].metadata["path"] == "main.py"


def test_chunker_min_chunk_size():
    doc = Document(content="Hi")
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=0, min_chunk_size=10)
    result = chunker.transform(doc)
    assert len(result) == 0

    doc2 = Document(content="This is a reasonably long sentence to keep.")
    chunker2 = RecursiveChunker(chunk_size=100, chunk_overlap=0, min_chunk_size=10)
    result2 = chunker2.transform(doc2)
    assert len(result2) == 1
