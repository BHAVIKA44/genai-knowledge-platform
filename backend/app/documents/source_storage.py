from pathlib import Path
from uuid import uuid4


class SourceStorageError(Exception):
    pass


class SourceNotFoundError(SourceStorageError):
    pass


class LocalSourceStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def save(self, source: bytes, extension: str) -> str:
        suffix = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        key = f"{uuid4()}{suffix}"
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            (self.root / key).write_bytes(source)
        except OSError as error:
            raise SourceStorageError("Source document could not be stored.") from error
        return key

    def load(self, key: str) -> bytes:
        path = self._path_for(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as error:
            raise SourceNotFoundError("Stored source document was not found.") from error
        except OSError as error:
            raise SourceStorageError("Stored source document could not be read.") from error

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            raise SourceStorageError("Stored source document could not be deleted.") from error

    def _path_for(self, key: str) -> Path:
        path = Path(key)
        if path.is_absolute() or path.name != key:
            raise SourceStorageError("Stored source reference is invalid.")
        return self.root / path
