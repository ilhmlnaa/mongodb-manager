from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import ScrollableContainer
from textual.widgets import Footer, Label, Button, RichLog

class BaseScreen(Screen):
    """A base screen to share common layout: Header and Footer."""
    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="main-container"):
            yield from self.compose_content()
        yield Footer()

    def compose_content(self) -> ComposeResult:
        yield Label("Override this in subclasses")


class ActionScreen(BaseScreen):
    """Base Screen for Backup, Restore, Sync with a Log Panel."""
    def compose_log_panel(self) -> ComposeResult:
        yield Label("Process Log:", classes="log-label")
        log_panel = RichLog(highlight=True, markup=True, id="rich-log")
        log_panel.can_focus = False
        yield log_panel
        yield Button("Back to Menu", id="btn-back", disabled=False)

    def write_log(self, text: str) -> None:
        log_widget = self.query_one("#rich-log", RichLog)
        log_widget.write(text)

    def set_running(self, running: bool) -> None:
        back_btn = self.query_one("#btn-back", Button)
        back_btn.disabled = running
        for btn in self.query(Button):
            if btn.id != "btn-back":
                btn.disabled = running
