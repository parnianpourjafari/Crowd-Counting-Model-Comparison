from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.io import loadmat


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "datasets" / "ShanghaiTech"

PARTS = {
    "part_A": {
        "test_dir": DATASET_ROOT / "part_A_final" / "test_data",
        "category": "dense",
    },
    "part_B": {
        "test_dir": DATASET_ROOT / "part_B_final" / "test_data",
        "category": "sparse_perspective",
    },
}

SELECTED_IMAGES_ROOT = ROOT / "selected_images"
SELECTED_GT_ROOT = ROOT / "selected_ground_truth"
CSV_PATH = ROOT / "ground_truth.csv"

SAMPLES_PER_PART = 5
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def walk_values(value: Any) -> Iterable[Any]:
    """Recursively walk dictionaries, MATLAB structs, cells, arrays and sequences."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not str(key).startswith("__"):
                yield from walk_values(item)
        return

    if isinstance(value, np.void):
        if value.dtype.names:
            for field_name in value.dtype.names:
                yield from walk_values(value[field_name])
        return

    if isinstance(value, np.ndarray):
        # MATLAB struct arrays
        if value.dtype.names:
            for field_name in value.dtype.names:
                yield from walk_values(value[field_name])
            return

        # MATLAB cells / Python objects
        if value.dtype == object:
            for item in value.flat:
                yield from walk_values(item)
            return

        # Numeric array
        if np.issubdtype(value.dtype, np.number):
            yield value
        return

    if isinstance(value, (list, tuple)):
        for item in value:
            yield from walk_values(item)


def count_from_numeric_array(array: np.ndarray) -> int | None:
    """Return a head count when the array looks like N×2 point coordinates."""
    array = np.asarray(array)

    # Remove singleton dimensions but retain coordinate structure.
    array = np.squeeze(array)

    if array.size == 0:
        return 0

    # One point may become shape (2,) after squeezing.
    if array.ndim == 1 and array.shape[0] == 2:
        return 1

    if array.ndim != 2:
        return None

    if array.shape[1] == 2:
        return int(array.shape[0])

    if array.shape[0] == 2:
        return int(array.shape[1])

    return None


def extract_count(mat_path: Path) -> int:
    """
    Extract the number of annotated heads from ShanghaiTech ground truth.

    simplify_cells=True converts many nested MATLAB cell/struct combinations
    into simpler Python objects. The recursive fallback supports older SciPy
    representations too.
    """
    try:
        data = loadmat(mat_path, simplify_cells=True)
    except TypeError:
        # Compatibility fallback for older SciPy versions.
        data = loadmat(mat_path)

    candidates: list[int] = []

    # Prefer known ShanghaiTech keys when available.
    preferred_values: list[Any] = []
    for key in ("image_info", "annPoints", "location"):
        if key in data:
            preferred_values.append(data[key])

    values_to_scan = preferred_values if preferred_values else [data]

    for root_value in values_to_scan:
        for value in walk_values(root_value):
            if not isinstance(value, np.ndarray):
                continue

            count = count_from_numeric_array(value)
            if count is not None:
                candidates.append(count)

    # If preferred-key scanning found nothing, scan the complete file.
    if not candidates:
        for value in walk_values(data):
            if not isinstance(value, np.ndarray):
                continue

            count = count_from_numeric_array(value)
            if count is not None:
                candidates.append(count)

    if not candidates:
        visible_keys = [key for key in data.keys() if not key.startswith("__")]
        raise ValueError(
            "Could not extract annotation points from "
            f"{mat_path}. MATLAB keys found: {visible_keys}"
        )

    # The coordinate array is normally the largest N×2 numeric array.
    return max(candidates)


def find_ground_truth(image_path: Path, ground_truth_dir: Path) -> Path:
    candidates = [
        ground_truth_dir / f"GT_{image_path.stem}.mat",
        ground_truth_dir / f"{image_path.stem}.mat",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    matches = list(ground_truth_dir.glob(f"*{image_path.stem}*.mat"))
    if len(matches) == 1:
        return matches[0]

    raise FileNotFoundError(
        f"No unique ground-truth file found for {image_path.name}"
    )


def choose_evenly_across_count_range(
    records: list[dict[str, object]],
    sample_count: int,
) -> list[dict[str, object]]:
    """Choose deterministic examples across the complete count range."""
    records = sorted(records, key=lambda row: int(row["ground_truth_count"]))

    if len(records) <= sample_count:
        return records

    indices = np.rint(
        np.linspace(0, len(records) - 1, sample_count)
    ).astype(int)

    return [records[int(index)] for index in indices]


def collect_part_records(
    part_name: str,
    test_dir: Path,
    category: str,
) -> list[dict[str, object]]:
    images_dir = test_dir / "images"
    ground_truth_dir = test_dir / "ground_truth"

    if not images_dir.exists():
        raise FileNotFoundError(f"Missing images directory: {images_dir}")

    if not ground_truth_dir.exists():
        raise FileNotFoundError(
            f"Missing ground-truth directory: {ground_truth_dir}"
        )

    image_paths = sorted(
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_paths:
        raise FileNotFoundError(f"No images found in: {images_dir}")

    records: list[dict[str, object]] = []

    for image_path in image_paths:
        gt_path = find_ground_truth(image_path, ground_truth_dir)
        count = extract_count(gt_path)

        records.append(
            {
                "part": part_name,
                "category": category,
                "image_path": image_path,
                "ground_truth_path": gt_path,
                "ground_truth_count": count,
            }
        )

    return records


def clear_previous_selection(directory: Path) -> None:
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)


def main() -> None:
    clear_previous_selection(SELECTED_IMAGES_ROOT)
    clear_previous_selection(SELECTED_GT_ROOT)

    selected_rows: list[dict[str, object]] = []

    for part_name, config in PARTS.items():
        test_dir = Path(config["test_dir"])
        category = str(config["category"])

        print(f"\nReading {part_name} ground truth...")

        all_records = collect_part_records(
            part_name,
            test_dir,
            category,
        )

        selected = choose_evenly_across_count_range(
            all_records,
            SAMPLES_PER_PART,
        )

        image_output_dir = SELECTED_IMAGES_ROOT / part_name
        gt_output_dir = SELECTED_GT_ROOT / part_name
        image_output_dir.mkdir(parents=True, exist_ok=True)
        gt_output_dir.mkdir(parents=True, exist_ok=True)

        print(f"{part_name}: selected {len(selected)} images")

        for record in selected:
            source_image = Path(record["image_path"])
            source_gt = Path(record["ground_truth_path"])

            selected_image = image_output_dir / source_image.name
            selected_gt = gt_output_dir / source_gt.name

            shutil.copy2(source_image, selected_image)
            shutil.copy2(source_gt, selected_gt)

            count = int(record["ground_truth_count"])

            selected_rows.append(
                {
                    "image_name": source_image.name,
                    "part": part_name,
                    "category": record["category"],
                    "ground_truth_count": count,
                    "original_image_path": str(
                        source_image.relative_to(ROOT)
                    ),
                    "selected_image_path": str(
                        selected_image.relative_to(ROOT)
                    ),
                    "selected_ground_truth_path": str(
                        selected_gt.relative_to(ROOT)
                    ),
                }
            )

            print(f"  {source_image.name}: {count} people")

    with CSV_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = [
            "image_name",
            "part",
            "category",
            "ground_truth_count",
            "original_image_path",
            "selected_image_path",
            "selected_ground_truth_path",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_rows)

    print(f"\nSaved CSV: {CSV_PATH}")
    print(f"Selected images: {SELECTED_IMAGES_ROOT}")
    print(f"Selected annotations: {SELECTED_GT_ROOT}")


if __name__ == "__main__":
    main()
