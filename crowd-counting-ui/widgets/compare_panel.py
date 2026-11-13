from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import MODELS
from models import PredictionResult
from style import (
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_TEXT_MUTED,
    RADIUS_SM,
    make_card,
)
from widgets.icons import make_icon

STATUS_COLORS = {
    "idle": COLOR_TEXT_MUTED,
    "loading": COLOR_PRIMARY,
    "done": COLOR_SUCCESS,
    "error": COLOR_DANGER,
}


class _ModelResultCell(QWidget):
    def __init__(self, model_key: str, parent=None):
        super().__init__(parent)
        self.model_key = model_key
        self.setObjectName("cell")
        make_card(self)

        self.name_label = QLabel(MODELS[model_key]["label"], self)
        self.name_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        self.name_label.setAlignment(Qt.AlignCenter)

        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setFixedSize(140, 140)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet(
            f"border: 1px solid {COLOR_BORDER}; border-radius: {RADIUS_SM}px; background: transparent;"
        )

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setTextVisible(False)

        self.count_label = QLabel("—", self)
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLOR_PRIMARY};")

        self.time_label = QLabel("—", self)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")

        self.status_label = QLabel("Idle", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']}; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 20)
        layout.setSpacing(8)
        layout.addWidget(self.name_label)
        layout.addWidget(self.thumbnail_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.count_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.status_label)

    def set_loading(self) -> None:
        self.progress_bar.setVisible(True)
        self.count_label.setText("—")
        self.time_label.setText("—")
        self.thumbnail_label.clear()
        self.status_label.setText("Running…")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['loading']}; font-size: 11px;")
        self.status_label.setToolTip("")

    def set_result(self, result: PredictionResult, density_map_bytes: bytes, reused: bool = False) -> None:
        self.progress_bar.setVisible(False)
        self.count_label.setText(str(result.rounded_count))
        self.time_label.setText(f"{result.inference_time_seconds:.4f} s")

        pixmap = QPixmap()
        pixmap.loadFromData(density_map_bytes)
        scaled = pixmap.scaled(
            self.thumbnail_label.width(),
            self.thumbnail_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.thumbnail_label.setPixmap(scaled)
        status_text = "Current result" if reused else "Done"
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['done']}; font-size: 11px;")
        self.status_label.setToolTip(
            "Reused from the result already shown above — not re-sent to the service." if reused else ""
        )

    def set_error(self, message: str) -> None:
        self.progress_bar.setVisible(False)
        self.count_label.setText("—")
        self.time_label.setText("—")
        self.thumbnail_label.clear()
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['error']}; font-size: 11px;")
        self.status_label.setToolTip(message)

    def reset(self) -> None:
        self.progress_bar.setVisible(False)
        self.count_label.setText("—")
        self.time_label.setText("—")
        self.thumbnail_label.clear()
        self.status_label.setText("Idle")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']}; font-size: 11px;")
        self.status_label.setToolTip("")


class ComparePanel(QWidget):
    compareRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.toggle_button = QToolButton(self)
        self.toggle_button.setText("Compare with all models")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.clicked.connect(self._on_toggle)

        self.run_button = QPushButton("Run comparison", self)
        self.run_button.setObjectName("primaryButton")
        self.run_button.setIcon(
            make_icon("play", QColor("white"), 13, disabled_color=QColor(COLOR_TEXT_MUTED))
        )
        self.run_button.clicked.connect(self.compareRequested.emit)

        self.content_frame = QFrame(self)
        self.content_frame.setObjectName("compareCard")
        self.content_frame.setVisible(False)

        grid_widget = QWidget(self.content_frame)
        grid = QGridLayout(grid_widget)
        grid.setSpacing(16)

        self.cells: dict[str, _ModelResultCell] = {}
        for column, model_key in enumerate(MODELS.keys()):
            cell = _ModelResultCell(model_key, grid_widget)
            self.cells[model_key] = cell
            grid.addWidget(cell, 0, column)

        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)
        content_layout.addWidget(self.run_button)
        content_layout.addWidget(grid_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_frame)

    def _on_toggle(self) -> None:
        expanded = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.content_frame.setVisible(expanded)

    def set_loading(self, model_key: str) -> None:
        self.cells[model_key].set_loading()

    def set_result(
        self, model_key: str, result: PredictionResult, density_map_bytes: bytes, reused: bool = False
    ) -> None:
        self.cells[model_key].set_result(result, density_map_bytes, reused=reused)

    def set_error(self, model_key: str, message: str) -> None:
        self.cells[model_key].set_error(message)

    def reset(self) -> None:
        for cell in self.cells.values():
            cell.reset()
