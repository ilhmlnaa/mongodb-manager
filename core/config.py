import os
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define Paths
SCRIPT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = SCRIPT_DIR / "mongodb-backup"

_raw_config_dir = os.getenv("MONGO_MANAGER_CONFIG_DIR", "config-data").strip()
_config_dir_path = Path(_raw_config_dir)
if _config_dir_path.is_absolute():
    CONFIG_DIR = _config_dir_path
else:
    CONFIG_DIR = (SCRIPT_DIR / _config_dir_path).resolve()

SERVERS_FILE = CONFIG_DIR / "servers.json"
SCHEDULES_FILE = CONFIG_DIR / "backup_schedules.json"
SETTINGS_FILE = CONFIG_DIR / "app_settings.json"

LEGACY_SERVERS_FILE = SCRIPT_DIR / "servers.json"
LEGACY_SCHEDULES_FILE = SCRIPT_DIR / "backup_schedules.json"
LEGACY_SETTINGS_FILE = SCRIPT_DIR / "app_settings.json"

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

def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def _migrate_legacy_json(legacy_file: Path, target_file: Path) -> None:
    if target_file.exists() or not legacy_file.exists():
        return
    target_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        legacy_file.replace(target_file)
    except OSError:
        try:
            shutil.copy2(legacy_file, target_file)
            legacy_file.unlink(missing_ok=True)
        except PermissionError:
            return

def _initialize_config_layout() -> None:
    _ensure_config_dir()
    _migrate_legacy_json(LEGACY_SERVERS_FILE, SERVERS_FILE)
    _migrate_legacy_json(LEGACY_SCHEDULES_FILE, SCHEDULES_FILE)
    _migrate_legacy_json(LEGACY_SETTINGS_FILE, SETTINGS_FILE)

_initialize_config_layout()

def load_servers() -> dict:
    if SERVERS_FILE.exists():
        with open(SERVERS_FILE, "r") as f:
            return json.load(f)

    if LEGACY_SERVERS_FILE.exists():
        with open(LEGACY_SERVERS_FILE, "r") as f:
            return json.load(f)

    return {}

def save_servers(servers: dict):
    try:
        with open(SERVERS_FILE, "w") as f:
            json.dump(servers, f, indent=2)
    except PermissionError:
        with open(LEGACY_SERVERS_FILE, "w") as f:
            json.dump(servers, f, indent=2)

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}

    if LEGACY_SETTINGS_FILE.exists():
        try:
            with open(LEGACY_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    return {}

def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except PermissionError:
        with open(LEGACY_SETTINGS_FILE, "w", encoding="utf-8") as f:
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
