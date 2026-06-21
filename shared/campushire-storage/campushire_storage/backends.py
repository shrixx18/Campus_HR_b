from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, file: UploadFile, folder: str) -> str:
        """Save file and return public/signed URL."""

    @abstractmethod
    async def get_url(self, key: str) -> str:
        """Return accessible URL for stored object."""


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str, public_base_url: str = "/files") -> None:
        self.base_path = Path(base_path)
        self.public_base_url = public_base_url.rstrip("/")
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile, folder: str) -> str:
        folder_path = self.base_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or "upload").suffix
        key = f"{folder}/{uuid4()}{suffix}"
        dest = self.base_path / key
        content = await file.read()
        dest.write_bytes(content)
        return f"{self.public_base_url}/{key}"

    async def get_url(self, key: str) -> str:
        return f"{self.public_base_url}/{key}"


class AzureBlobStorageBackend(StorageBackend):
    def __init__(self, connection_string: str, container: str) -> None:
        from azure.storage.blob import BlobServiceClient

        self.client = BlobServiceClient.from_connection_string(connection_string)
        self.container = container
        self.client.get_container_client(container).create_container(exist_ok=True)

    async def save(self, file: UploadFile, folder: str) -> str:
        suffix = Path(file.filename or "upload").suffix
        key = f"{folder}/{uuid4()}{suffix}"
        blob = self.client.get_blob_client(self.container, key)
        content = await file.read()
        blob.upload_blob(content, overwrite=True)
        return blob.url

    async def get_url(self, key: str) -> str:
        blob = self.client.get_blob_client(self.container, key)
        return blob.url


def create_storage_backend(backend: str, **kwargs) -> StorageBackend:
    if backend == "azure":
        return AzureBlobStorageBackend(
            connection_string=kwargs["connection_string"],
            container=kwargs["container"],
        )
    return LocalStorageBackend(
        base_path=kwargs.get("local_path", "/data/uploads"),
        public_base_url=kwargs.get("public_base_url", "/files"),
    )


ALLOWED_EXTENSIONS = {".pdf", ".csv", ".doc", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise ValueError("Filename is required")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {suffix} not allowed")
