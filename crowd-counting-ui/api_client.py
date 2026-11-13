import mimetypes
from urllib.parse import urljoin

import requests

from config import HEALTH_CHECK_TIMEOUT_SECONDS, PREDICT_TIMEOUT_SECONDS
from models import ApiError, PredictionResult, ServiceUnavailableError


def is_service_up(base_url: str, timeout: float) -> bool:
    try:
        response = requests.get(base_url + "/", timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


class ApiClient:
    def __init__(self, model_key: str, model_label: str, base_url: str, port: int):
        self.model_key = model_key
        self.model_label = model_label
        self.base_url = base_url
        self.port = port

    def check_health(self) -> bool:
        return is_service_up(self.base_url, HEALTH_CHECK_TIMEOUT_SECONDS)

    def predict(self, image_bytes: bytes, filename: str) -> PredictionResult:
        content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
        try:
            response = requests.post(
                self.base_url + "/predict",
                files={"file": (filename, image_bytes, content_type)},
                timeout=PREDICT_TIMEOUT_SECONDS,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
            raise ServiceUnavailableError(self.model_key, self.model_label, self.port) from error

        self._raise_for_status(response)
        return PredictionResult.from_json(self.model_key, response.json())

    def fetch_density_map(self, density_map_url: str) -> bytes:
        full_url = urljoin(self.base_url, density_map_url)
        try:
            response = requests.get(full_url, timeout=PREDICT_TIMEOUT_SECONDS)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
            raise ServiceUnavailableError(self.model_key, self.model_label, self.port) from error

        self._raise_for_status(response)
        return response.content

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ApiError(response.status_code, detail)
