# CSRNet Crowd Counting API

This project integrates the pretrained **CSRNet** crowd-counting model through the Lightweight Crowd Counting (`lwcc`) library and exposes it through a local FastAPI service.

The API accepts an image and returns an estimated crowd count, a rounded count, the native density-map dimensions, a density-map URL, and the measured inference time.

## Model configuration

- Display name: `CSRNet`
- LWCC model name: `CSRNet`
- Weights: `SHA`
- Training dataset: ShanghaiTech Part A
- Method: Density Estimation
- Task: Crowd Counting

CSRNet is a density-estimation model. It does not return bounding boxes or individual object detections.

## Project structure

```text
csrnet-counting-api/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── csrnet_service.py
│   └── main.py
├── outputs/
│   └── density_maps/
│       └── .gitkeep
├── scripts/
│   └── fix_lwcc_path.py
├── test_images/
│   └── test.jpg
├── tests/
│   ├── test_api.py
│   └── test_service.py
├── uploads/
│   └── .gitkeep
├── .gitignore
├── requirements.txt
├── test_csrnet.py
└── README.md
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On macOS, fix the incorrect LWCC weights path before the first real inference:

```bash
python scripts/fix_lwcc_path.py
```

## Tests

Run the structural and API tests:

```bash
pytest -v
```

Run the actual pretrained model:

```bash
python test_csrnet.py
```

The expected weight file is stored at:

```text
~/.lwcc/weights/CSRNet_SHA.pth
```

LWCC downloads it on first use if it is not already present.

## Run the API

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Use `POST /predict` to upload an image.

## Example response

```json
{
  "original_filename": "crowd.jpg",
  "model": "CSRNet",
  "model_weights": "SHA",
  "training_dataset": "ShanghaiTech Part A (SHA)",
  "method": "Density Estimation",
  "task": "Crowd Counting",
  "estimated_count": 220.0787,
  "rounded_count": 220,
  "density_map_shape": [83, 125],
  "density_map_url": "/outputs/density_maps/csrnet_density_example.png",
  "inference_time_seconds": 1.2345
}
```

## Important implementation details

- The model is loaded only once and reused between requests.
- `model.eval()` is called before inference.
- Inference runs inside `torch.inference_mode()`.
- FastAPI runs model inference in a thread pool.
- Uploaded files are validated using Pillow and removed after each request.
- Density maps are saved directly at their native array dimensions.
- The API accepts JPEG, PNG, BMP, WEBP, and TIFF images up to 10 MB.

## Attribution and limitation

This project serves a pretrained model supplied through LWCC. It does not train or reimplement CSRNet from scratch.

A successful inference confirms that the API and pretrained model run correctly. Measuring model accuracy requires images with known ground-truth crowd counts.
