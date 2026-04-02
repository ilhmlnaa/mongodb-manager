import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define Paths
SCRIPT_DIR = Path(__file__).resolve().parent.parent
SERVERS_FILE = SCRIPT_DIR / "servers.json"
BACKUP_DIR = SCRIPT_DIR / "mongodb-backup"
SCHEDULES_FILE = SCRIPT_DIR / "backup_schedules.json"
SETTINGS_FILE = SCRIPT_DIR / "app_settings.json"

# S3 configurations from .env
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

WEB_HOST = os.getenv("MONGO_MANAGER_WEB_HOST", "127.0.0.1")

try:
    WEB_PORT = int(os.getenv("MONGO_MANAGER_WEB_PORT", "8000"))
except ValueError:
    WEB_PORT = 8000

def load_servers() -> dict:
    if not SERVERS_FILE.exists():
        return {}
    with open(SERVERS_FILE, "r") as f:
        return json.load(f)

def save_servers(servers: dict):
    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)

def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def _is_set(value: str | None) -> bool:
    return value is not None and value.strip() != ""

def get_s3_missing_keys() -> list[str]:
    required = {
        "S3_ENDPOINT": S3_ENDPOINT,
        "S3_ACCESS_KEY": S3_ACCESS_KEY,
        "S3_SECRET_KEY": S3_SECRET_KEY,
        "S3_BUCKET_NAME": S3_BUCKET_NAME,
    }
    return [key for key, value in required.items() if not _is_set(value)]

def is_s3_configured() -> bool:
    return len(get_s3_missing_keys()) == 0
