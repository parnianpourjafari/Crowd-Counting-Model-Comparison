# DM-Count Crowd Counting API

A FastAPI service that integrates the pretrained **DM-Count** crowd-counting model through the **LWCC** library. The API accepts an image, estimates the number of people, and saves the predicted density map.

This project does not train or reimplement DM-Count from scratch. It provides a validated and reusable inference API around the pretrained model.

## Model information

- **Model:** DM-Count
- **Weights:** ShanghaiTech Part A (`SHA`)
- **Task:** Crowd counting
- **Method:** Density estimation + distribution matching
- **Input:** JPEG, PNG, BMP, WEBP, or TIFF image
- **Output:** Estimated count, rounded count, density-map shape, density-map URL, and inference time

DM-Count is not a general object-detection model. It does not return classes or bounding boxes.

## Project structure

```text
DMcount-counting-api/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── dmcount_service.py
│   └── main.py
├── outputs/
│   └── density_maps/
├── test_images/
│   └── test.jpg
├── tests/
│   ├── test_api.py
│   └── test_service.py
├── uploads/
├── .gitignore
├── requirements.txt
├── test_dmcount.py
└── README.md
```

The uploaded image is temporary and is deleted after every request. Generated density maps remain in `outputs/density_maps/`.

## Installation

```bash
cd DMcount-counting-api
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Windows, activate the environment with:

```bash
.venv\Scripts\activate
```

LWCC may download the pretrained weights on the first real inference. They are normally stored outside the project under:

```text
~/.lwcc/weights/DM-Count_SHA.pth
```

## Run a direct model test

```bash
python test_dmcount.py
```

The script runs the same service function used by the API and prints the result. It also saves the density map in `outputs/density_maps/`.

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

Returns the model name, weights, training dataset, method, task, input, and output description.

### `POST /predict`

Accepts an image as multipart form data. The maximum upload size is 10 MB.

Example response:

```json
{
  "original_filename": "crowd.jpg",
  "model": "DM-Count",
  "model_weights": "SHA",
  "training_dataset": "ShanghaiTech Part A (SHA)",
  "method": "Density Estimation + Distribution Matching",
  "task": "Crowd Counting",
  "estimated_count": 261.66513,
  "rounded_count": 262,
  "density_map_shape": [82, 124],
  "density_map_url": "/outputs/density_maps/dmcount_density_example.png",
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

Saving the density map directly preserves the density array's native height and width and avoids the extra canvas and margins created by `plt.savefig`.

## Tests

```bash
pytest -v
```

The automated tests verify:

- root endpoint behavior;
- rejection of fake image content;
- prediction response structure;
- cleanup of temporary uploads;
- preservation of the density map's native dimensions.

The API tests mock model inference, so they do not download weights. `test_dmcount.py` performs the real model inference.

## Known limitations

- The pretrained SHA weights are intended primarily for dense crowd scenes similar to ShanghaiTech Part A.
- A predicted count is not proof of accuracy unless it is compared with a manually verified ground-truth count.
- The first inference can be slower because the model must be loaded and the weights may need to be downloaded.
- Inference time depends on hardware, image size, preprocessing, and whether the model is already loaded.
