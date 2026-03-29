import tempfile
from pathlib import Path

from ragpipe.sources.file_source import FileSource
from ragpipe.pipeline import Document


def _write_temp(content: str, suffix: str = ".txt") -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def test_file_source_single_file():
    path = _write_temp("hello world\nhow are you")
    try:
        source = FileSource(paths=[str(path)])
        docs = list(source.extract())
        assert len(docs) == 1
        assert "hello world" in docs[0].content
        assert docs[0].metadata["source"] == "file"
        assert docs[0].metadata["filename"] == path.name
    finally:
        path.unlink()


def test_file_source_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "a.txt").write_text("file a")
        (Path(tmpdir) / "b.txt").write_text("file b")
        (Path(tmpdir) / "c.py").write_text("file c")

        source = FileSource(paths=[tmpdir], file_extensions=[".txt"])
        docs = list(source.extract())
        assert len(docs) == 2
        contents = {d.content for d in docs}
        assert "file a" in contents
        assert "file b" in contents


def test_file_source_non_recursive():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "root.txt").write_text("root")
        subdir = Path(tmpdir) / "sub"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        source = FileSource(paths=[tmpdir], recursive=False)
        docs = list(source.extract())
        assert len(docs) == 1
        assert docs[0].content == "root"


def test_file_source_recursive():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "root.txt").write_text("root")
        subdir = Path(tmpdir) / "sub"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        source = FileSource(paths=[tmpdir], recursive=True)
        docs = list(source.extract())
        assert len(docs) == 2


def test_file_source_nonexistent():
    source = FileSource(paths=["/nonexistent/path/foo.txt"])
    docs = list(source.extract())
    assert len(docs) == 0


def test_file_source_empty_file():
    path = _write_temp("   \n\n  ")
    try:
        source = FileSource(paths=[str(path)])
        docs = list(source.extract())
        assert len(docs) == 0
    finally:
        path.unlink()
