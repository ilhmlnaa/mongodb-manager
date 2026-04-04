from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Select, Input
from .base import BaseScreen
from ..config import load_servers, save_servers
from ..database import test_mongo_connection

class ManageServersScreen(BaseScreen):
    def compose_content(self) -> ComposeResult:
        servers = load_servers()
        with Vertical(classes="panel"):
            yield Label("Manage Servers", classes="panel-title")
            yield Select(
                [(s, s) for s in servers.keys()], 
                prompt="Select Server to Remove", 
                id="server-list"
            )
            yield Button("Remove Server", id="btn-remove-server", variant="error", disabled=len(servers) == 0)
            yield Label("--- Or Add a New Server ---", classes="divider")
            yield Input(placeholder="Server Name (Alias)", id="input-server-name")
            yield Input(placeholder="MongoDB URI (e.g. mongodb://...)", id="input-server-uri")
            yield Button("Test & Add Server", id="btn-add-server", variant="success")
            yield Label("", id="lbl-server-status")
            yield Button("Back", id="btn-back")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id != "server-list":
            return
        self.query_one("#btn-remove-server", Button).disabled = not bool(event.value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-remove-server":
            select = self.query_one("#server-list", Select)
            if select.value:
                servers = load_servers()
                if select.value in servers:
                    del servers[select.value]
                    save_servers(servers)
                    self.query_one("#lbl-server-status", Label).update(f"[green]Removed server '{select.value}'[/]")
                    select.set_options([(s, s) for s in servers.keys()])
        elif event.button.id == "btn-add-server":
            name = self.query_one("#input-server-name", Input).value.strip()
            uri = self.query_one("#input-server-uri", Input).value.strip()
            lbl = self.query_one("#lbl-server-status", Label)
            
            if not name or not uri:
                lbl.update("[red]Name and URI are required.[/]")
                return

            lbl.update("[yellow]Testing connection...[/]")
            success = test_mongo_connection(uri)
            if success:
                servers = load_servers()
                servers[name] = uri
                save_servers(servers)
                lbl.update(f"[green]Added server '{name}' successfully![/]")
                select = self.query_one("#server-list", Select)
                select.set_options([(s, s) for s in servers.keys()])
                self.query_one("#btn-remove-server", Button).disabled = False
            else:
                lbl.update("[red]Connection test failed. Invalid URI.[/]")
