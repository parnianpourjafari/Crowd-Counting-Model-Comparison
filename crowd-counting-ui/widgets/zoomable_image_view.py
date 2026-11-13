from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QToolButton,
    QWidget,
)

from style import COLOR_BORDER, RADIUS_SM
from widgets.icons import make_icon

ZOOM_IN_FACTOR = 1.15
ZOOM_OUT_FACTOR = 1 / ZOOM_IN_FACTOR
MIN_SCALE = 0.2
MAX_SCALE = 12.0
CANVAS_COLOR = QColor("#1f2937")

# The density-map canvas is always dark (for image contrast) regardless of
# the app's light/dark theme, so the zoom overlay uses a fixed dark/white
# look rather than the theme tokens.
_ZOOM_BUTTON_STYLE = """
QToolButton {
    background-color: rgba(0, 0, 0, 140);
    border: none;
    border-radius: 14px;
    padding: 0px;
}
QToolButton:hover {
    background-color: rgba(0, 0, 0, 185);
}
QToolButton:disabled {
    background-color: rgba(0, 0, 0, 60);
}
"""


class ZoomableImageView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._scale_factor = 1.0

        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(CANVAS_COLOR)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setStyleSheet(f"border: 1px solid {COLOR_BORDER}; border-radius: {RADIUS_SM}px;")

        self._zoom_out_button = self._make_zoom_button("zoom-out", self.zoom_out)
        self._zoom_in_button = self._make_zoom_button("zoom-in", self.zoom_in)
        self._set_zoom_buttons_enabled(False)

        controls = QWidget(self)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)
        controls_layout.addWidget(self._zoom_out_button)
        controls_layout.addWidget(self._zoom_in_button)
        self._controls = controls

    def _make_zoom_button(self, icon_name: str, on_click) -> QToolButton:
        button = QToolButton(self)
        button.setIcon(make_icon(icon_name, QColor("white"), 14))
        button.setFixedSize(QSize(28, 28))
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(_ZOOM_BUTTON_STYLE)
        button.clicked.connect(on_click)
        return button

    def _set_zoom_buttons_enabled(self, enabled: bool) -> None:
        self._zoom_in_button.setEnabled(enabled)
        self._zoom_out_button.setEnabled(enabled)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        margin = 12
        x = self.viewport().width() - self._controls.sizeHint().width() - margin
        y = self.viewport().height() - self._controls.sizeHint().height() - margin
        self._controls.move(max(x, 0), max(y, 0))
        self._controls.adjustSize()

    def set_image(self, image_bytes: bytes) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._scale_factor = 1.0
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        self._set_zoom_buttons_enabled(True)

    def clear(self) -> None:
        self._scene.clear()
        self._pixmap_item = None
        self._scale_factor = 1.0
        self.resetTransform()
        self._set_zoom_buttons_enabled(False)

    def zoom_in(self) -> None:
        self._apply_zoom(ZOOM_IN_FACTOR)

    def zoom_out(self) -> None:
        self._apply_zoom(ZOOM_OUT_FACTOR)

    def _apply_zoom(self, factor: float) -> None:
        if self._pixmap_item is None:
            return

        new_scale = min(max(self._scale_factor * factor, MIN_SCALE), MAX_SCALE)
        if new_scale == self._scale_factor:
            return

        applied_factor = new_scale / self._scale_factor
        self._scale_factor = new_scale
        self.scale(applied_factor, applied_factor)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt override
        factor = ZOOM_IN_FACTOR if event.angleDelta().y() > 0 else ZOOM_OUT_FACTOR
        self._apply_zoom(factor)
