from app.documents.chunk_models import DocumentChunk
from app.documents.chunk_repository import DocumentChunkRepository


def chunk(document_id: str, position: int, text: str) -> DocumentChunk:
    return DocumentChunk(
        document_id=document_id,
        position=position,
        text=text,
        content_length=len(text),
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding=[0.0] * 384,
    )


def test_insert_get_replace_and_delete_chunks(session) -> None:
    repository = DocumentChunkRepository(session)
    repository.insert_chunks("one", [chunk("one", 1, "second"), chunk("one", 0, "first")])
    session.commit()
    assert [item.text for item in repository.get_chunks("one")] == ["first", "second"]
    repository.replace_chunks("one", [chunk("one", 0, "replacement")])
    session.commit()
    assert [item.text for item in repository.get_chunks("one")] == ["replacement"]
    repository.delete_chunks("one")
    session.commit()
    assert repository.get_chunks("one") == []


def test_chunks_are_scoped_to_their_document(session) -> None:
    repository = DocumentChunkRepository(session)
    repository.insert_chunks("one", [chunk("one", 0, "one")])
    repository.insert_chunks("two", [chunk("two", 0, "two")])
    session.commit()
    repository.delete_chunks("one")
    session.commit()
    assert [item.text for item in repository.get_chunks("two")] == ["two"]
