import argparse
import sys
from datetime import datetime

from core.config import load_servers, BACKUP_DIR, SCRIPT_DIR, WEB_HOST, WEB_PORT
from core.database import dump_database, restore_database
from core.storage import zip_directory, upload_to_s3
from core.tui import MongoManagerApp

def run_backup(args):
    servers = load_servers()
    if args.server not in servers:
        print(f"❌ Server '{args.server}' not found in config-data/servers.json.")
        sys.exit(1)

    uri = servers[args.server]
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")

    if args.out:
        folder = SCRIPT_DIR / args.out
    else:
        folder = BACKUP_DIR / args.server / timestamp

    folder.mkdir(parents=True, exist_ok=True)
    db_arg = args.db

    print(f"📤 Starting automated backup for server '{args.server}', database: '{db_arg}'")
    success = dump_database(uri, db_arg, folder)
    
    if not success:
        print("❌ Backup process failed.")
        sys.exit(1)

    print("✅ Database dumped successfully.")

    if args.zip:
        zip_path = zip_directory(folder)
        if zip_path and args.s3:
            s3_obj_name = f"{args.server}/{zip_path.name}"
            upload_to_s3(zip_path, s3_obj_name)

def run_web(args):
    from textual_serve.server import Server
    import os
    executable = sys.executable.replace('\\', '/')
    script_path = os.path.abspath(__file__).replace('\\', '/')
    command = f'"{executable}" "{script_path}"'
    
    print(f"🌐 Starting Textual Web Server at http://{args.host}:{args.port}")
    server = Server(
        command,
        host=args.host,
        port=args.port,
        title="Mongo Manager"
    )
    server.serve()

def main():
    parser = argparse.ArgumentParser(
        description="Mongo Manager - Interactive & CLI tool for MongoDB Backup/Restore."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    backup_parser = subparsers.add_parser("backup", help="Run automated backup for a server")
    backup_parser.add_argument("server", type=str, help="Server alias defined in config-data/servers.json")
    backup_parser.add_argument("--db", type=str, default="all", help="Database name to backup (default: 'all')")
    backup_parser.add_argument("--out", type=str, help="Output directory path")
    backup_parser.add_argument("--zip", action="store_true", help="Compress the backup folder into a ZIP file")
    backup_parser.add_argument("--s3", action="store_true", help="Upload the zipped backup to S3 (requires --zip)")

    web_parser = subparsers.add_parser("web", help="Serve the Mongo Manager TUI as a web application")
    web_parser.add_argument("--host", type=str, default=WEB_HOST, help=f"Host IP to bind the web server (default: {WEB_HOST}, env: MONGO_MANAGER_WEB_HOST)")
    web_parser.add_argument("--port", type=int, default=WEB_PORT, help=f"Port to bind the web server (default: {WEB_PORT}, env: MONGO_MANAGER_WEB_PORT)")

    args = parser.parse_args()

    if args.command is None:
        try:
            app = MongoManagerApp()
            app.run()
        except KeyboardInterrupt:
            print("\n👋 Exited by user.")
            sys.exit(0)
    elif args.command == "backup":
        run_backup(args)
    elif args.command == "web":
        run_web(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
