# Bayesian Crowd Counting API

A FastAPI service that integrates a pretrained **Bayesian Crowd Counting** model through the **LWCC** library. The API accepts an image, estimates the number of people, and saves the predicted density map.

This project does not train or reimplement the Bayesian model from scratch. It provides a validated and reusable inference API around the pretrained model.

## Model information

- **Display name:** Bayesian Crowd Counting
- **LWCC model name:** `Bay`
- **Weights:** ShanghaiTech Part A (`SHA`)
- **Task:** Crowd counting
- **Method:** Density estimation; the pretrained model was trained using Bayesian Loss
- **Input:** JPEG, PNG, BMP, WEBP, or TIFF image
- **Output:** Estimated count, rounded count, density-map shape, density-map URL, and inference time

The model is not a general object-detection model. It does not return classes or bounding boxes.

## Project structure

```text
bayesian-counting-api/
├── app/
│   ├── __init__.py
│   ├── bayesian_service.py
│   ├── config.py
│   └── main.py
├── outputs/
│   └── density_maps/
├── scripts/
│   └── fix_lwcc_path.py
├── test_images/
│   └── test.jpg
├── tests/
│   ├── test_api.py
│   └── test_service.py
├── uploads/
├── .gitignore
├── requirements.txt
├── test_bayesian.py
└── README.md
```

The uploaded image is temporary and is deleted after every request. Generated density maps remain in `outputs/density_maps/`.

## Installation

```bash
cd bayesian-counting-api
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Windows, activate the environment with:

```bash
.venv\Scripts\activate
```

## LWCC path fix on macOS

Some installations of LWCC 0.0.7 incorrectly try to use the read-only path `/.lwcc/weights`. After installing the requirements, run:

```bash
python scripts/fix_lwcc_path.py
```

The corrected weight location is:

```text
~/.lwcc/weights/Bay_SHA.pth
```

If the installed LWCC version is already correct, the script makes no changes.

## Run automated tests

```bash
pytest -v
```

The API tests mock model inference, so they do not download weights.

## Run a direct model test

```bash
python test_bayesian.py
```

The script runs the same service function used by the API and saves the density map in `outputs/density_maps/`.

## Run the API

```bash
uvicorn app.main:app --reload
```

Interactive documentation:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

### `GET /`

Checks whether the API is running.

### `GET /model-info`

Returns the model display name, LWCC model name, weights, training dataset, method, task, input, and output description.

### `POST /predict`

Accepts an image as multipart form data. The maximum upload size is 10 MB.

Example response:

```json
{
  "original_filename": "crowd.jpg",
  "model": "Bayesian Crowd Counting",
  "model_weights": "SHA",
  "training_dataset": "ShanghaiTech Part A (SHA)",
  "method": "Density Estimation + Bayesian Loss Training",
  "task": "Crowd Counting",
  "estimated_count": 250.3823,
  "rounded_count": 250,
  "density_map_shape": [82, 124],
  "density_map_url": "/outputs/density_maps/bayesian_density_example.png",
  "inference_time_seconds": 1.2345
}
```

The values above are examples. Accuracy cannot be established without a ground-truth count for the input image.

## Validation and inference behavior

The API:

1. checks that the MIME type represents an image;
2. enforces the 10 MB size limit;
3. verifies the actual file content with Pillow;
4. saves the upload under a generated temporary filename;
5. runs model inference in a worker thread;
6. loads and reuses one pretrained model instance;
7. explicitly places the model in evaluation mode;
8. runs inference with gradients disabled;
9. saves the density array directly with `plt.imsave`;
10. deletes the temporary upload in a `finally` block.

Saving the density map directly preserves the density array's native height and width.

## Known limitations

- The SHA weights are intended primarily for dense crowd scenes similar to ShanghaiTech Part A.
- Bayesian Loss describes the model's training method; it is not recalculated by the API during inference.
- A predicted count is not proof of accuracy unless it is compared with a manually verified ground-truth count.
- The first inference can be slower because the model must be loaded and the weights may need to be downloaded.
- Inference time depends on hardware, image size, preprocessing, and whether the model is already loaded.
