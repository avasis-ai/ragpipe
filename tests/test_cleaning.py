from ragpipe.transforms.cleaning import HTMLCleaner, PIIRemover
from ragpipe.pipeline import Document


def test_html_cleaner_basic():
    html = "<html><body><h1>Title</h1><p>Hello world</p><script>alert('x')</script></body></html>"
    doc = Document(content=html)
    cleaner = HTMLCleaner()
    result = cleaner.transform(doc)
    assert len(result) == 1
    text = result[0].content
    assert "Title" in text
    assert "Hello world" in text


def test_html_cleaner_non_html_passthrough():
    doc = Document(content="Plain text without HTML", metadata={"path": "test.txt"})
    cleaner = HTMLCleaner()
    result = cleaner.transform(doc)
    assert len(result) == 1
    assert result[0].content == "Plain text without HTML"


def test_html_cleaner_strips_attributes():
    html = '<div class="foo" id="bar"><a href="http://example.com">Link to page</a></div>'
    doc = Document(content=html)
    cleaner = HTMLCleaner(strip_attributes=True, min_text_length=1)
    result = cleaner.transform(doc)
    assert len(result) == 1
    assert "Link to page" in result[0].content


def test_pii_remover_email():
    text = "Contact us at support@example.com for help."
    doc = Document(content=text)
    remover = PIIRemover()
    result = remover.transform(doc)
    assert "support@example.com" not in result[0].content
    assert "[REDACTED]" in result[0].content
    assert result[0].metadata["pii_removed"]["email"] == 1


def test_pii_remover_phone():
    text = "Call me at 555-123-4567 or (555) 987 6543."
    doc = Document(content=text)
    remover = PIIRemover()
    result = remover.transform(doc)
    assert result[0].metadata["pii_removed"]["phone"] >= 1


def test_pii_remover_custom_pattern():
    text = "My API key is AKIAIOSFODNN7EXAMPLE"
    doc = Document(content=text)
    remover = PIIRemover(custom_patterns=[("aws_key", r"AKIA[A-Z0-9]{16}")])
    result = remover.transform(doc)
    assert "AKIAIOSFODNN7EXAMPLE" not in result[0].content
    assert result[0].metadata["pii_removed"]["aws_key"] == 1


def test_pii_remover_keep_fields():
    text = "Email test@example.com is safe."
    doc = Document(content=text)
    remover = PIIRemover(keep_fields=["email"])
    result = remover.transform(doc)
    assert "test@example.com" in result[0].content
    assert result[0].metadata.get("pii_removed") == {}


def test_pii_remover_no_pii():
    text = "No sensitive data here."
    doc = Document(content=text)
    remover = PIIRemover()
    result = remover.transform(doc)
    assert result[0].content == "No sensitive data here."
    assert result[0].metadata.get("pii_removed") == {}


def test_html_cleaner_min_length():
    html = "<p>x</p>"
    doc = Document(content=html)
    cleaner = HTMLCleaner(min_text_length=5)
    result = cleaner.transform(doc)
    assert len(result) == 0
