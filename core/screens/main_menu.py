from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Select
from .base import BaseScreen

class MainMenuScreen(BaseScreen):
    TIMEZONE_OPTIONS = [
        ("UTC", "UTC"),
        ("Asia/Jakarta", "Asia/Jakarta"),
        ("Asia/Singapore", "Asia/Singapore"),
        ("Asia/Tokyo", "Asia/Tokyo"),
        ("Europe/London", "Europe/London"),
        ("America/New_York", "America/New_York"),
    ]

    BINDINGS = [
        ("down", "app.focus_next", "Next"),
        ("up", "app.focus_previous", "Previous"),
    ]

    def on_mount(self) -> None:
        timezone_select = self.query_one("#sel-timezone", Select)
        timezone_select.set_options(self.TIMEZONE_OPTIONS)
        current_timezone = self.app.get_timezone()
        if current_timezone in [value for _, value in self.TIMEZONE_OPTIONS]:
            timezone_select.value = current_timezone
        self._update_clock()
        self.set_interval(1, self._update_clock)

        try:
            self.query_one("#btn-backup", Button).focus()
        except:
            pass

    def _update_clock(self) -> None:
        self.query_one("#lbl-menu-clock", Label).update(self.app.get_time_display())

    def compose_content(self) -> ComposeResult:
        with Vertical(id="menu-container"):
            yield Label("Mongo Manager Dashboard", id="app-title")
            yield Button("Backup Database", id="btn-backup", variant="primary")
            yield Button("Schedule Backup", id="btn-schedule", variant="primary")
            yield Button("Manage Schedules", id="btn-manage-schedules")
            yield Button("Restore Database", id="btn-restore", variant="primary")
            yield Button("Synchronize Databases", id="btn-sync", variant="primary")
            yield Button("Manage Servers", id="btn-servers")
            yield Select([], prompt="Select Timezone", id="sel-timezone")
            yield Label("Time: -", id="lbl-menu-clock")
            yield Button("Exit", id="btn-exit", variant="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "sel-timezone" and event.value:
            self.app.set_timezone(str(event.value))
            self._update_clock()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-backup":
            self.app.push_screen("backup")
        elif event.button.id == "btn-schedule":
            self.app.push_screen("schedule_backup")
        elif event.button.id == "btn-manage-schedules":
            self.app.push_screen("manage_schedules")
        elif event.button.id == "btn-restore":
            self.app.push_screen("restore")
        elif event.button.id == "btn-sync":
            self.app.push_screen("sync")
        elif event.button.id == "btn-servers":
            self.app.push_screen("manage_servers")
        elif event.button.id == "btn-exit":
            self.app.exit()
