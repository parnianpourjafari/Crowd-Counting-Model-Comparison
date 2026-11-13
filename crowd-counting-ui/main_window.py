import datetime
from dataclasses import dataclass

from PyQt5.QtCore import QThreadPool, QTimer, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient
from config import HEALTH_CHECK_INTERVAL_MS, MODELS
from history_store import HistoryEntry, HistoryStore
from models import ApiError, PredictionResult, ServiceUnavailableError
from style import COLOR_TEXT_FAINT, COLOR_TEXT_MUTED, apply_card_shadow, make_card
from widgets.compare_panel import ComparePanel
from widgets.history_panel import HistoryPanel
from widgets.icons import make_icon
from widgets.image_drop_area import ImageDropArea
from widgets.model_selector import ModelSelector
from widgets.result_panel import ResultPanel
from workers import HealthCheckWorker, PredictWorker


@dataclass
class AppState:
    image_filename: str | None = None
    image_bytes: bytes | None = None
    last_result: PredictionResult | None = None
    last_density_map_bytes: bytes | None = None
    last_model_label: str | None = None
    last_model_key: str | None = None
    # The exact image bytes that produced last_result, so Compare can tell
    # whether that cached result still matches the currently loaded image
    # before reusing it (identity check, not a content comparison).
    last_result_image_bytes: bytes | None = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crowd Counting Client")
        self.resize(1200, 820)

        self.state = AppState()
        self.thread_pool = QThreadPool.globalInstance()
        self.history_store = HistoryStore()

        self.clients = {
            key: ApiClient(key, cfg["label"], cfg["base_url"], cfg["port"])
            for key, cfg in MODELS.items()
        }

        self._pending_compare = set()
        # Monotonic counters used to discard results/errors from requests
        # that were superseded by a Reset (or a newer comparison run) before
        # they came back, so a stale response can't silently repopulate the
        # UI or history after the user has moved on.
        self._run_generation = 0
        self._compare_generation = 0
        self._model_health: dict[str, bool] = {}

        self._build_ui()
        self._wire_signals()
        self._start_health_monitor()

    def _build_ui(self) -> None:
        title_label = QLabel("Crowd Counting Client", self)
        title_label.setObjectName("titleLabel")

        header_layout = QVBoxLayout()
        header_layout.addWidget(title_label)

        self.model_selector = ModelSelector(self)
        self.image_drop_area = ImageDropArea(self)

        self.run_button = QPushButton("Run", self)
        self.run_button.setObjectName("primaryButton")
        self.run_button.setIcon(
            make_icon("play", QColor("white"), 13, disabled_color=QColor(COLOR_TEXT_FAINT))
        )
        self.run_button.setEnabled(False)

        self.reset_button = QPushButton("Reset", self)
        self.reset_button.setIcon(make_icon("refresh", QColor(COLOR_TEXT_MUTED), 13))

        self.history_button = QPushButton("History", self)
        self.history_button.setIcon(make_icon("clock", QColor(COLOR_TEXT_MUTED), 13))
        self.history_button.setCheckable(True)

        secondary_buttons_row = QHBoxLayout()
        secondary_buttons_row.setSpacing(8)
        secondary_buttons_row.addWidget(self.reset_button)
        secondary_buttons_row.addWidget(self.history_button)

        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.addWidget(self.run_button)
        buttons_layout.addLayout(secondary_buttons_row)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(18)
        left_layout.addWidget(self.model_selector)
        left_layout.addWidget(self.image_drop_area)
        left_layout.addLayout(buttons_layout)
        left_layout.addStretch()

        left_column = QWidget(self)
        left_column.setObjectName("leftColumn")
        left_column.setLayout(left_layout)
        left_column.setMaximumWidth(320)
        make_card(left_column)
        apply_card_shadow(left_column)

        self.result_panel = ResultPanel(self)
        self.result_panel.setObjectName("resultCard")
        make_card(self.result_panel)
        apply_card_shadow(self.result_panel)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        top_layout.addWidget(left_column)
        top_layout.addWidget(self.result_panel, stretch=1)

        self.compare_panel = ComparePanel(self)
        apply_card_shadow(self.compare_panel.content_frame)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(28, 24, 28, 28)
        main_layout.setSpacing(20)
        main_layout.addLayout(header_layout)
        main_layout.addLayout(top_layout, stretch=1)
        main_layout.addWidget(self.compare_panel)

        # Wrapped in a scroll area so expanding "Compare with all models"
        # (or any other future growth) never clips content when it needs
        # more vertical space than the current window height — it scrolls
        # instead. setWidgetResizable(True) still lets the content stretch
        # to fill the viewport (via top_layout's stretch factor above) when
        # everything already fits.
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

        self.history_panel = HistoryPanel(self)
        self.history_dock = QDockWidget("History", self)
        self.history_dock.setWidget(self.history_panel)
        self.history_dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.history_dock)
        self.history_dock.setVisible(False)
        self.history_dock.visibilityChanged.connect(self.history_button.setChecked)

    def _wire_signals(self) -> None:
        self.image_drop_area.imageLoaded.connect(self._on_image_loaded)
        self.image_drop_area.invalidFile.connect(self._show_warning)

        self.run_button.clicked.connect(self._on_run_clicked)
        self.reset_button.clicked.connect(self._on_reset_clicked)
        self.history_button.clicked.connect(self.history_dock.setVisible)

        self.result_panel.exportRequested.connect(self._on_export_requested)

        self.compare_panel.compareRequested.connect(self._on_compare_requested)

        self.history_panel.entrySelected.connect(self._on_history_selected)

        self.model_selector.modelChanged.connect(self._on_model_changed)

    def _start_health_monitor(self) -> None:
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._poll_health)
        self.health_timer.start(HEALTH_CHECK_INTERVAL_MS)
        self._poll_health()

    def _poll_health(self) -> None:
        for key, client in self.clients.items():
            worker = HealthCheckWorker(client)
            worker.signals.result.connect(self._on_health_result)
            self.thread_pool.start(worker)

    def _on_health_result(self, model_key: str, is_up: bool) -> None:
        self.model_selector.update_status(model_key, is_up)
        self._model_health[model_key] = is_up
        if model_key == self.model_selector.current_model_key():
            self._update_run_enabled()

    def _on_model_changed(self, model_key: str) -> None:
        self._update_run_enabled()

    def _update_run_enabled(self) -> None:
        model_key = self.model_selector.current_model_key()
        # Unknown health (no check has completed yet) doesn't block Run.
        is_healthy = self._model_health.get(model_key, True)
        self.run_button.setEnabled(self.state.image_bytes is not None and is_healthy)

    def _on_image_loaded(self, filename: str, image_bytes: bytes) -> None:
        self.state.image_filename = filename
        self.state.image_bytes = image_bytes
        self._update_run_enabled()

    def _on_run_clicked(self) -> None:
        if self.state.image_bytes is None:
            return

        model_key = self.model_selector.current_model_key()
        client = self.clients[model_key]
        model_label = MODELS[model_key]["label"]
        image_bytes = self.state.image_bytes

        self._run_generation += 1
        generation = self._run_generation

        self.run_button.setEnabled(False)
        self.result_panel.show_loading(model_label)

        worker = PredictWorker(client, image_bytes, self.state.image_filename)
        worker.signals.result.connect(
            lambda mk, result, density_map_bytes, gen=generation, img=image_bytes:
                self._on_predict_result(gen, mk, result, density_map_bytes, img)
        )
        worker.signals.error.connect(
            lambda mk, error, gen=generation: self._on_predict_error(gen, mk, error)
        )
        self.thread_pool.start(worker)

    def _on_predict_result(
        self,
        generation: int,
        model_key: str,
        result: PredictionResult,
        density_map_bytes: bytes,
        image_bytes: bytes,
    ) -> None:
        if generation != self._run_generation:
            return  # superseded by a Reset (or another run) before this came back

        model_label = MODELS[model_key]["label"]
        self.result_panel.show_result(model_label, result, density_map_bytes)

        self.state.last_result = result
        self.state.last_density_map_bytes = density_map_bytes
        self.state.last_model_label = model_label
        self.state.last_model_key = model_key
        # Identity, not equality — this is the exact bytes object this
        # request was launched with, so Compare can tell whether it still
        # matches self.state.image_bytes (i.e. no new image was loaded
        # since) before treating it as reusable.
        self.state.last_result_image_bytes = image_bytes

        self._add_history_entry(model_key, model_label, result, density_map_bytes)

        self._update_run_enabled()

    def _on_predict_error(self, generation: int, model_key: str, error: Exception) -> None:
        if generation != self._run_generation:
            return  # superseded by a Reset (or another run) before this came back

        # Clear any previously displayed result so a failed run can't leave a
        # stale count/image on screen (with Export still enabled) that no
        # longer corresponds to the current image.
        self.result_panel.reset()
        self.state.last_result = None
        self.state.last_density_map_bytes = None
        self.state.last_model_label = None
        self.state.last_model_key = None
        self.state.last_result_image_bytes = None

        self._update_run_enabled()
        self._show_error(error)

    def _add_history_entry(
        self, model_key: str, model_label: str, result: PredictionResult, density_map_bytes: bytes
    ) -> None:
        entry = HistoryEntry(
            timestamp=datetime.datetime.now(),
            model_key=model_key,
            model_label=model_label,
            density_map_bytes=density_map_bytes,
            result=result,
        )
        self.history_store.add(entry)
        self.history_panel.add_entry(entry)

    def _on_compare_requested(self) -> None:
        if self.state.image_bytes is None:
            self._show_warning("Load an image before comparing models.")
            return

        self._compare_generation += 1
        generation = self._compare_generation
        self._pending_compare = set(self.clients.keys())
        self.compare_panel.run_button.setEnabled(False)

        # If we already have a result for the currently selected model and it
        # was computed from this exact image, reuse it instead of re-sending
        # the same request — avoids a redundant HTTP round trip for a column
        # that would just duplicate what's already shown in the result panel
        # above.
        reusable_model_key = None
        if (
            self.state.last_result is not None
            and self.state.last_model_key is not None
            and self.state.last_result_image_bytes is self.state.image_bytes
        ):
            reusable_model_key = self.state.last_model_key

        for model_key, client in self.clients.items():
            if model_key == reusable_model_key:
                self.compare_panel.set_result(
                    model_key, self.state.last_result, self.state.last_density_map_bytes, reused=True
                )
                self._on_compare_job_done(model_key)
                continue

            self.compare_panel.set_loading(model_key)
            worker = PredictWorker(client, self.state.image_bytes, self.state.image_filename)
            worker.signals.result.connect(
                lambda mk, result, density_map_bytes, gen=generation:
                    self._on_compare_result(gen, mk, result, density_map_bytes)
            )
            worker.signals.error.connect(
                lambda mk, error, gen=generation: self._on_compare_error(gen, mk, error)
            )
            self.thread_pool.start(worker)

    def _on_compare_result(
        self, generation: int, model_key: str, result: PredictionResult, density_map_bytes: bytes
    ) -> None:
        if generation != self._compare_generation:
            return  # superseded by a Reset (or a newer comparison run)

        self.compare_panel.set_result(model_key, result, density_map_bytes)
        self._on_compare_job_done(model_key)

        model_label = MODELS[model_key]["label"]
        self._add_history_entry(model_key, model_label, result, density_map_bytes)

    def _on_compare_error(self, generation: int, model_key: str, error: Exception) -> None:
        if generation != self._compare_generation:
            return  # superseded by a Reset (or a newer comparison run)

        self.compare_panel.set_error(model_key, self._format_error(error))
        self._on_compare_job_done(model_key)

    def _on_compare_job_done(self, model_key: str) -> None:
        self._pending_compare.discard(model_key)
        if not self._pending_compare:
            self.compare_panel.run_button.setEnabled(True)

    def _on_export_requested(self) -> None:
        if self.state.last_result is None or self.state.last_density_map_bytes is None:
            return

        fmt, ok = QInputDialog.getItem(
            self, "Export format", "Choose export format:", ["json", "csv"], 0, False
        )
        if not ok:
            return

        dest_dir = QFileDialog.getExistingDirectory(self, "Choose export folder")
        if not dest_dir:
            return

        entry = HistoryEntry(
            timestamp=datetime.datetime.now(),
            model_key=self.state.last_model_key or self.model_selector.current_model_key(),
            model_label=self.state.last_model_label or "",
            density_map_bytes=self.state.last_density_map_bytes,
            result=self.state.last_result,
        )

        try:
            result_path = self.history_store.export(entry, dest_dir, fmt)
        except OSError as error:
            self._show_warning(f"Could not export: {error}")
            return

        QMessageBox.information(self, "Export complete", f"Saved to:\n{result_path.parent}")

    def _on_history_selected(self, entry: HistoryEntry) -> None:
        self.model_selector.set_model_key(entry.model_key)
        self.result_panel.show_result(entry.model_label, entry.result, entry.density_map_bytes)

        self.state.last_result = entry.result
        self.state.last_density_map_bytes = entry.density_map_bytes
        self.state.last_model_label = entry.model_label
        self.state.last_model_key = entry.model_key
        # History entries don't retain the original image bytes, so we can't
        # verify this result still matches the loaded image — never treat it
        # as reusable for Compare.
        self.state.last_result_image_bytes = None

    def _on_reset_clicked(self) -> None:
        # Invalidate any requests still in flight so their results/errors are
        # ignored when they arrive, instead of silently repopulating the UI
        # or history after the user has already reset.
        self._run_generation += 1
        self._compare_generation += 1
        self._pending_compare.clear()

        self.state = AppState()
        self.image_drop_area.reset()
        self.result_panel.reset()
        self.compare_panel.reset()
        self.compare_panel.run_button.setEnabled(True)
        self._update_run_enabled()

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Warning", message)

    def _show_error(self, error: Exception) -> None:
        QMessageBox.critical(self, "Error", self._format_error(error))

    @staticmethod
    def _format_error(error: Exception) -> str:
        if isinstance(error, ServiceUnavailableError):
            return str(error)
        if isinstance(error, ApiError):
            return f"Server error ({error.status_code}): {error.detail}"
        return str(error)
