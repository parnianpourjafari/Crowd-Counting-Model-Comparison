from PyQt5.QtCore import QObject, QRunnable, pyqtSignal

from api_client import ApiClient
from models import PredictionResult


class PredictWorkerSignals(QObject):
    started = pyqtSignal(str)
    result = pyqtSignal(str, PredictionResult, bytes)
    error = pyqtSignal(str, Exception)


class PredictWorker(QRunnable):
    def __init__(self, client: ApiClient, image_bytes: bytes, filename: str):
        super().__init__()
        self.client = client
        self.image_bytes = image_bytes
        self.filename = filename
        self.signals = PredictWorkerSignals()

    def run(self) -> None:
        self.signals.started.emit(self.client.model_key)
        try:
            prediction = self.client.predict(self.image_bytes, self.filename)
            density_map_bytes = self.client.fetch_density_map(prediction.density_map_url)
        except Exception as error:  # noqa: BLE001 - surfaced to UI via signal
            self.signals.error.emit(self.client.model_key, error)
            return
        self.signals.result.emit(self.client.model_key, prediction, density_map_bytes)


class HealthCheckWorkerSignals(QObject):
    result = pyqtSignal(str, bool)


class HealthCheckWorker(QRunnable):
    def __init__(self, client: ApiClient):
        super().__init__()
        self.client = client
        self.signals = HealthCheckWorkerSignals()

    def run(self) -> None:
        is_up = self.client.check_health()
        self.signals.result.emit(self.client.model_key, is_up)
