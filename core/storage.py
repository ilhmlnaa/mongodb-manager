import shutil
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from .config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME, is_s3_configured

def zip_directory(dir_path: Path) -> Path:
    """Zips a given directory and returns the path to the zip file."""
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"❌ Directory not found for zipping: {dir_path}")
        return None
    
    zip_path = str(dir_path)  # make_archive appends .zip automatically
    print(f"📦 Zipping directory {dir_path}...")
    shutil.make_archive(zip_path, 'zip', dir_path)
    final_zip_path = Path(f"{zip_path}.zip")
    print(f"✅ Created ZIP archive at: {final_zip_path}")
    return final_zip_path

def upload_to_s3(file_path: Path, object_name: str = None) -> bool:
    """Uploads a file to an S3-compatible service (e.g. Cloudflare R2)."""
    if not is_s3_configured():
        print("❌ S3 is not fully configured in your .env file.")
        return False

    if not file_path.exists():
        print(f"❌ File to upload not found: {file_path}")
        return False

    if object_name is None:
        object_name = file_path.name

    print(f"☁️  Uploading '{file_path.name}' to S3 Bucket '{S3_BUCKET_NAME}'...")
    
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY
        )
        s3_client.upload_file(str(file_path), S3_BUCKET_NAME, object_name)
        print("✅ S3 Upload successful!")
        return True
    except ClientError as e:
        print(f"❌ Failed to upload to S3: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred during S3 upload: {e}")
        return False
