import tempfile
from dataclasses import dataclass
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.labels import DocItemLabel

from app.documents.models import DocumentType
from app.documents.source_storage import LocalSourceStorage, SourceNotFoundError, SourceStorageError


class StoredDocumentParserError(Exception):
    pass


class MissingSourceKeyError(StoredDocumentParserError):
    pass


@dataclass(frozen=True)
class StoredDocumentParseResult:
    text: str
    document: DoclingDocument


class StoredDocumentParser:
    def __init__(self, storage: LocalSourceStorage) -> None:
        self.storage = storage

    def parse(
        self, source_storage_key: str | None, document_type: DocumentType
    ) -> StoredDocumentParseResult:
        if not source_storage_key:
            raise MissingSourceKeyError("Stored source reference is missing.")
        try:
            content = self.storage.load(source_storage_key)
        except (SourceNotFoundError, SourceStorageError) as error:
            raise StoredDocumentParserError("Stored source could not be loaded.") from error
        if document_type in {DocumentType.TEXT, DocumentType.MARKDOWN}:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise StoredDocumentParserError("Stored source could not be read.") from error
            document = DoclingDocument(name=Path(source_storage_key).stem)
            document.add_text(label=DocItemLabel.TEXT, text=text)
            return StoredDocumentParseResult(text=text, document=document)
        if document_type is DocumentType.PDF:
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf") as source_file:
                    source_file.write(content)
                    source_file.flush()
                    document = (
                        DocumentConverter(
                            format_options={
                                InputFormat.PDF: PdfFormatOption(
                                    pipeline_options=PdfPipelineOptions(do_ocr=False)
                                )
                            }
                        )
                        .convert(source_file.name)
                        .document
                    )
                return StoredDocumentParseResult(
                    text=document.export_to_markdown(), document=document
                )
            except Exception as error:
                raise StoredDocumentParserError("Stored source could not be parsed.") from error
        raise StoredDocumentParserError("Stored source type is not supported.")
