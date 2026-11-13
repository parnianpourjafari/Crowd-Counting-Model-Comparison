from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

# Small hand-drawn line icons rendered via QPainter — no external icon
# fonts/assets, and fully recolorable per theme by passing a QColor.


def _new_painter(size: int, color: QColor, stroke_width: float = 1.6) -> tuple:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color)
    pen.setWidthF(stroke_width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    return pixmap, painter


def _draw_upload(painter: QPainter, s: float) -> None:
    painter.drawLine(QPointF(s * 0.5, s * 0.18), QPointF(s * 0.5, s * 0.62))
    head = QPainterPath()
    head.moveTo(s * 0.32, s * 0.36)
    head.lineTo(s * 0.5, s * 0.18)
    head.lineTo(s * 0.68, s * 0.36)
    painter.drawPath(head)
    tray = QPainterPath()
    tray.moveTo(s * 0.2, s * 0.68)
    tray.lineTo(s * 0.2, s * 0.82)
    tray.lineTo(s * 0.8, s * 0.82)
    tray.lineTo(s * 0.8, s * 0.68)
    painter.drawPath(tray)


def _draw_download(painter: QPainter, s: float) -> None:
    painter.drawLine(QPointF(s * 0.5, s * 0.16), QPointF(s * 0.5, s * 0.6))
    head = QPainterPath()
    head.moveTo(s * 0.32, s * 0.42)
    head.lineTo(s * 0.5, s * 0.6)
    head.lineTo(s * 0.68, s * 0.42)
    painter.drawPath(head)
    tray = QPainterPath()
    tray.moveTo(s * 0.2, s * 0.68)
    tray.lineTo(s * 0.2, s * 0.82)
    tray.lineTo(s * 0.8, s * 0.82)
    tray.lineTo(s * 0.8, s * 0.68)
    painter.drawPath(tray)


def _draw_play(painter: QPainter, s: float) -> None:
    path = QPainterPath()
    path.moveTo(s * 0.32, s * 0.2)
    path.lineTo(s * 0.32, s * 0.8)
    path.lineTo(s * 0.8, s * 0.5)
    path.closeSubpath()
    painter.setBrush(painter.pen().color())
    painter.drawPath(path)


def _draw_refresh(painter: QPainter, s: float) -> None:
    rect = QRectF(s * 0.18, s * 0.18, s * 0.64, s * 0.64)
    painter.drawArc(rect, 40 * 16, 260 * 16)
    head = QPainterPath()
    head.moveTo(s * 0.78, s * 0.22)
    head.lineTo(s * 0.84, s * 0.38)
    head.lineTo(s * 0.66, s * 0.34)
    head.closeSubpath()
    painter.setBrush(painter.pen().color())
    painter.drawPath(head)


def _draw_clock(painter: QPainter, s: float) -> None:
    rect = QRectF(s * 0.15, s * 0.15, s * 0.7, s * 0.7)
    painter.drawEllipse(rect)
    painter.drawLine(QPointF(s * 0.5, s * 0.5), QPointF(s * 0.5, s * 0.3))
    painter.drawLine(QPointF(s * 0.5, s * 0.5), QPointF(s * 0.65, s * 0.58))


def _draw_magnifier(painter: QPainter, s: float) -> None:
    rect = QRectF(s * 0.18, s * 0.18, s * 0.48, s * 0.48)
    painter.drawEllipse(rect)
    painter.drawLine(QPointF(s * 0.62, s * 0.62), QPointF(s * 0.84, s * 0.84))


def _draw_zoom_in(painter: QPainter, s: float) -> None:
    _draw_magnifier(painter, s)
    painter.drawLine(QPointF(s * 0.3, s * 0.42), QPointF(s * 0.54, s * 0.42))
    painter.drawLine(QPointF(s * 0.42, s * 0.3), QPointF(s * 0.42, s * 0.54))


def _draw_zoom_out(painter: QPainter, s: float) -> None:
    _draw_magnifier(painter, s)
    painter.drawLine(QPointF(s * 0.3, s * 0.42), QPointF(s * 0.54, s * 0.42))


def _draw_chart(painter: QPainter, s: float) -> None:
    painter.drawLine(QPointF(s * 0.2, s * 0.5), QPointF(s * 0.2, s * 0.82))
    painter.drawLine(QPointF(s * 0.46, s * 0.32), QPointF(s * 0.46, s * 0.82))
    painter.drawLine(QPointF(s * 0.72, s * 0.42), QPointF(s * 0.72, s * 0.82))
    painter.drawLine(QPointF(s * 0.14, s * 0.82), QPointF(s * 0.86, s * 0.82))


_DRAWERS = {
    "upload": _draw_upload,
    "download": _draw_download,
    "play": _draw_play,
    "refresh": _draw_refresh,
    "clock": _draw_clock,
    "zoom-in": _draw_zoom_in,
    "zoom-out": _draw_zoom_out,
    "chart": _draw_chart,
}


def make_icon(name: str, color: QColor, size: int = 16, disabled_color: QColor | None = None) -> QIcon:
    drawer = _DRAWERS.get(name)
    if drawer is None:
        raise ValueError(f"Unknown icon: {name}")

    icon = QIcon()
    pixmap, painter = _new_painter(size, color)
    drawer(painter, float(size))
    painter.end()
    icon.addPixmap(pixmap, QIcon.Normal)

    if disabled_color is not None:
        dis_pixmap, dis_painter = _new_painter(size, disabled_color)
        drawer(dis_painter, float(size))
        dis_painter.end()
        icon.addPixmap(dis_pixmap, QIcon.Disabled)

    return icon


def make_pixmap(name: str, color: QColor, size: int = 16) -> QPixmap:
    drawer = _DRAWERS.get(name)
    if drawer is None:
        raise ValueError(f"Unknown icon: {name}")
    pixmap, painter = _new_painter(size, color)
    drawer(painter, float(size))
    painter.end()
    return pixmap
