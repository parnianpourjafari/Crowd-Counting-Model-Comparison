import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from models import PredictionResult


@dataclass
class HistoryEntry:
    timestamp: datetime
    model_key: str
    model_label: str
    density_map_bytes: bytes
    result: PredictionResult

    def label(self) -> str:
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"{time_str} — {self.model_label} — count={self.result.rounded_count}"


class HistoryStore:
    def __init__(self):
        self._entries: list[HistoryEntry] = []

    def add(self, entry: HistoryEntry) -> None:
        self._entries.append(entry)

    def all(self) -> list[HistoryEntry]:
        return list(self._entries)

    def export(self, entry: HistoryEntry, dest_dir: str, fmt: str) -> Path:
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        stamp = entry.timestamp.strftime("%Y%m%d_%H%M%S_%f")
        base_name = f"{entry.model_key}_{stamp}"

        density_map_path = dest_path / f"{base_name}_density_map.png"
        density_map_path.write_bytes(entry.density_map_bytes)

        # entry fields are listed last so they always win over any same-named
        # keys the service's raw response happens to contain.
        result_dict = {
            **entry.result.raw,
            "timestamp": entry.timestamp.isoformat(),
            "model_key": entry.model_key,
            "model_label": entry.model_label,
        }

        if fmt == "json":
            result_path = dest_path / f"{base_name}.json"
            result_path.write_text(json.dumps(result_dict, indent=2), encoding="utf-8")
        elif fmt == "csv":
            result_path = dest_path / f"{base_name}.csv"
            with result_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(result_dict.keys())
                writer.writerow(result_dict.values())
        else:
            raise ValueError(f"Unsupported export format: {fmt}")

        return result_path
