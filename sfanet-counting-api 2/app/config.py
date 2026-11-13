from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
DENSITY_MAP_DIR = OUTPUT_DIR / "density_maps"

MODEL_DISPLAY_NAME = "SFANet"
LWCC_MODEL_NAME = "SFANet"
MODEL_WEIGHTS = "SHB"
MODEL_METHOD = "Density Estimation + Multi-Scale Fusion + Attention"
MODEL_TASK = "Crowd Counting"
TRAINING_DATASET = "ShanghaiTech Part B (SHB)"

MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "BMP", "WEBP", "TIFF"}
IMAGE_FORMAT_SUFFIXES = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "BMP": ".bmp",
    "WEBP": ".webp",
    "TIFF": ".tiff",
}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DENSITY_MAP_DIR.mkdir(parents=True, exist_ok=True)
