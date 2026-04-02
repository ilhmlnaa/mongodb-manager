import shutil
from pymongo import MongoClient, errors
from pathlib import Path
from .config import SCRIPT_DIR
from .utils import run_command


def _resolve_tool(tool_name: str) -> str:
    resolved = shutil.which(tool_name)
    if resolved:
        return resolved

    bundled = SCRIPT_DIR / "mongo-tools" / "linux" / "bin" / tool_name
    if bundled.exists():
        return str(bundled)

    return tool_name

def test_mongo_connection(uri: str) -> bool:
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.list_database_names()
        return True
    except errors.PyMongoError as e:
        print(f"❌ Connection failed: {e}")
        return False

def get_accessible_databases(uri: str) -> list[str]:
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        dbs = client.list_database_names()
        return [db for db in dbs if db not in ("admin", "config", "local")]
    except Exception as e:
        print(f"❌ Failed to fetch databases: {e}")
        return []

def dump_database(uri: str, db_name: str, out_dir: Path, logger=None) -> bool:
    """Dump a specific database to a folder."""
    mongodump = _resolve_tool("mongodump")
    if db_name and db_name != "all":
        cmd = f'"{mongodump}" --uri="{uri}" --db="{db_name}" --out="{out_dir}"'
    else:
        cmd = f'"{mongodump}" --uri="{uri}" --out="{out_dir}"'
    return run_command(cmd, logger=logger)

def restore_database(uri: str, target_db_name: str, dump_dir: Path, source_db_name: str = None, logger=None) -> bool:
    """Restore a mongodump from a specific directory."""
    mongorestore = _resolve_tool("mongorestore")
    if source_db_name:
        cmd = (
            f'"{mongorestore}" --drop --uri="{uri}" '
            f'--nsFrom="{source_db_name}.*" --nsTo="{target_db_name}.*" "{dump_dir}"'
        )
    else:
        # Full restore from directory
        cmd = f'"{mongorestore}" --drop --uri="{uri}" "{dump_dir}"'
    return run_command(cmd, logger=logger)
