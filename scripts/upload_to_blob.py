"""
Upload Knowledge Base to Azure Blob Storage

Uploads files from data/knowledge_base/ASK HR Knowledge/ to Azure Blob
Storage, preserving the flat file layout under the container.

Supports authentication via:
  - AZURE_STORAGE_ACCOUNT_URL with DefaultAzureCredential (managed identity / az login)
  - AZURE_STORAGE_CONNECTION_STRING (connection string)

Usage:
    uv run python -m scripts.upload_to_blob
    uv run python -m scripts.upload_to_blob --container my-container
    uv run python -m scripts.upload_to_blob --dry-run
"""

import argparse
import logging
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# scripts/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

DEFAULT_DIRS = [
    PROJECT_ROOT / "data" / "knowledge_base" / "ASK HR Knowledge",
]


def get_blob_service_client():
    """Create a BlobServiceClient using connection string or DefaultAzureCredential."""
    from azure.storage.blob import BlobServiceClient

    account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    if account_url:
        from azure.identity import DefaultAzureCredential

        logger.info("Authenticating with DefaultAzureCredential against %s", account_url)
        return BlobServiceClient(account_url, credential=DefaultAzureCredential())

    if conn_str and conn_str != "your_connection_string_here":
        logger.info("Authenticating with connection string")
        return BlobServiceClient.from_connection_string(conn_str)

    logger.error(
        "No storage credentials found. Set AZURE_STORAGE_CONNECTION_STRING "
        "or AZURE_STORAGE_ACCOUNT_URL in your .env file."
    )
    sys.exit(1)


def collect_files(directories: list[Path]) -> list[tuple[Path, str]]:
    """Walk directories and return (local_path, blob_name) pairs.

    For files under ASK HR Knowledge/, the blob name is just the filename
    (flat layout in the container). This matches how the integrated
    vectorization indexer expects documents in blob storage.
    """
    files: list[tuple[Path, str]] = []

    for directory in directories:
        if not directory.exists():
            logger.warning("Directory not found, skipping: %s", directory)
            continue
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                # Flat blob names — just the filename, no subdirectory nesting
                blob_name = file_path.name
                files.append((file_path, blob_name))

    return files


def upload_files(
    files: list[tuple[Path, str]],
    container_name: str,
    *,
    overwrite: bool = True,
    dry_run: bool = False,
) -> None:
    """Upload collected files to Azure Blob Storage."""
    from azure.storage.blob import ContentSettings

    if not files:
        logger.info("No files to upload.")
        return

    if dry_run:
        logger.info("DRY RUN — %d file(s) would be uploaded:", len(files))
        for local_path, blob_name in files:
            size_kb = local_path.stat().st_size / 1024
            logger.info("  -> %s (%.1f KB)", blob_name, size_kb)
        return

    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(container_name)

    # Create container if it doesn't exist
    try:
        container_client.get_container_properties()
    except Exception:
        logger.info("Creating container: %s", container_name)
        container_client.create_container()

    uploaded = 0
    failed = 0
    total = len(files)

    for file_path, blob_name in files:
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        try:
            with open(file_path, "rb") as fh:
                container_client.upload_blob(
                    name=blob_name,
                    data=fh,
                    overwrite=overwrite,
                    content_settings=ContentSettings(content_type=content_type),
                )
            uploaded += 1
            logger.info("Uploaded [%d/%d]: %s", uploaded + failed, total, blob_name)
        except Exception:
            failed += 1
            logger.exception("Failed to upload: %s", blob_name)

    logger.info(
        "Upload complete — %d succeeded, %d failed out of %d total",
        uploaded, failed, total,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload ASK HR Knowledge files to Azure Blob Storage"
    )
    parser.add_argument(
        "--container",
        default=os.getenv("AZURE_STORAGE_CONTAINER", "ask-hr-knowledge"),
        help="Target blob container name (default: AZURE_STORAGE_CONTAINER env var or 'ask-hr-knowledge')",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Skip files that already exist in the container",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be uploaded without actually uploading",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger.info("Collecting files from data/knowledge_base/ASK HR Knowledge/ ...")

    files = collect_files(DEFAULT_DIRS)
    logger.info("Found %d file(s) to upload", len(files))

    upload_files(
        files,
        container_name=args.container,
        overwrite=not args.no_overwrite,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
