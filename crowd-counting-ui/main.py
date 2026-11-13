import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from main_window import MainWindow
from service_manager import ServiceManager
from style import APP_STYLESHEET
from widgets.startup_dialog import StartupDialog


class ServiceStartupWorker(QThread):
    serviceStatus = pyqtSignal(str, str)
    startupFinished = pyqtSignal()

    def __init__(self, service_manager: ServiceManager, parent=None):
        super().__init__(parent)
        self.service_manager = service_manager

    def run(self) -> None:
        self.service_manager.start_all(
            lambda model_key, status: self.serviceStatus.emit(model_key, status)
        )
        self.startupFinished.emit()


def main() -> None:
    app = QApplication(sys.argv)
    # Fusion renders every widget (including native dialogs like QMessageBox
    # and QFileDialog) from the app's own palette/stylesheet instead of the
    # OS's Aqua widgets, so they stay consistent with the app's theme instead
    # of drifting to match OS dark mode independently.
    app.setStyle("Fusion")
    # The default QFont already resolves to the OS system font (San
    # Francisco on macOS) without needing to name it — naming "-apple-system"
    # in QSS doesn't work, Qt's font matcher doesn't understand that CSS-only
    # keyword and falls back with a warning.
    app.setFont(QFont(app.font().family(), 13))
    app.setStyleSheet(APP_STYLESHEET)

    service_manager = ServiceManager()
    app.aboutToQuit.connect(service_manager.stop_owned)

    startup_dialog = StartupDialog()
    startup_worker = ServiceStartupWorker(service_manager)
    startup_worker.serviceStatus.connect(startup_dialog.update_service)
    startup_worker.startupFinished.connect(startup_dialog.accept)
    startup_worker.start()
    startup_dialog.exec_()
    startup_worker.wait()

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
