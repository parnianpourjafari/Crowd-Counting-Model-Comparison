import subprocess
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget


def _detect_dark_mode() -> bool:
    """Launch-time only — does not live-update if the OS theme changes
    while the app is running, since this runs before QApplication exists
    (style.py is imported transitively before main() creates it)."""
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        return result.returncode == 0 and result.stdout.strip() == "Dark"
    except Exception:
        return False


IS_DARK = _detect_dark_mode()

_LIGHT = {
    "bg": "#f5f5f7",
    "surface": "#ffffff",
    "border": "#e5e5ea",
    "text": "#1d1d1f",
    "text_muted": "#6e6e73",
    "text_faint": "#a1a1a6",
    "primary": "#4f46e5",
    "primary_hover": "#4338ca",
    "primary_pressed": "#3730a3",
    "primary_soft": "#eef2ff",
    "success": "#22c55e",
    "danger": "#ef4444",
    "muted_dot": "#c7c7cc",
    "input_border": "#d1d1d6",
    "hover": "#ececee",
    "pressed": "#e0e0e2",
    "scrollbar": "#c7c7cc",
    "scrollbar_hover": "#a1a1a6",
    "shadow": (15, 23, 42, 18),
}

_DARK = {
    "bg": "#1c1c1e",
    "surface": "#2c2c2e",
    "border": "#3a3a3c",
    "text": "#f5f5f7",
    "text_muted": "#98989d",
    "text_faint": "#6e6e73",
    "primary": "#818cf8",
    "primary_hover": "#a5b4fc",
    "primary_pressed": "#6366f1",
    "primary_soft": "#33314f",
    "success": "#34d399",
    "danger": "#f87171",
    "muted_dot": "#48484a",
    "input_border": "#48484a",
    "hover": "#3a3a3c",
    "pressed": "#48484a",
    "scrollbar": "#48484a",
    "scrollbar_hover": "#6e6e73",
    "shadow": (0, 0, 0, 60),
}

_C = _DARK if IS_DARK else _LIGHT

COLOR_BG = _C["bg"]
COLOR_CARD = _C["surface"]
COLOR_BORDER = _C["border"]
COLOR_TEXT = _C["text"]
COLOR_TEXT_MUTED = _C["text_muted"]
COLOR_TEXT_FAINT = _C["text_faint"]
COLOR_PRIMARY = _C["primary"]
COLOR_PRIMARY_HOVER = _C["primary_hover"]
COLOR_PRIMARY_PRESSED = _C["primary_pressed"]
COLOR_PRIMARY_SOFT = _C["primary_soft"]
COLOR_SUCCESS = _C["success"]
COLOR_DANGER = _C["danger"]
COLOR_MUTED_DOT = _C["muted_dot"]
COLOR_INPUT_BORDER = _C["input_border"]
COLOR_HOVER = _C["hover"]
COLOR_PRESSED = _C["pressed"]
COLOR_SCROLLBAR = _C["scrollbar"]
COLOR_SCROLLBAR_HOVER = _C["scrollbar_hover"]
_SHADOW_RGBA = _C["shadow"]

# Two radii used everywhere instead of arbitrary per-widget values.
RADIUS_SM = 8   # buttons, inputs, chips, thumbnails
RADIUS_MD = 14  # cards, panels

# Shared spacing scale for layout margins/spacing across widget files.
SPACE_XS = 6
SPACE_SM = 10
SPACE_MD = 16
SPACE_LG = 24

APP_STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-size: 13px;
}}

QMainWindow {{
    background-color: {COLOR_BG};
}}

QLabel {{
    background-color: transparent;
}}

QLabel#titleLabel {{
    font-size: 22px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}

QLabel#sectionCaption {{
    color: {COLOR_TEXT_MUTED};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}}

QWidget#leftColumn, QWidget#resultCard, QFrame#compareCard, QWidget#cell {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_MD}px;
}}

QPushButton {{
    background-color: transparent;
    border: 1px solid {COLOR_INPUT_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 9px 18px;
    font-weight: 600;
    color: {COLOR_TEXT};
}}
QPushButton:hover {{
    background-color: {COLOR_HOVER};
    border-color: {COLOR_TEXT_FAINT};
}}
QPushButton:pressed {{
    background-color: {COLOR_PRESSED};
}}
QPushButton:disabled {{
    color: {COLOR_TEXT_FAINT};
    background-color: transparent;
    border-color: {COLOR_BORDER};
}}
QPushButton:checkable:checked {{
    background-color: {COLOR_PRIMARY_SOFT};
    border-color: {COLOR_PRIMARY};
    color: {COLOR_PRIMARY_HOVER};
}}
QPushButton:default {{
    border-color: {COLOR_PRIMARY};
}}

QPushButton#primaryButton {{
    background-color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_PRIMARY};
    color: white;
}}
QPushButton#primaryButton:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
    border-color: {COLOR_PRIMARY_HOVER};
}}
QPushButton#primaryButton:pressed {{
    background-color: {COLOR_PRIMARY_PRESSED};
}}
QPushButton#primaryButton:disabled {{
    background-color: {COLOR_PRIMARY_SOFT};
    border-color: {COLOR_PRIMARY_SOFT};
    color: {COLOR_TEXT_FAINT};
}}

QComboBox {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_INPUT_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 8px 12px;
}}
QComboBox:hover {{
    border-color: {COLOR_TEXT_FAINT};
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_PRIMARY_SOFT};
    selection-color: {COLOR_PRIMARY_HOVER};
    outline: none;
    padding: 4px;
}}

QProgressBar {{
    border: none;
    background-color: {COLOR_BORDER};
    border-radius: 3px;
    max-height: 4px;
    min-height: 4px;
}}
QProgressBar::chunk {{
    background-color: {COLOR_PRIMARY};
    border-radius: 3px;
}}

QListWidget {{
    background-color: {COLOR_CARD};
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 10px;
    border-radius: {RADIUS_SM}px;
    margin: 2px 0px;
}}
QListWidget::item:selected {{
    background-color: {COLOR_PRIMARY_SOFT};
    color: {COLOR_PRIMARY_HOVER};
}}
QListWidget::item:hover {{
    background-color: {COLOR_HOVER};
}}

QDockWidget {{
    font-weight: 600;
    color: {COLOR_TEXT};
}}
QDockWidget::title {{
    background-color: {COLOR_BG};
    padding: 12px;
    border-bottom: 1px solid {COLOR_BORDER};
}}

QToolButton {{
    border: none;
    background: transparent;
    font-weight: 600;
    color: {COLOR_TEXT_MUTED};
    padding: 6px 4px;
}}
QToolButton:hover {{
    color: {COLOR_TEXT};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_SCROLLBAR};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_SCROLLBAR_HOVER};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QMessageBox, QFileDialog, QInputDialog {{
    background-color: {COLOR_CARD};
}}
"""


def make_card(widget: QWidget) -> None:
    widget.setAttribute(Qt.WA_StyledBackground, True)


def apply_card_shadow(widget: QWidget) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(18)
    effect.setXOffset(0)
    effect.setYOffset(1)
    effect.setColor(QColor(*_SHADOW_RGBA))
    widget.setGraphicsEffect(effect)
