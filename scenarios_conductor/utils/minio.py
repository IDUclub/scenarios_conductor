"""Utility for downloading files from Minio S3 storage."""


import tempfile

import structlog
from minio import Minio
from minio.error import S3Error

from scenarios_conductor.config import FileServerConfig


def download_from_minio(config: FileServerConfig, file_path: str, logger: structlog.stdlib.BoundLogger) -> str:
    """
    Download file from Minio to a temporary file.

    Args:
        config: Minio configuration.
        file_path: Path where to get the file in S3.
        logger: Logger instance.

    Returns:
        Path to downloaded temporary file.
    """
    try:
        # Create Minio client
        minio_client = Minio(
            endpoint=config.url.replace("http://", "").replace("https://", ""),
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.url.startswith("https"),
        )

        # Create temporary file
        suffix = "." + file_path.rsplit(".", maxsplit=1)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name

        # Download file
        minio_client.fget_object(bucket_name=config.bucket, object_name=file_path, file_path=str(temp_path))

        logger.info("File downloaded from Minio", bucket=config.bucket, path=file_path, temp_path=str(temp_path))

        return temp_path

    except S3Error as e:
        logger.error("Failed to download cadastre file from Minio", error=str(e), bucket=config.bucket, path=file_path)
        raise
    except Exception as e:
        logger.error("Unexpected error downloading from Minio", error=str(e))
        raise
