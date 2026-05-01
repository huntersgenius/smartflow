import asyncio
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import PurePath
from typing import BinaryIO
from urllib.parse import quote
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings


logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when the S3-compatible storage backend cannot complete an operation."""


@dataclass(frozen=True)
class UploadedObject:
    s3_key: str
    url: str
    presigned_url: str


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.settings.S3_ENDPOINT_URL,
                aws_access_key_id=self.settings.S3_ACCESS_KEY,
                aws_secret_access_key=self.settings.S3_SECRET_KEY,
                region_name=self.settings.S3_REGION,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    async def upload_fileobj(
        self,
        fileobj: BinaryIO,
        s3_key: str,
        content_type: str,
        presigned_expires_in: int = 3600,
    ) -> UploadedObject:
        extra_args = {"ContentType": content_type}
        try:
            await asyncio.to_thread(
                self.client.upload_fileobj,
                fileobj,
                self.settings.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs=extra_args,
            )
            presigned_url = await self.get_presigned_url(
                s3_key,
                expires_in=presigned_expires_in,
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            logger.exception("storage_upload_failed", extra={"s3_key": s3_key})
            raise StorageError("Storage upload failed") from exc

        return UploadedObject(
            s3_key=s3_key,
            url=self.get_url(s3_key),
            presigned_url=presigned_url,
        )

    async def delete(self, s3_key: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.settings.S3_BUCKET_NAME,
                Key=s3_key,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("storage_delete_failed", extra={"s3_key": s3_key})
            raise StorageError("Storage delete failed") from exc

    async def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        try:
            return await asyncio.to_thread(
                self.client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.settings.S3_BUCKET_NAME, "Key": s3_key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("storage_presign_failed", extra={"s3_key": s3_key})
            raise StorageError("Storage presign failed") from exc

    def get_url(self, s3_key: str) -> str:
        base_url = self.settings.MEDIA_BASE_URL.rstrip("/")
        return f"{base_url}/{_quote_key(s3_key)}"


def build_menu_image_key(menu_item_id: str, filename: str | None, content_type: str) -> str:
    suffix = PurePath(filename or "").suffix.lower()
    if not suffix:
        suffix = mimetypes.guess_extension(content_type) or ".bin"
    return f"menu/items/{menu_item_id}/{uuid4().hex}{suffix}"


def _quote_key(s3_key: str) -> str:
    return "/".join(quote(part, safe="") for part in s3_key.split("/"))
