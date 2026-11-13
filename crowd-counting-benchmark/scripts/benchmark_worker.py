from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from lwcc import LWCC
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one crowd-counting model on the shared benchmark images."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--service-module", required=True)
    parser.add_argument("--model-label", required=True)
    parser.add_argument("--ground-truth-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    return parser.parse_args()


def synchronize(device: torch.device) -> None:
    if device.type == "cuda" and torch.cuda.is_available():
        torch.cuda.synchronize(device)
    elif device.type == "mps" and hasattr(torch, "mps"):
        try:
            torch.mps.synchronize()
        except Exception:
            pass


def detect_device(model: Any) -> torch.device:
    try:
        return next(model.parameters()).device
    except (StopIteration, AttributeError):
        return torch.device("cpu")


def load_benchmark_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"No benchmark rows found in {csv_path}")

    required = {
        "image_name",
        "part",
        "category",
        "ground_truth_count",
        "selected_image_path",
    }
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(
            f"Missing columns in {csv_path.name}: {sorted(missing)}"
        )

    return rows


def run_inference(
    image_path: Path,
    model: Any,
    device: torch.device,
) -> tuple[float, np.ndarray, float]:
    synchronize(device)
    start = time.perf_counter()

    with torch.inference_mode():
        count, density = LWCC.get_count(
            str(image_path),
            model=model,
            return_density=True,
        )

    synchronize(device)
    elapsed = time.perf_counter() - start

    estimated_count = float(count)
    density_array = np.asarray(density)

    if not math.isfinite(estimated_count):
        raise RuntimeError("The model returned a non-finite count.")

    if density_array.ndim != 2 or density_array.size == 0:
        raise RuntimeError(
            f"Invalid density-map shape: {density_array.shape}"
        )

    if not np.isfinite(density_array).all():
        raise RuntimeError("The density map contains non-finite values.")

    return estimated_count, density_array, elapsed


def main() -> None:
    args = parse_args()

    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")

    project_root = args.project_root.expanduser().resolve()
    ground_truth_csv = args.ground_truth_csv.expanduser().resolve()
    output_json = args.output_json.expanduser().resolve()
    benchmark_root = ground_truth_csv.parent

    if not project_root.exists():
        raise FileNotFoundError(f"Project not found: {project_root}")

    sys.path.insert(0, str(project_root))

    service = importlib.import_module(args.service_module)
    config = importlib.import_module("app.config")

    print(f"\n[{args.model_label}] Loading model...", flush=True)
    load_start = time.perf_counter()
    model = service.get_model()
    model_load_seconds = time.perf_counter() - load_start

    device = detect_device(model)
    rows = load_benchmark_rows(ground_truth_csv)

    first_image = (
        benchmark_root / rows[0]["selected_image_path"]
    ).resolve()

    print(
        f"[{args.model_label}] Model loaded in "
        f"{model_load_seconds:.3f}s on {device}.",
        flush=True,
    )
    print(
        f"[{args.model_label}] Warm-up on {first_image.name}...",
        flush=True,
    )

    # One unmeasured warm-up pass avoids including initialization overhead
    # in the per-image timing measurements.
    run_inference(first_image, model, device)

    result_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        image_path = (
            benchmark_root / row["selected_image_path"]
        ).resolve()
        ground_truth = int(row["ground_truth_count"])

        print(
            f"[{args.model_label}] {index}/{len(rows)} "
            f"{image_path.name} (GT={ground_truth})",
            flush=True,
        )

        try:
            with Image.open(image_path) as image:
                width, height = image.size

            counts: list[float] = []
            times: list[float] = []
            density_shape: list[int] | None = None

            for repeat_index in range(1, args.repeats + 1):
                count, density, elapsed = run_inference(
                    image_path,
                    model,
                    device,
                )
                counts.append(count)
                times.append(elapsed)
                density_shape = [
                    int(density.shape[0]),
                    int(density.shape[1]),
                ]

                print(
                    f"    repeat {repeat_index}/{args.repeats}: "
                    f"count={count:.3f}, time={elapsed:.4f}s",
                    flush=True,
                )

            estimated_count = statistics.fmean(counts)
            signed_error = estimated_count - ground_truth
            absolute_error = abs(signed_error)
            percentage_error = (
                absolute_error / ground_truth * 100.0
                if ground_truth != 0
                else None
            )

            result_rows.append(
                {
                    "status": "ok",
                    "model": args.model_label,
                    "model_weights": getattr(
                        config, "MODEL_WEIGHTS", ""
                    ),
                    "training_dataset": getattr(
                        config, "TRAINING_DATASET", ""
                    ),
                    "image_name": row["image_name"],
                    "part": row["part"],
                    "category": row["category"],
                    "ground_truth_count": ground_truth,
                    "estimated_count": estimated_count,
                    "count_std": (
                        statistics.pstdev(counts)
                        if len(counts) > 1
                        else 0.0
                    ),
                    "rounded_count": round(estimated_count),
                    "signed_error": signed_error,
                    "absolute_error": absolute_error,
                    "squared_error": signed_error ** 2,
                    "percentage_error": percentage_error,
                    "average_inference_seconds": statistics.fmean(times),
                    "median_inference_seconds": statistics.median(times),
                    "min_inference_seconds": min(times),
                    "max_inference_seconds": max(times),
                    "inference_std_seconds": (
                        statistics.pstdev(times)
                        if len(times) > 1
                        else 0.0
                    ),
                    "repeats": args.repeats,
                    "image_width": width,
                    "image_height": height,
                    "image_pixels": width * height,
                    "density_map_height": density_shape[0]
                    if density_shape
                    else None,
                    "density_map_width": density_shape[1]
                    if density_shape
                    else None,
                    "device": str(device),
                    "selected_image_path": row[
                        "selected_image_path"
                    ],
                    "error": "",
                }
            )
        except Exception as error:
            print(
                f"    ERROR: {type(error).__name__}: {error}",
                flush=True,
            )
            result_rows.append(
                {
                    "status": "error",
                    "model": args.model_label,
                    "model_weights": getattr(
                        config, "MODEL_WEIGHTS", ""
                    ),
                    "training_dataset": getattr(
                        config, "TRAINING_DATASET", ""
                    ),
                    "image_name": row["image_name"],
                    "part": row["part"],
                    "category": row["category"],
                    "ground_truth_count": ground_truth,
                    "selected_image_path": row[
                        "selected_image_path"
                    ],
                    "device": str(device),
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    payload = {
        "model": args.model_label,
        "model_load_seconds": model_load_seconds,
        "device": str(device),
        "repeats": args.repeats,
        "rows": result_rows,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    successful = sum(
        1 for row in result_rows if row["status"] == "ok"
    )
    print(
        f"[{args.model_label}] Finished: "
        f"{successful}/{len(result_rows)} successful.",
        flush=True,
    )
    print(
        f"[{args.model_label}] Saved: {output_json}",
        flush=True,
    )


if __name__ == "__main__":
    main()
