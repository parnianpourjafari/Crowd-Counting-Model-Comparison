from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget

from style import COLOR_DANGER, COLOR_MUTED_DOT, COLOR_SUCCESS

STATE_COLORS = {
    "up": QColor(COLOR_SUCCESS),
    "down": QColor(COLOR_DANGER),
    "unknown": QColor(COLOR_MUTED_DOT),
}


def make_dot_pixmap(state: str, size: int = 10) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(STATE_COLORS.get(state, STATE_COLORS["unknown"]))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return pixmap


def make_dot_icon(state: str, size: int = 10) -> QIcon:
    return QIcon(make_dot_pixmap(state, size))


class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "unknown"
        self.setFixedSize(QSize(12, 12))

    def set_state(self, state: str) -> None:
        if state not in STATE_COLORS:
            state = "unknown"
        self._state = state
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(STATE_COLORS[self._state])
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
