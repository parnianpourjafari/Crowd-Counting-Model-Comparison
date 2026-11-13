from dataclasses import dataclass, field
from typing import Any


class ServiceUnavailableError(Exception):
    def __init__(self, model_key: str, model_label: str, port: int):
        self.model_key = model_key
        self.model_label = model_label
        self.port = port
        super().__init__(
            f"The {model_label} service is not reachable. "
            f"Make sure it's running on port {port}."
        )


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


@dataclass
class PredictionResult:
    model_key: str
    original_filename: str
    model: str
    model_weights: str
    training_dataset: str
    method: str
    task: str
    estimated_count: float
    rounded_count: int
    density_map_shape: list
    density_map_url: str
    inference_time_seconds: float
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, model_key: str, data: dict[str, Any]) -> "PredictionResult":
        return cls(
            model_key=model_key,
            original_filename=data["original_filename"],
            model=data["model"],
            model_weights=data["model_weights"],
            training_dataset=data["training_dataset"],
            method=data["method"],
            task=data["task"],
            estimated_count=data["estimated_count"],
            rounded_count=data["rounded_count"],
            density_map_shape=data["density_map_shape"],
            density_map_url=data["density_map_url"],
            inference_time_seconds=data["inference_time_seconds"],
            raw=data,
        )
