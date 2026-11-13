from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from history_store import HistoryEntry


class HistoryPanel(QWidget):
    entrySelected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.list_widget)

    def add_entry(self, entry: HistoryEntry) -> None:
        item = QListWidgetItem(entry.label())
        item.setData(Qt.UserRole, entry)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        entry = item.data(Qt.UserRole)
        if entry is not None:
            self.entrySelected.emit(entry)
