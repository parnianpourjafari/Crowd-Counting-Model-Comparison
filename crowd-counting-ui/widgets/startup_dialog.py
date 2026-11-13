from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from config import MODELS
from style import COLOR_TEXT_MUTED
from widgets.status_dot import StatusDot

STATUS_TEXT = {
    "checking": "Checking...",
    "starting": "Starting...",
    "ready": "Ready",
    "failed": "Failed - see logs",
}

STATUS_DOT_STATE = {
    "checking": "unknown",
    "starting": "unknown",
    "ready": "up",
    "failed": "down",
}


class StartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crowd Counting Client")
        self.setModal(True)
        self.setFixedWidth(320)
        # Startup isn't user-cancellable (there's nothing to cancel back to
        # yet), so don't let Escape/[X] dismiss it — that used to leave the
        # app looking hung with no visible window while services kept
        # starting in the background. See reject() below.
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        self._dots = {}
        self._status_labels = {}

        title_label = QLabel("Starting services...", self)
        title_label.setStyleSheet("font-weight: 700; font-size: 14px;")

        rows_layout = QVBoxLayout()
        rows_layout.setSpacing(12)
        for model_key, cfg in MODELS.items():
            dot = StatusDot(self)
            dot.set_state("unknown")

            name_label = QLabel(cfg["label"], self)

            status_label = QLabel("Checking...", self)
            status_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")

            row_layout = QHBoxLayout()
            row_layout.addWidget(dot)
            row_layout.addWidget(name_label)
            row_layout.addStretch()
            row_layout.addWidget(status_label)
            rows_layout.addLayout(row_layout)

            self._dots[model_key] = dot
            self._status_labels[model_key] = status_label

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(title_label)
        layout.addLayout(rows_layout)

    def reject(self) -> None:
        pass  # ignore Escape/close attempts; the dialog closes via accept() only

    def update_service(self, model_key: str, status: str) -> None:
        if model_key not in self._dots:
            return
        self._dots[model_key].set_state(STATUS_DOT_STATE.get(status, "unknown"))
        self._status_labels[model_key].setText(STATUS_TEXT.get(status, status))
