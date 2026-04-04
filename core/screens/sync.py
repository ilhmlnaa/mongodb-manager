import shutil

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Select, Input

from .base import ActionScreen
from ..config import load_servers, SCRIPT_DIR
from ..database import get_accessible_databases, dump_database, restore_database

class SyncScreen(ActionScreen):
    def compose_content(self) -> ComposeResult:
        servers = load_servers()
        with Vertical(classes="panel"):
            yield Label("Synchronize Databases", classes="panel-title")
            yield from self.compose_log_panel()
            yield Select([(s, s) for s in servers.keys()], prompt="Source Server", id="sel-source")
            yield Select([(s, s) for s in servers.keys()], prompt="Target Server", id="sel-target")
            yield Select([], prompt="Database", id="sel-db", disabled=True)
            yield Input(placeholder="Custom Target DB Name (Optional)", id="in-custom-db")
            yield Button("Start Synchronization", id="btn-sync", variant="primary", disabled=True)

    def _update_submit_state(self) -> None:
        src = self.query_one("#sel-source", Select).value
        tgt = self.query_one("#sel-target", Select).value
        db = self.query_one("#sel-db", Select).value
        self.query_one("#btn-sync", Button).disabled = not (src and tgt and db)

    @work(thread=True)
    def fetch_databases(self, uri: str) -> None:
        dbs = get_accessible_databases(uri)
        options = [(db, db) for db in dbs]
        def update_ui():
            sel_db = self.query_one("#sel-db", Select)
            sel_db.set_options(options)
            sel_db.disabled = False
            self._update_submit_state()
            try:
                sel_db.focus()
            except:
                pass
        self.app.call_from_thread(update_ui)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "sel-source" and event.value:
            servers = load_servers()
            uri = servers.get(event.value)
            if uri:
                self.query_one("#sel-db", Select).disabled = True
                self.fetch_databases(uri)
                self._update_submit_state()
        elif event.control.id in ("sel-target", "sel-db"):
            self._update_submit_state()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-sync":
            src = self.query_one("#sel-source", Select).value
            tgt = self.query_one("#sel-target", Select).value
            db = self.query_one("#sel-db", Select).value
            custom_db = self.query_one("#in-custom-db", Input).value.strip() or db

            if not src or not tgt or not db:
                self.write_log("[red]Please complete all fields.[/]")
                return
            if src == tgt:
                self.write_log("[red]Source and Target must be different![/]")
                return

            self.run_sync(src, tgt, db, custom_db)

    @work(thread=True)
    def run_sync(self, src: str, tgt: str, db: str, custom_db: str) -> None:
        self.app.call_from_thread(self.set_running, True)
        try:
            servers = load_servers()
            def log_cmd(msg: str):
                self.app.call_from_thread(self.write_log, msg)

            temp_dir = SCRIPT_DIR / f"tmp-dump-{db}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            log_cmd(f"[cyan]Dumping '{db}' from '{src}'...[/]")
            if not dump_database(servers[src], db, temp_dir, logger=log_cmd):
                log_cmd("[red]Sync aborted due to dump failure.[/]")
                return

            log_cmd(f"[cyan]Restoring to '{tgt}' as '{custom_db}'...[/]")
            if restore_database(servers[tgt], custom_db, str(temp_dir), source_db_name=db, logger=log_cmd):
                log_cmd("[green]Synchronize completed successfully.[/]")
            else:
                log_cmd("[red]Synchronize failed at restore stage.[/]")
            
            shutil.rmtree(temp_dir)
        finally:
            self.app.call_from_thread(self.set_running, False)
