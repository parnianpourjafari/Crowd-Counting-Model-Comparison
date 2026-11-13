from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACHELOR_ROOT = ROOT.parent
RESULTS_DIR = ROOT / "results_final"
WORKER_PATH = ROOT / "scripts" / "benchmark_worker.py"
GROUND_TRUTH_CSV = ROOT / "ground_truth_final.csv"

MODELS = [
    {
        "label": "CSRNet",
        "slug": "csrnet",
        "project_dir": "csrnet-counting-api 2",
        "service_module": "app.csrnet_service",
    },
    {
        "label": "Bayesian",
        "slug": "bayesian",
        "project_dir": "bayesian-counting-api 2",
        "service_module": "app.bayesian_service",
    },
    {
        "label": "DM-Count",
        "slug": "dmcount",
        "project_dir": "DMcount-counting-api 2",
        "service_module": "app.dmcount_service",
    },
    {
        "label": "SFANet",
        "slug": "sfanet",
        "project_dir": "sfanet-counting-api 2",
        "service_module": "app.sfanet_service",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the final 50-image crowd-counting benchmark."
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Timed inference runs per image (default: 3).",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        choices=[model["slug"] for model in MODELS],
        help="Optionally benchmark only selected models.",
    )
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def mean_or_none(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def build_summary(
    rows: list[dict[str, Any]],
    group_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        if row.get("status") != "ok":
            continue

        key = tuple(row[field] for field in group_fields)
        grouped[key].append(row)

    summary_rows: list[dict[str, Any]] = []

    for key, group in sorted(grouped.items()):
        absolute_errors = [
            float(row["absolute_error"]) for row in group
        ]
        squared_errors = [
            float(row["squared_error"]) for row in group
        ]
        percentage_errors = [
            float(row["percentage_error"])
            for row in group
            if row.get("percentage_error") is not None
        ]
        inference_times = [
            float(row["average_inference_seconds"])
            for row in group
        ]

        summary: dict[str, Any] = {
            field: value
            for field, value in zip(group_fields, key)
        }
        summary.update(
            {
                "images": len(group),
                "mae": statistics.fmean(absolute_errors),
                "rmse": math.sqrt(statistics.fmean(squared_errors)),
                "mape_percent": mean_or_none(percentage_errors),
                "average_inference_seconds": statistics.fmean(
                    inference_times
                ),
                "median_image_inference_seconds": statistics.median(
                    inference_times
                ),
                "min_image_inference_seconds": min(inference_times),
                "max_image_inference_seconds": max(inference_times),
            }
        )
        summary_rows.append(summary)

    return summary_rows


def print_table(
    title: str,
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> None:
    print(f"\n{title}")
    print("=" * len(title))

    if not rows:
        print("No successful results.")
        return

    headers = [header for _, header in columns]
    formatted: list[list[str]] = []

    for row in rows:
        rendered: list[str] = []

        for key, _ in columns:
            value = row.get(key, "")

            if isinstance(value, float):
                rendered.append(f"{value:.4f}")
            elif value is None:
                rendered.append("")
            else:
                rendered.append(str(value))

        formatted.append(rendered)

    widths = [
        max(
            len(headers[index]),
            max(len(row[index]) for row in formatted),
        )
        for index in range(len(headers))
    ]

    print(
        " | ".join(
            headers[index].ljust(widths[index])
            for index in range(len(headers))
        )
    )
    print("-+-".join("-" * width for width in widths))

    for row in formatted:
        print(
            " | ".join(
                row[index].ljust(widths[index])
                for index in range(len(widths))
            )
        )


def main() -> None:
    args = parse_args()

    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")

    if not GROUND_TRUTH_CSV.exists():
        raise FileNotFoundError(
            f"Missing final ground-truth CSV: {GROUND_TRUTH_CSV}"
        )

    if not WORKER_PATH.exists():
        raise FileNotFoundError(
            f"Missing benchmark worker: {WORKER_PATH}"
        )

    selected_models = [
        model
        for model in MODELS
        if not args.only or model["slug"] in args.only
    ]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_payloads: list[dict[str, Any]] = []
    combined_rows: list[dict[str, Any]] = []

    for model in selected_models:
        project_root = (
            BACHELOR_ROOT / model["project_dir"]
        ).resolve()
        python_path = project_root / ".venv" / "bin" / "python"
        output_json = RESULTS_DIR / f"raw_{model['slug']}.json"

        if not project_root.exists():
            raise FileNotFoundError(
                f"Project folder not found: {project_root}"
            )

        if not python_path.exists():
            raise FileNotFoundError(
                f"Virtual-environment Python not found: {python_path}"
            )

        command = [
            str(python_path),
            str(WORKER_PATH),
            "--project-root",
            str(project_root),
            "--service-module",
            model["service_module"],
            "--model-label",
            model["label"],
            "--ground-truth-csv",
            str(GROUND_TRUTH_CSV),
            "--output-json",
            str(output_json),
            "--repeats",
            str(args.repeats),
        ]

        print(
            f"\nStarting {model['label']} FINAL benchmark "
            f"with {args.repeats} repeats per image..."
        )

        completed = subprocess.run(
            command,
            cwd=project_root,
            check=False,
        )

        if completed.returncode != 0:
            print(
                f"{model['label']} worker failed with exit code "
                f"{completed.returncode}. Continuing."
            )
            continue

        payload = json.loads(
            output_json.read_text(encoding="utf-8")
        )
        raw_payloads.append(payload)

        model_load_seconds = payload.get("model_load_seconds")

        for row in payload.get("rows", []):
            row["model_load_seconds"] = model_load_seconds
            combined_rows.append(row)

    if not combined_rows:
        raise RuntimeError("No model produced benchmark results.")

    write_csv(
        RESULTS_DIR / "benchmark_results.csv",
        combined_rows,
    )

    model_summary = build_summary(combined_rows, ("model",))
    model_summary.sort(key=lambda row: float(row["mae"]))
    write_csv(
        RESULTS_DIR / "summary_by_model.csv",
        model_summary,
    )

    part_summary = build_summary(
        combined_rows,
        ("model", "part"),
    )
    write_csv(
        RESULTS_DIR / "summary_by_model_and_part.csv",
        part_summary,
    )

    category_summary = build_summary(
        combined_rows,
        ("model", "category"),
    )
    write_csv(
        RESULTS_DIR / "summary_by_model_and_category.csv",
        category_summary,
    )

    failed_rows = [
        row
        for row in combined_rows
        if row.get("status") != "ok"
    ]
    write_csv(
        RESULTS_DIR / "failed_runs.csv",
        failed_rows,
    )

    metadata = {
        "benchmark_type": "final_shanghaitech_50_images",
        "repeats_per_image": args.repeats,
        "models_requested": [
            model["label"] for model in selected_models
        ],
        "models_completed": [
            payload["model"] for payload in raw_payloads
        ],
        "total_rows": len(combined_rows),
        "successful_rows": sum(
            1
            for row in combined_rows
            if row.get("status") == "ok"
        ),
        "failed_rows": len(failed_rows),
    }
    (
        RESULTS_DIR / "benchmark_metadata.json"
    ).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print_table(
        "FINAL overall model comparison",
        model_summary,
        [
            ("model", "Model"),
            ("images", "Images"),
            ("mae", "MAE"),
            ("rmse", "RMSE"),
            ("mape_percent", "MAPE %"),
            ("average_inference_seconds", "Avg seconds"),
        ],
    )

    print_table(
        "FINAL comparison by ShanghaiTech part",
        part_summary,
        [
            ("model", "Model"),
            ("part", "Part"),
            ("images", "Images"),
            ("mae", "MAE"),
            ("rmse", "RMSE"),
            ("mape_percent", "MAPE %"),
            ("average_inference_seconds", "Avg seconds"),
        ],
    )

    print(
        f"\nSaved detailed final results: "
        f"{RESULTS_DIR / 'benchmark_results.csv'}"
    )
    print(f"Final results folder: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
