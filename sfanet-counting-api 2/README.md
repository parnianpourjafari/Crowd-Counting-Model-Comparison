# SFANet Crowd Counting API

This project integrates a pretrained SFANet crowd-counting model through the Lightweight Crowd Counting (LWCC) library and exposes it through FastAPI.

The API receives an image, estimates the crowd count, creates a density map, and returns a consistent JSON response suitable for comparison with the CSRNet, DM-Count, and Bayesian projects.

## Model

- **Model:** SFANet
- **LWCC model name:** `SFANet`
- **Weights:** `SHB`
- **Training dataset:** ShanghaiTech Part B
- **Method:** Density Estimation + Multi-Scale Fusion + Attention
- **Task:** Crowd Counting

SFANet is a density-estimation model. It does not return person bounding boxes or object classes.

ShanghaiTech Part B generally contains less-dense street scenes than ShanghaiTech Part A. Therefore, the available SFANet-SHB weights should not be compared with SHA-based models as though all models had identical training data.

## Important inference correction

SFANet contains Batch Normalization layers. The project explicitly loads the model once and calls:

```python
model.eval()
```

It also performs inference within:

```python
with torch.inference_mode():
```

This prevents BatchNorm from using statistics from the current uploaded image and makes the output appropriate for inference.

## Project structure

```text
sfanet-counting-api/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   └── sfanet_service.py
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
├── test_sfanet.py
└── README.md
```

## Installation

```bash
cd sfanet-counting-api
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Windows:

```powershell
.venv\Scripts\activate
```

## Fixing the LWCC weights path on macOS

Some LWCC releases incorrectly use `/.lwcc/weights`, which is read-only on macOS. With the virtual environment active, run:

```bash
python scripts/fix_lwcc_path.py
```

The correct directory is:

```text
~/.lwcc/weights/
```

The expected SFANet weight file is downloaded or read from this directory.

## Automated tests

```bash
pytest -v
```

The tests verify:

- the API starts correctly;
- invalid image content is rejected;
- temporary upload files are removed;
- response fields match the shared project format;
- `model.eval()` is called;
- the density-map PNG preserves the native density-array dimensions.

The automated tests mock the neural-network inference. They verify the application code, not the accuracy of the pretrained model.

## Real model test

```bash
python test_sfanet.py
```

This loads the actual SFANet-SHB weights, runs inference on `test_images/test.jpg`, and saves the density map under `outputs/density_maps/`.

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
  "model": "SFANet",
  "model_weights": "SHB",
  "training_dataset": "ShanghaiTech Part B (SHB)",
  "method": "Density Estimation + Multi-Scale Fusion + Attention",
  "task": "Crowd Counting",
  "estimated_count": 42.73,
  "rounded_count": 43,
  "density_map_shape": [336, 496],
  "density_map_url": "/outputs/density_maps/sfanet_density_example.png",
  "inference_time_seconds": 1.2345
}
```

## Limitations

- The project uses pretrained weights supplied through LWCC; it does not train SFANet from scratch.
- A valid model output does not prove counting accuracy without a ground-truth count.
- SFANet is available through LWCC with SHB weights, while the other selected models may use SHA weights.
- The first inference can be slower because the model and weights are loaded lazily.
