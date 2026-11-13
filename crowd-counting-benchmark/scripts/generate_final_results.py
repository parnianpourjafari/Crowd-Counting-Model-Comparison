from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results_final"
CHARTS_DIR = RESULTS_DIR / "charts"

SUMMARY_MODEL_CSV = RESULTS_DIR / "summary_by_model.csv"
SUMMARY_PART_CSV = RESULTS_DIR / "summary_by_model_and_part.csv"
DETAIL_CSV = RESULTS_DIR / "benchmark_results.csv"
REPORT_PATH = RESULTS_DIR / "final_results_summary.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str | None) -> float:
    if value is None or value == "":
        return math.nan
    return float(value)


def save_bar_chart(
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    filename: str,
) -> None:
    plt.figure(figsize=(8, 5))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("Model")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / filename, dpi=220)
    plt.close()


def plot_grouped_part_mae(rows: list[dict[str, str]]) -> None:
    models = sorted({row["model"] for row in rows})
    parts = sorted({row["part"] for row in rows})

    values: dict[tuple[str, str], float] = {
        (row["model"], row["part"]): to_float(row["mae"])
        for row in rows
    }

    x = list(range(len(models)))
    group_width = 0.8
    bar_width = group_width / max(len(parts), 1)

    plt.figure(figsize=(9, 5.5))

    for part_index, part in enumerate(parts):
        positions = [
            position - group_width / 2 + bar_width / 2 + part_index * bar_width
            for position in x
        ]
        heights = [values[(model, part)] for model in models]
        plt.bar(positions, heights, width=bar_width, label=part)

    plt.xticks(x, models)
    plt.title("MAE by ShanghaiTech Part")
    plt.xlabel("Model")
    plt.ylabel("Mean Absolute Error")
    plt.legend(title="Dataset Part")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "04_mae_by_part.png", dpi=220)
    plt.close()


def plot_predictions(rows: list[dict[str, str]]) -> None:
    successful = [row for row in rows if row.get("status") == "ok"]
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)

    for row in successful:
        grouped[row["model"]].append(
            (
                to_float(row["ground_truth_count"]),
                to_float(row["estimated_count"]),
            )
        )

    all_ground_truth = [
        ground_truth
        for points in grouped.values()
        for ground_truth, _ in points
    ]

    if not all_ground_truth:
        return

    maximum = max(all_ground_truth)

    plt.figure(figsize=(7.5, 6))

    for model, points in sorted(grouped.items()):
        points = sorted(points, key=lambda item: item[0])
        ground_truth = [item[0] for item in points]
        predictions = [item[1] for item in points]
        plt.scatter(ground_truth, predictions, label=model, alpha=0.8)

    plt.plot([0, maximum], [0, maximum], linestyle="--", label="Perfect prediction")
    plt.title("Predicted Count vs Ground Truth")
    plt.xlabel("Ground-truth crowd count")
    plt.ylabel("Predicted crowd count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "05_predictions_vs_ground_truth.png", dpi=220)
    plt.close()


def plot_absolute_error_by_count(rows: list[dict[str, str]]) -> None:
    successful = [row for row in rows if row.get("status") == "ok"]
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)

    for row in successful:
        grouped[row["model"]].append(
            (
                to_float(row["ground_truth_count"]),
                to_float(row["absolute_error"]),
            )
        )

    plt.figure(figsize=(8, 5.5))

    for model, points in sorted(grouped.items()):
        points = sorted(points, key=lambda item: item[0])
        ground_truth = [item[0] for item in points]
        errors = [item[1] for item in points]
        plt.scatter(ground_truth, errors, label=model, alpha=0.8)

    plt.title("Absolute Error by Crowd Size")
    plt.xlabel("Ground-truth crowd count")
    plt.ylabel("Absolute error")
    plt.legend()
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "06_absolute_error_by_count.png", dpi=220)
    plt.close()


def best_row(rows: list[dict[str, str]], metric: str) -> dict[str, str]:
    return min(rows, key=lambda row: to_float(row[metric]))


def make_report(
    model_rows: list[dict[str, str]],
    part_rows: list[dict[str, str]],
) -> None:
    overall_accuracy = best_row(model_rows, "mae")
    overall_speed = best_row(model_rows, "average_inference_seconds")

    part_a_rows = [row for row in part_rows if row["part"] == "part_A"]
    part_b_rows = [row for row in part_rows if row["part"] == "part_B"]

    best_part_a = best_row(part_a_rows, "mae")
    best_part_b = best_row(part_b_rows, "mae")

    lines = [
        "# Final Crowd-Counting Benchmark Summary",
        "",
        "## Experimental setup",
        "",
        "- 50 ShanghaiTech test images were evaluated.",
        "- 25 images were selected from Part A and 25 from Part B.",
        "- Each image was run three times per model for timing.",
        "- Model loading and one warm-up inference were excluded from inference timing.",
        "- MAE and RMSE are the primary accuracy metrics.",
        "",
        "## Main findings",
        "",
        (
            f"- **Best overall accuracy:** {overall_accuracy['model']} "
            f"(MAE {to_float(overall_accuracy['mae']):.2f}, "
            f"RMSE {to_float(overall_accuracy['rmse']):.2f})."
        ),
        (
            f"- **Fastest average inference:** {overall_speed['model']} "
            f"({to_float(overall_speed['average_inference_seconds']):.4f} seconds/image)."
        ),
        (
            f"- **Best on dense Part A images:** {best_part_a['model']} "
            f"(MAE {to_float(best_part_a['mae']):.2f})."
        ),
        (
            f"- **Best on Part B street scenes:** {best_part_b['model']} "
            f"(MAE {to_float(best_part_b['mae']):.2f})."
        ),
        "",
        "## Overall results",
        "",
        "| Model | MAE | RMSE | MAPE (%) | Avg inference (s) |",
        "|---|---:|---:|---:|---:|",
    ]

    for row in sorted(model_rows, key=lambda item: to_float(item["mae"])):
        lines.append(
            f"| {row['model']} "
            f"| {to_float(row['mae']):.2f} "
            f"| {to_float(row['rmse']):.2f} "
            f"| {to_float(row['mape_percent']):.2f} "
            f"| {to_float(row['average_inference_seconds']):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The Bayesian model provides the strongest overall accuracy and performs "
                "best on the dense ShanghaiTech Part A subset. SFANet performs best on "
                "Part B, indicating stronger suitability for lower-density street scenes "
                "and perspective variation. CSRNet provides the fastest average inference, "
                "while DM-Count offers a competitive balance between accuracy and speed."
            ),
            "",
            "## Important limitation",
            "",
            (
                "CSRNet, Bayesian, and DM-Count use SHA weights, whereas SFANet uses SHB "
                "weights. Therefore, the experiment compares both model architecture and "
                "training-domain effects. The results support selecting a model for a "
                "specific image domain, but they are not a perfectly controlled comparison "
                "of architecture alone."
            ),
            "",
            "## Generated charts",
            "",
            "- `charts/01_overall_mae.png`",
            "- `charts/02_overall_rmse.png`",
            "- `charts/03_average_inference_time.png`",
            "- `charts/04_mae_by_part.png`",
            "- `charts/05_predictions_vs_ground_truth.png`",
            "- `charts/06_absolute_error_by_count.png`",
            "",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    model_rows = read_csv(SUMMARY_MODEL_CSV)
    part_rows = read_csv(SUMMARY_PART_CSV)
    detail_rows = read_csv(DETAIL_CSV)

    # Keep the CSV order for the overall plots.
    labels = [row["model"] for row in model_rows]

    save_bar_chart(
        labels,
        [to_float(row["mae"]) for row in model_rows],
        "Overall Mean Absolute Error",
        "MAE (lower is better)",
        "01_overall_mae.png",
    )

    save_bar_chart(
        labels,
        [to_float(row["rmse"]) for row in model_rows],
        "Overall Root Mean Squared Error",
        "RMSE (lower is better)",
        "02_overall_rmse.png",
    )

    save_bar_chart(
        labels,
        [to_float(row["average_inference_seconds"]) for row in model_rows],
        "Average Inference Time per Image",
        "Seconds (lower is better)",
        "03_average_inference_time.png",
    )

    plot_grouped_part_mae(part_rows)
    plot_predictions(detail_rows)
    plot_absolute_error_by_count(detail_rows)
    make_report(model_rows, part_rows)

    print(f"Charts created in: {CHARTS_DIR}")
    print(f"Summary report created: {REPORT_PATH}")


if __name__ == "__main__":
    main()
