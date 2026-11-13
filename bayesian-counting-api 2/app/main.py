from io import BytesIO
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.bayesian_service import predict_count
from app.config import (
    ALLOWED_IMAGE_FORMATS,
    IMAGE_FORMAT_SUFFIXES,
    LWCC_MODEL_NAME,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    MODEL_DISPLAY_NAME,
    MODEL_METHOD,
    MODEL_TASK,
    MODEL_WEIGHTS,
    OUTPUT_DIR,
    TRAINING_DATASET,
    UPLOAD_DIR,
)

app = FastAPI(
    title="Bayesian Crowd Counting API",
    description=(
        "Upload an image and estimate the number of people "
        "using a pretrained Bayesian crowd-counting model."
    ),
    version="1.1.0",
)

app.mount(
    "/outputs",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="outputs",
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Bayesian Crowd Counting API is running.",
        "docs": "/docs",
    }


@app.get("/model-info")
def model_info() -> dict[str, str]:
    return {
        "model": MODEL_DISPLAY_NAME,
        "lwcc_model_name": LWCC_MODEL_NAME,
        "weights": MODEL_WEIGHTS,
        "training_dataset": TRAINING_DATASET,
        "method": MODEL_METHOD,
        "task": MODEL_TASK,
        "input": "Image",
        "output": "Estimated count and density map",
        "important_note": (
            "This is a crowd-counting model, not a general object-detection model."
        ),
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict:
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must be an image.",
        )

    original_filename = file.filename or "uploaded_image"
    temporary_path: Path | None = None

    try:
        contents = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded image is empty.",
            )

        if len(contents) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"The uploaded image must be at most {MAX_UPLOAD_SIZE_MB} MB.",
            )

        try:
            with Image.open(BytesIO(contents)) as image:
                image_format = image.format
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid image.",
            ) from error

        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported image format. "
                    "Use JPEG, PNG, BMP, WEBP, or TIFF."
                ),
            )

        suffix = IMAGE_FORMAT_SUFFIXES[image_format]
        temporary_path = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
        temporary_path.write_bytes(contents)

        started_at = perf_counter()
        result = await run_in_threadpool(predict_count, temporary_path)
        inference_time_seconds = perf_counter() - started_at

        return {
            "original_filename": original_filename,
            "model": result["model"],
            "model_weights": result["model_weights"],
            "training_dataset": result["training_dataset"],
            "method": result["method"],
            "task": result["task"],
            "estimated_count": result["estimated_count"],
            "rounded_count": result["rounded_count"],
            "density_map_shape": result["density_map_shape"],
            "density_map_url": (
                "/outputs/density_maps/"
                f"{result['density_map_filename']}"
            ),
            "inference_time_seconds": round(inference_time_seconds, 4),
        }

    except HTTPException:
        raise

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected prediction error: {error}",
        ) from error

    finally:
        await file.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
