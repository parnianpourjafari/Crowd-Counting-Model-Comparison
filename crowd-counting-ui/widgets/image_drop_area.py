from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from config import ALLOWED_IMAGE_SUFFIXES, MAX_UPLOAD_SIZE_MB
from style import (
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SOFT,
    COLOR_TEXT_MUTED,
    RADIUS_SM,
)
from widgets.icons import make_icon

PLACEHOLDER_TEXT = "Drag & drop an image here\nor click Browse…"

IDLE_STYLE = (
    f"QLabel {{ border: 2px dashed {COLOR_BORDER}; border-radius: {RADIUS_SM}px; "
    f"color: {COLOR_TEXT_MUTED}; background-color: transparent; }}"
)
DRAG_ACTIVE_STYLE = (
    f"QLabel {{ border: 2px dashed {COLOR_PRIMARY}; border-radius: {RADIUS_SM}px; "
    f"color: {COLOR_PRIMARY}; background-color: {COLOR_PRIMARY_SOFT}; }}"
)
LOADED_STYLE = (
    f"QLabel {{ border: 1px solid {COLOR_BORDER}; border-radius: {RADIUS_SM}px; "
    f"background-color: transparent; }}"
)


class ImageDropArea(QWidget):
    imageLoaded = pyqtSignal(str, bytes)
    invalidFile = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.preview_label = QLabel(PLACEHOLDER_TEXT, self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet(IDLE_STYLE)

        self.browse_button = QPushButton("Browse…", self)
        self.browse_button.setIcon(make_icon("upload", QColor(COLOR_TEXT_MUTED), 13))
        self.browse_button.clicked.connect(self._browse)

        self._current_pixmap: QPixmap | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.browse_button)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.preview_label.setStyleSheet(DRAG_ACTIVE_STYLE)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.preview_label.setStyleSheet(IDLE_STYLE)

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.preview_label.setStyleSheet(IDLE_STYLE)
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path:
            self._load_path(path)

    def _browse(self) -> None:
        suffixes = " ".join(f"*{s}" for s in sorted(ALLOWED_IMAGE_SUFFIXES))
        path, _ = QFileDialog.getOpenFileName(
            self, "Select an image", "", f"Images ({suffixes})"
        )
        if path:
            self._load_path(path)

    def _load_path(self, path: str) -> None:
        file_path = Path(path)

        if file_path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            self.invalidFile.emit(
                "Unsupported file type. Use JPEG, PNG, BMP, WEBP, or TIFF."
            )
            return

        try:
            data = file_path.read_bytes()
        except OSError as error:
            self.invalidFile.emit(f"Could not read file: {error}")
            return

        max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            self.invalidFile.emit(f"Image must be at most {MAX_UPLOAD_SIZE_MB} MB.")
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            self.invalidFile.emit("The selected file is not a valid image.")
            return

        self._show_thumbnail(pixmap)
        self.imageLoaded.emit(file_path.name, data)

    def _show_thumbnail(self, pixmap: QPixmap) -> None:
        self._current_pixmap = pixmap
        self._rescale_thumbnail()
        self.preview_label.setStyleSheet(LOADED_STYLE)

    def _rescale_thumbnail(self) -> None:
        if self._current_pixmap is None:
            return
        scaled = self._current_pixmap.scaled(
            self.preview_label.width() or 300,
            self.preview_label.height() or 200,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._rescale_thumbnail()

    def reset(self) -> None:
        self._current_pixmap = None
        self.preview_label.clear()
        self.preview_label.setText(PLACEHOLDER_TEXT)
        self.preview_label.setStyleSheet(IDLE_STYLE)
