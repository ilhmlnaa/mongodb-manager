from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from textual.app import App

from .config import load_settings, save_settings
from .screens import (
    MainMenuScreen,
    BackupScreen,
    ScheduleBackupScreen,
    ManageSchedulesScreen,
    RestoreScreen,
    SyncScreen,
    ManageServersScreen,
)

class MongoManagerApp(App):
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
    ]
    
    CSS = """
    #main-container {
        align-horizontal: center;
        padding: 1;
    }
    .panel {
        width: 60%;
        height: auto;
        border: solid green;
        padding: 1;
        margin-bottom: 2;
        background: $surface;
    }
    .panel-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        width: 100%;
        color: $accent;
    }
    #menu-container {
        align-horizontal: center;
        width: 40%;
        height: auto;
        border: solid $primary;
        padding: 2;
        margin-top: 1;
    }
    #app-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
        color: $text;
        width: 100%;
    }
    #lbl-menu-clock {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
        width: 100%;
    }
    Button {
        width: 100%;
        margin-bottom: 1;
    }
    .divider {
        width: 100%;
        text-align: center;
        margin: 1;
        color: $text-muted;
    }
    .log-label {
        margin-top: 1;
        text-style: bold;
    }
    RichLog {
        height: 15;
        border: solid $secondary;
        background: $panel;
    }
    Input {
        margin-bottom: 1;
    }
    """
    
    SCREENS = {
        "menu": MainMenuScreen,
        "backup": BackupScreen,
        "schedule_backup": ScheduleBackupScreen,
        "manage_schedules": ManageSchedulesScreen,
        "restore": RestoreScreen,
        "sync": SyncScreen,
        "manage_servers": ManageServersScreen
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timezone = self._load_timezone()

    def _detect_timezone(self) -> str:
        tzinfo = datetime.now().astimezone().tzinfo
        key = getattr(tzinfo, "key", None)
        return key if isinstance(key, str) else "UTC"

    def _load_timezone(self) -> str:
        settings = load_settings()
        saved_timezone = settings.get("timezone")
        if isinstance(saved_timezone, str) and saved_timezone:
            try:
                ZoneInfo(saved_timezone)
                return saved_timezone
            except ZoneInfoNotFoundError:
                pass
        return self._detect_timezone()

    def _save_timezone(self) -> None:
        settings = load_settings()
        settings["timezone"] = self._timezone
        save_settings(settings)

    def set_timezone(self, timezone_name: str) -> None:
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            self.notify(f"Timezone '{timezone_name}' not found.", severity="error")
            return
        self._timezone = timezone_name
        self._save_timezone()

    def get_timezone(self) -> str:
        return self._timezone

    def now(self) -> datetime:
        return datetime.now(ZoneInfo(self._timezone))

    def get_time_display(self) -> str:
        now = self.now()
        return f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')} | Timezone: {self._timezone}"

    def on_mount(self) -> None:
        self.push_screen("menu")

if __name__ == "__main__":
    app = MongoManagerApp()
    app.run()
