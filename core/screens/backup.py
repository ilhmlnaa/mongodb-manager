from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Select, Checkbox

from .base import ActionScreen
from ..config import load_servers, BACKUP_DIR, is_s3_configured
from ..database import get_accessible_databases, dump_database
from ..storage import zip_directory, upload_to_s3

class BackupScreen(ActionScreen):
    def compose_content(self) -> ComposeResult:
        servers = load_servers()
        with Vertical(classes="panel"):
            yield Label("Backup Database", classes="panel-title")
            yield from self.compose_log_panel()
            yield Select([(s, s) for s in servers.keys()], prompt="Select Target Server", id="sel-server")
            yield Select([], prompt="Select Database (Select Server first)", id="sel-db", disabled=True)
            yield Checkbox("Compress to ZIP archive", value=True, id="chk-zip")
            
            s3_configured = is_s3_configured()
            yield Checkbox(
                "Upload ZIP to S3 (Cloudflare R2)", 
                value=s3_configured, 
                id="chk-s3", 
                disabled=not s3_configured
            )
            yield Button("Start Backup", id="btn-start-backup", variant="success", disabled=True)

    def _update_submit_state(self) -> None:
        server = self.query_one("#sel-server", Select).value
        db = self.query_one("#sel-db", Select).value
        self.query_one("#btn-start-backup", Button).disabled = not (server and db)

    @work(thread=True)
    def fetch_databases(self, server_name: str, uri: str) -> None:
        self.app.call_from_thread(self.write_log, f"[yellow]Fetching databases for '{server_name}'...[/]")
        dbs = get_accessible_databases(uri)
        options = [("Backup All", "all")] + [(db, db) for db in dbs]
        
        def update_ui():
            sel_db = self.query_one("#sel-db", Select)
            sel_db.set_options(options)
            sel_db.disabled = False
            self.write_log("[green]Databases fetched.[/]")
            self._update_submit_state()
            try:
                sel_db.focus()
            except:
                pass
            
        self.app.call_from_thread(update_ui)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "sel-server" and event.value:
            servers = load_servers()
            uri = servers.get(event.value)
            if uri:
                self.query_one("#sel-db", Select).disabled = True
                self.fetch_databases(event.value, uri)
                self._update_submit_state()
        elif event.control.id == "sel-db":
            self._update_submit_state()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id != "chk-zip":
            return
        s3_checkbox = self.query_one("#chk-s3", Checkbox)
        if not event.value:
            s3_checkbox.value = False
            s3_checkbox.disabled = True
            return
        if is_s3_configured():
            s3_checkbox.disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-start-backup":
            server = self.query_one("#sel-server", Select).value
            db = self.query_one("#sel-db", Select).value
            do_zip = self.query_one("#chk-zip", Checkbox).value
            do_s3 = self.query_one("#chk-s3", Checkbox).value

            if not server or not db:
                self.write_log("[red]Error: Please select both a server and a database.[/]")
                return

            if do_s3 and not do_zip:
                self.write_log("[red]Error: Upload to S3 requires 'Compress to ZIP archive'.[/]")
                return

            self.run_backup(server, db, do_zip, do_s3)

    @work(thread=True)
    def run_backup(self, server: str, db: str, do_zip: bool, do_s3: bool) -> None:
        self.app.call_from_thread(self.set_running, True)
        
        try:
            servers = load_servers()
            uri = servers[server]
            timestamp = self.app.now().strftime("%Y-%m-%d-%H-%M")
            folder = BACKUP_DIR / server / timestamp
            folder.mkdir(parents=True, exist_ok=True)
            
            def log_callback(msg: str):
                self.app.call_from_thread(self.write_log, msg)

            log_callback(f"[cyan]Dumping database '{db}' from '{server}'...[/]")
            success = dump_database(uri, db, folder, logger=log_callback)
            
            if not success:
                log_callback("[red]Backup process failed.[/]")
                return
            log_callback("[green]Database dump successful.[/]")

            if do_zip:
                log_callback("[cyan]Zipping backup folder...[/]")
                zip_path = zip_directory(folder)
                if zip_path:
                    log_callback(f"[green]ZIP created at: {zip_path}[/]")
                    if do_s3:
                        log_callback("[cyan]Uploading to S3...[/]")
                        s3_obj = f"{server}/{zip_path.name}"
                        up_success = upload_to_s3(zip_path, s3_obj, logger=log_callback)
                        if up_success:
                            log_callback("[green]S3 upload successful.[/]")
                        else:
                            log_callback("[red]S3 upload failed.[/]")
        finally:
            self.app.call_from_thread(self.set_running, False)
