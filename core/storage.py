import shutil
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pathlib import Path
from typing import Callable
from .config import (
    S3_ENDPOINT,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    S3_BUCKET_NAME,
    is_s3_configured,
    get_s3_missing_keys,
)

def zip_directory(dir_path: Path) -> Path:
    """Zips a given directory and returns the path to the zip file."""
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"❌ Directory not found for zipping: {dir_path}")
        return None
    
    zip_path = str(dir_path) 
    print(f"📦 Zipping directory {dir_path}...")
    shutil.make_archive(zip_path, 'zip', dir_path)
    final_zip_path = Path(f"{zip_path}.zip")
    print(f"✅ Created ZIP archive at: {final_zip_path}")
    return final_zip_path

def _normalize_endpoint(endpoint: str | None) -> str | None:
    if endpoint is None:
        return None
    normalized = endpoint.strip()
    if normalized and not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized


def upload_to_s3(file_path: Path, object_name: str = None, logger: Callable[[str], None] | None = None) -> bool:
    """Uploads a file to an S3-compatible service (e.g. Cloudflare R2)."""
    def log(message: str) -> None:
        print(message)
        if logger is not None:
            logger(message)

    if not is_s3_configured():
        missing = ", ".join(get_s3_missing_keys())
        log(f"❌ S3 is not fully configured in your .env file. Missing: {missing}")
        return False

    if not file_path.exists():
        log(f"❌ File to upload not found: {file_path}")
        return False

    if object_name is None:
        object_name = file_path.name

    endpoint = _normalize_endpoint(S3_ENDPOINT)
    if endpoint is None:
        log("❌ S3 endpoint is empty.")
        return False

    log(f"☁️  Uploading '{file_path.name}' to S3 Bucket '{S3_BUCKET_NAME}' via '{endpoint}'...")
    
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name='auto',
            config=Config(signature_version='s3v4', retries={'max_attempts': 3, 'mode': 'standard'})
        )
        s3_client.upload_file(str(file_path), S3_BUCKET_NAME, object_name)
        log("✅ S3 Upload successful!")
        return True
    except ClientError as e:
        log(f"❌ Failed to upload to S3 (ClientError): {e}")
        return False
    except BotoCoreError as e:
        log(f"❌ Failed to upload to S3 (BotoCoreError): {e}")
        return False
    except Exception as e:
        log(f"❌ An unexpected error occurred during S3 upload: {e}")
        return False
