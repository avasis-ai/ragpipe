import json
import tempfile
from pathlib import Path

from ragpipe.sinks.json_sink import JSONSink
from ragpipe.pipeline import Document


def test_json_sink_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "out.json"
        sink = JSONSink(output_path=str(path))

        docs = [
            Document(content="hello world", metadata={"source": "test"}),
            Document(content="foo bar", metadata={"source": "test2"}),
        ]

        written = sink.write(docs)
        assert written == 2

        data = json.loads(path.read_text())
        assert len(data) == 2
        assert data[0]["content"] == "hello world"
        assert data[1]["content"] == "foo bar"
        assert "embedding" not in data[0]


def test_json_sink_with_embeddings():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "out.json"
        sink = JSONSink(output_path=str(path), include_embeddings=True)

        docs = [Document(content="test", embedding=[0.1, 0.2, 0.3])]
        sink.write(docs)

        data = json.loads(path.read_text())
        assert data[0]["embedding"] == [0.1, 0.2, 0.3]


def test_json_sink_append():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "out.json"

        sink = JSONSink(output_path=str(path))
        sink.write([Document(content="first")])

        sink = JSONSink(output_path=str(path), append=True)
        sink.write([Document(content="second")])

        data = json.loads(path.read_text())
        assert len(data) == 2
        assert data[0]["content"] == "first"
        assert data[1]["content"] == "second"


def test_json_sink_creates_dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sub" / "dir" / "out.json"
        sink = JSONSink(output_path=str(path))
        sink.write([Document(content="nested")])

        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data) == 1


def test_json_sink_skip_no_embedding():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "out.json"
        sink = JSONSink(output_path=str(path), include_embeddings=True)

        docs = [
            Document(content="with emb", embedding=[0.1]),
            Document(content="no emb", embedding=None),
        ]
        sink.write(docs)

        data = json.loads(path.read_text())
        assert "embedding" in data[0]
        assert "embedding" not in data[1]
