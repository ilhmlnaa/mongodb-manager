from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Select

from .base import ActionScreen
from ..config import load_servers, BACKUP_DIR
from ..database import restore_database

class RestoreScreen(ActionScreen):
    def compose_content(self) -> ComposeResult:
        servers = load_servers()
        with Vertical(classes="panel"):
            yield Label("Restore Database", classes="panel-title")
            yield from self.compose_log_panel()
            yield Select([(s, s) for s in servers.keys()], prompt="Select Target Server", id="sel-server")
            
            backups = []
            if BACKUP_DIR.exists():
                for f in BACKUP_DIR.iterdir():
                    if f.is_dir():
                        backups.append((f.name, str(f)))
            yield Select(backups, prompt="Select Backup Folder", id="sel-backup-dir")
            yield Button("Start Restore", id="btn-start-restore", variant="warning", disabled=True)

    def _update_submit_state(self) -> None:
        server = self.query_one("#sel-server", Select).value
        folder = self.query_one("#sel-backup-dir", Select).value
        self.query_one("#btn-start-restore", Button).disabled = not (server and folder)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id in ("sel-server", "sel-backup-dir"):
            self._update_submit_state()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-start-restore":
            server = self.query_one("#sel-server", Select).value
            folder = self.query_one("#sel-backup-dir", Select).value

            if not server or not folder:
                self.write_log("[red]Please select both server and folder.[/]")
                return

            self.run_restore(server, folder)

    @work(thread=True)
    def run_restore(self, server: str, folder: str) -> None:
        self.app.call_from_thread(self.set_running, True)
        try:
            servers = load_servers()
            uri = servers[server]
            
            def log_cmd(msg: str):
                self.app.call_from_thread(self.write_log, msg)

            log_cmd(f"[cyan]Restoring from '{folder}' to '{server}'...[/]")
            success = restore_database(uri, "", str(folder), logger=log_cmd)
            if success:
                log_cmd("[green]Database restored successfully.[/]")
            else:
                log_cmd("[red]Restore process failed.[/]")
        finally:
            self.app.call_from_thread(self.set_running, False)
