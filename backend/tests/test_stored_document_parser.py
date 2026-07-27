from types import SimpleNamespace

import pytest
from docling.datamodel.base_models import InputFormat

from app.documents.models import DocumentType
from app.documents.source_storage import LocalSourceStorage
from app.documents.stored_document_parser import (
    MissingSourceKeyError,
    StoredDocumentParser,
    StoredDocumentParserError,
)


def test_stored_pdf_returns_markdown_and_document(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    storage = LocalSourceStorage(str(tmp_path))
    key = storage.save(b"pdf", ".pdf")
    document = SimpleNamespace(export_to_markdown=lambda: "# Parsed")
    converter_options = {}

    def fake_converter(**options):
        converter_options.update(options)
        return SimpleNamespace(convert=lambda _: SimpleNamespace(document=document))

    monkeypatch.setattr("app.documents.stored_document_parser.DocumentConverter", fake_converter)
    result = StoredDocumentParser(storage).parse(key, DocumentType.PDF)
    assert result.text == "# Parsed"
    assert result.document is document
    pipeline_options = converter_options["format_options"][InputFormat.PDF].pipeline_options
    assert pipeline_options.do_ocr is False


def test_stored_text_and_markdown_preserve_content(tmp_path) -> None:
    storage = LocalSourceStorage(str(tmp_path))
    parser = StoredDocumentParser(storage)
    assert parser.parse(storage.save(b"plain", ".txt"), DocumentType.TEXT).text == "plain"
    assert parser.parse(storage.save(b"# note", ".md"), DocumentType.MARKDOWN).text == "# note"


def test_missing_or_corrupted_source_has_safe_error(tmp_path) -> None:
    parser = StoredDocumentParser(LocalSourceStorage(str(tmp_path)))
    with pytest.raises(MissingSourceKeyError):
        parser.parse(None, DocumentType.PDF)
    with pytest.raises(StoredDocumentParserError) as error:
        parser.parse("missing.pdf", DocumentType.PDF)
    assert "missing.pdf" not in str(error.value)
