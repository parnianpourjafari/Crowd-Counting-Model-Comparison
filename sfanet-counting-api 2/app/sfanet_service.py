from pathlib import Path
from typing import Any
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import torch
from lwcc import LWCC

from app.config import (
    DENSITY_MAP_DIR,
    LWCC_MODEL_NAME,
    MODEL_DISPLAY_NAME,
    MODEL_METHOD,
    MODEL_TASK,
    MODEL_WEIGHTS,
    TRAINING_DATASET,
)

_MODEL: Any | None = None


def get_model() -> Any:
    """Load SFANet once and configure BatchNorm layers for inference."""
    global _MODEL

    if _MODEL is None:
        try:
            _MODEL = LWCC.load_model(
                model_name=LWCC_MODEL_NAME,
                model_weights=MODEL_WEIGHTS,
            )
            # Critical for SFANet because it contains BatchNorm layers.
            _MODEL.eval()
        except Exception as error:
            raise RuntimeError(
                f"Failed to load {MODEL_DISPLAY_NAME} "
                f"with {MODEL_WEIGHTS} weights: {error}"
            ) from error

    return _MODEL


def predict_count(image_path: str | Path) -> dict[str, Any]:
    """Run SFANet inference and save the density map at native resolution."""
    input_path = Path(image_path)

    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input image was not found: {input_path}")

    model = get_model()

    try:
        with torch.inference_mode():
            count, density = LWCC.get_count(
                str(input_path),
                model=model,
                return_density=True,
            )
    except Exception as error:
        raise RuntimeError(f"{MODEL_DISPLAY_NAME} inference failed: {error}") from error

    estimated_count = float(count)
    density_array = np.asarray(density)

    if not np.isfinite(estimated_count):
        raise RuntimeError("The model returned a non-finite crowd count.")

    if density_array.ndim != 2 or density_array.size == 0:
        raise RuntimeError(
            f"The model returned an invalid density map shape: {density_array.shape}"
        )

    if not np.isfinite(density_array).all():
        raise RuntimeError("The model returned a density map with non-finite values.")

    density_filename = f"sfanet_density_{uuid4().hex}.png"
    density_path = DENSITY_MAP_DIR / density_filename

    try:
        plt.imsave(density_path, density_array, cmap="jet")
    except Exception as error:
        raise RuntimeError(f"Failed to save the density map: {error}") from error

    return {
        "model": MODEL_DISPLAY_NAME,
        "model_weights": MODEL_WEIGHTS,
        "training_dataset": TRAINING_DATASET,
        "method": MODEL_METHOD,
        "task": MODEL_TASK,
        "estimated_count": estimated_count,
        "rounded_count": round(estimated_count),
        "density_map_shape": [
            int(density_array.shape[0]),
            int(density_array.shape[1]),
        ],
        "density_map_filename": density_filename,
    }
