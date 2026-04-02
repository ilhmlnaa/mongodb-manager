import asyncio
import json
from datetime import datetime
from pathlib import Path
import shutil

from textual import work
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Label, Select, Checkbox, Input, RichLog, ListView, ListItem
from textual.containers import Vertical, Horizontal, ScrollableContainer

from .config import load_servers, save_servers, BACKUP_DIR, SCRIPT_DIR, SCHEDULES_FILE, is_s3_configured
from .database import get_accessible_databases, dump_database, restore_database, test_mongo_connection
from .storage import zip_directory, upload_to_s3

class BaseScreen(Screen):
    """A base screen to share common layout: Header and Footer."""
    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="main-container"):
            yield from self.compose_content()
        yield Footer()

    def compose_content(self) -> ComposeResult:
        yield Label("Override this in subclasses")


class MainMenuScreen(BaseScreen):
    BINDINGS = [
        ("down", "app.focus_next", "Next"),
        ("up", "app.focus_previous", "Previous"),
    ]

    def on_mount(self) -> None:
        try:
            self.query_one("#btn-backup", Button).focus()
        except:
            pass

    def compose_content(self) -> ComposeResult:
        with Vertical(id="menu-container"):
            yield Label("Mongo Manager Dashboard", id="app-title")
            yield Button("Backup Database", id="btn-backup", variant="primary")
            yield Button("Schedule Backup", id="btn-schedule", variant="primary")
            yield Button("Manage Schedules", id="btn-manage-schedules")
            yield Button("Restore Database", id="btn-restore", variant="primary")
            yield Button("Synchronize Databases", id="btn-sync", variant="primary")
            yield Button("Manage Servers", id="btn-servers")
            yield Button("Exit", id="btn-exit", variant="error")

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
            yield Button("Remove Server", id="btn-remove-server", variant="error")
            yield Label("--- Or Add a New Server ---", classes="divider")
            yield Input(placeholder="Server Name (Alias)", id="input-server-name")
            yield Input(placeholder="MongoDB URI (e.g. mongodb://...)", id="input-server-uri")
            yield Button("Test & Add Server", id="btn-add-server", variant="success")
            yield Label("", id="lbl-server-status")
            yield Button("⏪ Back", id="btn-back")

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
            else:
                lbl.update("[red]Connection test failed. Invalid URI.[/]")


class ActionScreen(BaseScreen):
    """Base Screen for Backup, Restore, Sync with a Log Panel."""
    def compose_log_panel(self) -> ComposeResult:
        yield Label("Process Log:", classes="log-label")
        log_panel = RichLog(highlight=True, markup=True, id="rich-log")
        log_panel.can_focus = False
        yield log_panel
        yield Button("⏪ Back to Menu", id="btn-back", disabled=False)

    def write_log(self, text: str) -> None:
        log_widget = self.query_one("#rich-log", RichLog)
        log_widget.write(text)

    def set_running(self, running: bool) -> None:
        back_btn = self.query_one("#btn-back", Button)
        back_btn.disabled = running
        for btn in self.query(Button):
            if btn.id != "btn-back":
                btn.disabled = running


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
            yield Button("🚀 Start Backup", id="btn-start-backup", variant="success")

    @work(thread=True)
    def fetch_databases(self, server_name: str, uri: str) -> None:
        self.app.call_from_thread(self.write_log, f"[yellow]Fetching databases for '{server_name}'...[/]")
        dbs = get_accessible_databases(uri)
        options = [("📦 Backup All", "all")] + [(db, db) for db in dbs]
        
        def update_ui():
            sel_db = self.query_one("#sel-db", Select)
            sel_db.set_options(options)
            sel_db.disabled = False
            self.write_log("[green]Databases fetched.[/]")
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
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
            folder = BACKUP_DIR / server / timestamp
            folder.mkdir(parents=True, exist_ok=True)
            
            def log_callback(msg: str):
                self.app.call_from_thread(self.write_log, msg)

            log_callback(f"[cyan]📤 Dumping database '{db}' from '{server}'...[/]")
            success = dump_database(uri, db, folder, logger=log_callback)
            
            if not success:
                log_callback("[red]❌ Backup process failed![/]")
                return
            log_callback("[green]✅ Database dump successful.[/]")

            if do_zip:
                log_callback("[cyan]📦 Zipping backup folder...[/]")
                zip_path = zip_directory(folder)
                if zip_path:
                    log_callback(f"[green]✅ ZIP Created at: {zip_path}[/]")
                    if do_s3:
                        log_callback("[cyan]☁️ Uploading to S3...[/]")
                        s3_obj = f"{server}/{zip_path.name}"
                        up_success = upload_to_s3(zip_path, s3_obj)
                        if up_success:
                            log_callback("[green]✅ S3 Upload successful![/]")
                        else:
                            log_callback("[red]❌ S3 Upload failed![/]")
        finally:
            self.app.call_from_thread(self.set_running, False)


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
            yield Button("🔥 Start Restore", id="btn-start-restore", variant="warning")

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

            log_cmd(f"[cyan]📥 Restoring from '{folder}' to '{server}'...[/]")
            success = restore_database(uri, "", str(folder), logger=log_cmd)
            if success:
                log_cmd("[green]✅ Database restored successfully.[/]")
            else:
                log_cmd("[red]❌ Restore process failed![/]")
        finally:
            self.app.call_from_thread(self.set_running, False)


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
            yield Button("🔄 Start Synchronization", id="btn-sync", variant="primary")

    @work(thread=True)
    def fetch_databases(self, uri: str) -> None:
        dbs = get_accessible_databases(uri)
        options = [(db, db) for db in dbs]
        def update_ui():
            sel_db = self.query_one("#sel-db", Select)
            sel_db.set_options(options)
            sel_db.disabled = False
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

            log_cmd(f"[cyan]📤 Dumping '{db}' from '{src}'...[/]")
            if not dump_database(servers[src], db, temp_dir, logger=log_cmd):
                log_cmd("[red]❌ Sync aborted due to dump failure.[/]")
                return

            log_cmd(f"[cyan]📥 Restoring to '{tgt}' as '{custom_db}'...[/]")
            if restore_database(servers[tgt], custom_db, str(temp_dir), source_db_name=db, logger=log_cmd):
                log_cmd("[green]✅ Synchronize completed successfully.[/]")
            else:
                log_cmd("[red]❌ Synchronize failed at restore stage.[/]")
            
            shutil.rmtree(temp_dir)
        finally:
            self.app.call_from_thread(self.set_running, False)


class ScheduleBackupScreen(ActionScreen):
    WEEKDAY_OPTIONS = [
        ("Monday", "1"),
        ("Tuesday", "2"),
        ("Wednesday", "3"),
        ("Thursday", "4"),
        ("Friday", "5"),
        ("Saturday", "6"),
        ("Sunday", "0"),
    ]
    DAY_OF_MONTH_OPTIONS = [(str(i), str(i)) for i in range(1, 32)]

    def compose_content(self) -> ComposeResult:
        servers = load_servers()
        s3_configured = is_s3_configured()

        with Vertical(classes="panel"):
            yield Label("Schedule Backup", classes="panel-title")
            yield from self.compose_log_panel()
            yield Select([(s, s) for s in servers.keys()], prompt="Select Target Server", id="sch-server")
            yield Select([], prompt="Select Database (Select Server first)", id="sch-db", disabled=True)
            yield Select(
                [
                    ("Every Day", "daily"),
                    ("Every Week", "weekly"),
                    ("Every Month", "monthly"),
                    ("Every 3 Months", "quarterly"),
                    ("Custom Cron", "custom"),
                ],
                prompt="Schedule Type",
                id="sch-type",
            )
            yield Select(self.WEEKDAY_OPTIONS, prompt="Day (for weekly)", id="sch-weekday", disabled=True)
            yield Select(self.DAY_OF_MONTH_OPTIONS, prompt="Day of month (for monthly/quarterly)", id="sch-monthday", disabled=True)
            yield Input(value="00:00", placeholder="HH:MM (24-hour)", id="sch-time")
            yield Input(placeholder="Custom cron (e.g. 0 2 1 */3 *)", id="sch-custom-cron", disabled=True)
            yield Checkbox("Compress to ZIP archive", value=True, id="sch-zip")
            yield Checkbox(
                "Upload ZIP to S3 (Cloudflare R2)",
                value=s3_configured,
                id="sch-s3",
                disabled=not s3_configured,
            )
            yield Button("💾 Save Schedule", id="btn-save-schedule", variant="success")

    @work(thread=True)
    def fetch_databases(self, server_name: str, uri: str) -> None:
        self.app.call_from_thread(self.write_log, f"[yellow]Fetching databases for '{server_name}'...[/]")
        dbs = get_accessible_databases(uri)
        options = [("📦 Backup All", "all")] + [(db, db) for db in dbs]

        def update_ui():
            sel_db = self.query_one("#sch-db", Select)
            sel_db.set_options(options)
            sel_db.disabled = False
            self.write_log("[green]Databases fetched for schedule form.[/]")

        self.app.call_from_thread(update_ui)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "sch-server" and event.value:
            servers = load_servers()
            uri = servers.get(event.value)
            if uri:
                self.query_one("#sch-db", Select).disabled = True
                self.fetch_databases(event.value, uri)

        if event.control.id == "sch-type":
            schedule_type = str(event.value)
            weekday_select = self.query_one("#sch-weekday", Select)
            monthday_select = self.query_one("#sch-monthday", Select)
            custom_cron_input = self.query_one("#sch-custom-cron", Input)

            weekday_select.disabled = schedule_type != "weekly"
            monthday_select.disabled = schedule_type not in ("monthly", "quarterly")
            custom_cron_input.disabled = schedule_type != "custom"

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id != "sch-zip":
            return
        s3_checkbox = self.query_one("#sch-s3", Checkbox)
        if not event.value:
            s3_checkbox.value = False
            s3_checkbox.disabled = True
            return
        if is_s3_configured():
            s3_checkbox.disabled = False

    def _parse_time(self, raw_time: str) -> tuple[int, int] | None:
        parts = raw_time.strip().split(":")
        if len(parts) != 2:
            return None
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except ValueError:
            return None
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None
        return hour, minute

    def _build_backup_command(self, server: str, db: str, do_zip: bool, do_s3: bool) -> str:
        cmd = f"python main.py backup {server} --db {db}"
        if do_zip:
            cmd += " --zip"
        if do_s3:
            cmd += " --s3"
        return cmd

    def _is_valid_cron_expression(self, cron_expression: str) -> bool:
        parts = cron_expression.strip().split()
        return len(parts) == 5

    def _save_schedule(self, item: dict) -> None:
        schedules = []
        if SCHEDULES_FILE.exists():
            try:
                with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
                    schedules = json.load(f)
                    if not isinstance(schedules, list):
                        schedules = []
            except Exception:
                schedules = []

        schedules.append(item)
        with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
            return

        if event.button.id != "btn-save-schedule":
            return

        server = self.query_one("#sch-server", Select).value
        db = self.query_one("#sch-db", Select).value
        schedule_type = self.query_one("#sch-type", Select).value
        weekday = self.query_one("#sch-weekday", Select).value
        monthday = self.query_one("#sch-monthday", Select).value
        raw_time = self.query_one("#sch-time", Input).value
        custom_cron = self.query_one("#sch-custom-cron", Input).value.strip()
        do_zip = self.query_one("#sch-zip", Checkbox).value
        do_s3 = self.query_one("#sch-s3", Checkbox).value

        if not server or not db or not schedule_type:
            self.write_log("[red]Please fill server, database, and schedule type.[/]")
            self.notify("Please fill server, database, and schedule type.", severity="error")
            return

        if do_s3 and not do_zip:
            self.write_log("[red]Upload to S3 requires 'Compress to ZIP archive'.[/]")
            self.notify("Upload to S3 requires 'Compress to ZIP archive'.", severity="error")
            return

        weekday_label = None
        monthday_label = None

        if schedule_type == "custom":
            if not self._is_valid_cron_expression(custom_cron):
                self.write_log("[red]Invalid custom cron expression.[/]")
                self.notify("Custom cron must have 5 fields (e.g. 0 2 1 */3 *).", severity="error")
                return
            cron_expr = custom_cron
            time_label = "custom"
        else:
            parsed_time = self._parse_time(raw_time)
            if not parsed_time:
                self.write_log("[red]Invalid time format for schedule.[/]")
                self.notify("Invalid time format. Use HH:MM (e.g. 02:30).", severity="error")
                return

            hour, minute = parsed_time
            time_label = f"{hour:02d}:{minute:02d}"

            if schedule_type == "daily":
                cron_expr = f"{minute} {hour} * * *"
            elif schedule_type == "weekly":
                if not weekday:
                    self.write_log("[red]Weekly schedule requires weekday selection.[/]")
                    self.notify("Please select day for weekly schedule.", severity="error")
                    return
                cron_expr = f"{minute} {hour} * * {weekday}"
                weekday_map = {value: label for label, value in self.WEEKDAY_OPTIONS}
                weekday_label = weekday_map.get(str(weekday), "Unknown")
            elif schedule_type == "monthly":
                if not monthday:
                    self.write_log("[red]Monthly schedule requires day-of-month selection.[/]")
                    self.notify("Please select day of month for monthly schedule.", severity="error")
                    return
                cron_expr = f"{minute} {hour} {monthday} * *"
                monthday_label = str(monthday)
            elif schedule_type == "quarterly":
                if not monthday:
                    self.write_log("[red]Quarterly schedule requires day-of-month selection.[/]")
                    self.notify("Please select day of month for quarterly schedule.", severity="error")
                    return
                cron_expr = f"{minute} {hour} {monthday} */3 *"
                monthday_label = str(monthday)
            else:
                self.write_log("[red]Unknown schedule type selected.[/]")
                self.notify("Unknown schedule type selected.", severity="error")
                return

        self.write_log(f"[cyan]Generated cron: {cron_expr}[/]")
        command = self._build_backup_command(str(server), str(db), do_zip, do_s3)
        cron_line = f"{cron_expr} cd {SCRIPT_DIR} && {command} >> {SCRIPT_DIR / 'cron.log'} 2>&1"

        schedule_item = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "server": str(server),
            "database": str(db),
            "schedule_type": str(schedule_type),
            "time": time_label,
            "weekday": weekday_label,
            "day_of_month": monthday_label,
            "zip": do_zip,
            "s3": do_s3,
            "cron": cron_expr,
            "command": command,
            "cron_line": cron_line,
        }

        self._save_schedule(schedule_item)
        self.write_log("[green]Schedule saved successfully.[/]")
        self.notify("Schedule saved to backup_schedules.json.", severity="information")
        self.notify(cron_line, title="Cron Line", timeout=12)


class ManageSchedulesScreen(ActionScreen):
    def _load_schedules(self) -> list[dict]:
        if not SCHEDULES_FILE.exists():
            return []
        try:
            with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
        return []

    def _save_schedules(self, schedules: list[dict]) -> None:
        with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2)

    def _format_schedule_option(self, idx: int, item: dict) -> tuple[str, str]:
        server = item.get("server", "-")
        database = item.get("database", "-")
        schedule_type = item.get("schedule_type", "-")
        time_str = item.get("time", "-")
        weekday = item.get("weekday")
        day_of_month = item.get("day_of_month")
        type_label = schedule_type
        if schedule_type == "weekly" and weekday:
            type_label = f"weekly ({weekday})"
        elif schedule_type == "monthly" and day_of_month:
            type_label = f"monthly (day {day_of_month})"
        elif schedule_type == "quarterly" and day_of_month:
            type_label = f"quarterly (day {day_of_month})"
        label = f"#{idx + 1} | {server} | {database} | {type_label} {time_str}"
        return label, str(idx)

    def _refresh_schedule_options(self) -> None:
        schedules = self._load_schedules()
        select = self.query_one("#sch-list", Select)
        delete_button = self.query_one("#btn-delete-schedule", Button)
        options = [self._format_schedule_option(i, item) for i, item in enumerate(schedules)]
        select.set_options(options)
        select.disabled = len(options) == 0
        delete_button.disabled = len(options) == 0
        self.write_log(f"[cyan]Loaded {len(options)} schedule(s).[/]")

        detail = self.query_one("#sch-detail", Label)
        status = self.query_one("#sch-manage-status", Label)
        if not options:
            detail.update("[yellow]No saved schedules found.[/]")
            status.update("")
        else:
            detail.update("Select a schedule to see detail.")

    def compose_content(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Manage Backup Schedules", classes="panel-title")
            yield from self.compose_log_panel()
            yield Select([], prompt="Select Schedule", id="sch-list")
            yield Label("Select a schedule to see detail.", id="sch-detail")
            yield Button("🔄 Refresh", id="btn-refresh-schedule")
            yield Button("🗑 Delete Selected", id="btn-delete-schedule", variant="error", disabled=True)
            yield Label("", id="sch-manage-status")

    def on_mount(self) -> None:
        self._refresh_schedule_options()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id != "sch-list":
            return
        if event.value is None:
            return

        schedules = self._load_schedules()
        detail = self.query_one("#sch-detail", Label)
        value_str = str(event.value)

        if not value_str.isdigit():
            detail.update("Select a schedule to see detail.")
            return

        try:
            idx = int(value_str)
        except ValueError:
            detail.update("Select a schedule to see detail.")
            return

        if idx < 0 or idx >= len(schedules):
            detail.update("Select a schedule to see detail.")
            return

        item = schedules[idx]
        self.query_one("#btn-delete-schedule", Button).disabled = False
        self.write_log(
            f"[yellow]Selected schedule #{idx + 1}: {item.get('server', '-')} / {item.get('database', '-')}[/]"
        )
        detail_lines = [
            f"Server: {item.get('server', '-')}",
            f"Database: {item.get('database', '-')}",
            f"Type: {item.get('schedule_type', '-')}",
            f"Time: {item.get('time', '-')}",
            f"Weekday: {item.get('weekday', '-')}",
            f"Day of month: {item.get('day_of_month', '-')}",
            f"Cron: {item.get('cron', '-')}",
            f"Command: {item.get('command', '-')}",
        ]
        detail.update("\n".join(detail_lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
            return

        if event.button.id == "btn-refresh-schedule":
            self._refresh_schedule_options()
            self.write_log("[green]Schedule list refreshed.[/]")
            return

        if event.button.id != "btn-delete-schedule":
            return

        status = self.query_one("#sch-manage-status", Label)
        select = self.query_one("#sch-list", Select)
        selected = select.value
        if selected is None:
            status.update("[red]Please select a schedule first.[/]")
            self.write_log("[red]Delete failed: no schedule selected.[/]")
            return

        schedules = self._load_schedules()
        try:
            idx = int(str(selected))
        except ValueError:
            status.update("[red]Invalid selected schedule.[/]")
            self.write_log("[red]Delete failed: invalid selected schedule.[/]")
            return

        if idx < 0 or idx >= len(schedules):
            status.update("[red]Selected schedule not found.[/]")
            self.write_log("[red]Delete failed: selected schedule not found.[/]")
            return

        removed = schedules.pop(idx)
        self._save_schedules(schedules)
        self._refresh_schedule_options()
        self.write_log(
            f"[green]Deleted schedule for server '{removed.get('server', '-')}' db '{removed.get('database', '-')}'.[/]"
        )
        status.update(
            f"[green]Deleted schedule for server '{removed.get('server', '-')}' db '{removed.get('database', '-')}'.[/]"
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

    def on_mount(self) -> None:
        self.push_screen("menu")

if __name__ == "__main__":
    app = MongoManagerApp()
    app.run()
