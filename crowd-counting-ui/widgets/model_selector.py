from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from config import MODELS
from style import COLOR_TEXT_MUTED
from widgets.icons import make_pixmap
from widgets.status_dot import make_dot_icon


class ModelSelector(QWidget):
    modelChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model_keys = list(MODELS.keys())

        caption_icon = QLabel(self)
        caption_icon.setPixmap(make_pixmap("chart", QColor(COLOR_TEXT_MUTED), 12))
        caption_text = QLabel("MODEL", self)
        caption_text.setObjectName("sectionCaption")

        caption_layout = QHBoxLayout()
        caption_layout.setContentsMargins(0, 0, 0, 0)
        caption_layout.setSpacing(6)
        caption_layout.addWidget(caption_icon)
        caption_layout.addWidget(caption_text)
        caption_layout.addStretch()

        self.combo = QComboBox(self)
        for key in self._model_keys:
            self.combo.addItem(make_dot_icon("unknown"), MODELS[key]["label"], userData=key)

        self.description_label = QLabel(self)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(caption_layout)
        layout.addWidget(self.combo)
        layout.addWidget(self.description_label)

        self.combo.currentIndexChanged.connect(self._on_index_changed)
        self._on_index_changed(self.combo.currentIndex())

    def _on_index_changed(self, index: int) -> None:
        key = self.combo.itemData(index)
        if key is None:
            return
        self.description_label.setText(MODELS[key]["description"])
        self.modelChanged.emit(key)

    def current_model_key(self) -> str:
        return self.combo.currentData()

    def set_model_key(self, key: str) -> None:
        index = self._model_keys.index(key)
        self.combo.setCurrentIndex(index)

    def update_status(self, model_key: str, is_up: bool) -> None:
        index = self._model_keys.index(model_key)
        state = "up" if is_up else "down"
        self.combo.setItemIcon(index, make_dot_icon(state))
