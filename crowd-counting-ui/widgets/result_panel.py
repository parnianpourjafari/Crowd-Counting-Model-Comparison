from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models import PredictionResult
from style import COLOR_PRIMARY, COLOR_TEXT, COLOR_TEXT_FAINT, COLOR_TEXT_MUTED
from widgets.icons import make_icon
from widgets.zoomable_image_view import ZoomableImageView


class ResultPanel(QWidget):
    exportRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.model_label = QLabel("No model run yet", self)
        self.model_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-weight: 600;")

        self.count_label = QLabel("—", self)
        self.count_label.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {COLOR_PRIMARY};")

        self.time_label = QLabel("—", self)
        self.time_label.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {COLOR_TEXT};")

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)

        self.export_button = QPushButton("Export…", self)
        self.export_button.setIcon(
            make_icon("download", QColor(COLOR_TEXT_MUTED), 13, disabled_color=QColor(COLOR_TEXT_FAINT))
        )
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.exportRequested.emit)

        self.image_view = ZoomableImageView(self)
        self.image_view.setMinimumHeight(280)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.model_label)
        header_layout.addStretch()
        header_layout.addWidget(self.export_button)

        count_caption = QLabel("ESTIMATED COUNT", self)
        count_caption.setObjectName("sectionCaption")
        time_caption = QLabel("INFERENCE TIME", self)
        time_caption.setObjectName("sectionCaption")

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(36)

        count_block = QVBoxLayout()
        count_block.setSpacing(4)
        count_block.addWidget(count_caption)
        count_block.addWidget(self.count_label)

        time_block = QVBoxLayout()
        time_block.setSpacing(4)
        time_block.addWidget(time_caption)
        time_block.addWidget(self.time_label)

        stats_layout.addLayout(count_block)
        stats_layout.addLayout(time_block)
        stats_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(18)
        layout.addLayout(header_layout)
        layout.addLayout(stats_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.image_view, stretch=1)

    def show_loading(self, model_label: str) -> None:
        self.model_label.setText(f"Model: {model_label}")
        self.progress_bar.setVisible(True)
        self.export_button.setEnabled(False)

    def hide_loading(self) -> None:
        self.progress_bar.setVisible(False)

    def show_result(self, model_label: str, result: PredictionResult, density_map_bytes: bytes) -> None:
        self.progress_bar.setVisible(False)
        self.model_label.setText(f"Model: {model_label}")
        self.count_label.setText(str(result.rounded_count))
        self.time_label.setText(f"{result.inference_time_seconds:.4f} s")
        self.image_view.set_image(density_map_bytes)
        self.export_button.setEnabled(True)

    def reset(self) -> None:
        self.progress_bar.setVisible(False)
        self.model_label.setText("No model run yet")
        self.count_label.setText("—")
        self.time_label.setText("—")
        self.image_view.clear()
        self.export_button.setEnabled(False)
