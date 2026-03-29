from ragpipe.pipeline import Document, Pipeline


def test_document_creation():
    doc = Document(content="Hello world", metadata={"source": "test"})
    assert doc.content == "Hello world"
    assert doc.metadata["source"] == "test"
    assert len(doc.id) == 16
    assert doc.char_count == 11


def test_document_deterministic_id():
    d1 = Document(content="abc", metadata={"x": 1})
    d2 = Document(content="abc", metadata={"x": 1})
    assert d1.id == d2.id


def test_document_different_ids():
    d1 = Document(content="abc", metadata={"x": 1})
    d2 = Document(content="abc", metadata={"x": 2})
    assert d1.id != d2.id


def test_pipeline_no_source():
    p = Pipeline()
    try:
        p.run()
        assert False, "Should have raised"
    except ValueError as e:
        assert "Source" in str(e)


def test_pipeline_dry_run():
    class FakeSource:
        def extract(self):
            yield Document(content="hello")
            yield Document(content="world")

    p = Pipeline(source=FakeSource())
    docs = p.dry_run()
    assert len(docs) == 2
    assert docs[0].content == "hello"


def test_pipeline_transform_chain():
    class FakeSource:
        def extract(self):
            yield Document(content="alpha beta gamma delta epsilon zeta")

    class SplitTransform:
        def transform(self, doc):
            words = doc.content.split()
            return [Document(content=w, metadata={"index": i}) for i, w in enumerate(words)]

    class UppercaseTransform:
        def transform(self, doc):
            return [Document(content=doc.content.upper(), metadata=doc.metadata)]

    p = Pipeline(source=FakeSource())
    p.add_transform(SplitTransform())
    p.add_transform(UppercaseTransform())

    docs = p.dry_run()
    assert len(docs) == 6
    assert docs[0].content == "ALPHA"
    assert docs[-1].content == "ZETA"


def test_pipeline_run_stats():
    class CountingSource:
        def extract(self):
            for i in range(3):
                yield Document(content=f"doc-{i}")

    class PassTransform:
        def transform(self, doc):
            return [doc]

    written_docs = []

    class CountingSink:
        def write(self, docs):
            written_docs.extend(docs)
            return len(docs)

    sink = CountingSink()
    p = Pipeline(source=CountingSource())
    p.add_transform(PassTransform())
    p.add_sink(sink)

    stats = p.run()
    assert stats["extracted"] == 3
    assert stats["transformed"] == 3
    assert stats["written"] == 3
    assert len(written_docs) == 3


def test_pipeline_multiple_sinks():
    class FakeSource:
        def extract(self):
            yield Document(content="test")

    sink1_data = []
    sink2_data = []

    class Sink1:
        def write(self, docs):
            sink1_data.extend(docs)
            return len(docs)

    class Sink2:
        def write(self, docs):
            sink2_data.extend(docs)
            return len(docs)

    p = Pipeline(source=FakeSource())
    p.add_sink(Sink1())
    p.add_sink(Sink2())
    p.run()

    assert len(sink1_data) == 1
    assert len(sink2_data) == 1


def test_pipeline_fluent_api():
    class FakeSource:
        def extract(self):
            yield Document(content="x")

    class NoopTransform:
        def transform(self, doc):
            return [doc]

    class NoopSink:
        def __init__(self):
            self.docs = []

        def write(self, docs):
            self.docs = docs
            return len(docs)

    sink = NoopSink()
    p = Pipeline().add_source(FakeSource()).add_transform(NoopTransform()).add_sink(sink)
    p.run()
    assert len(sink.docs) == 1
