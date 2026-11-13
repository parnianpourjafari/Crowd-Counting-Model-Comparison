import os

# Folder names of the sibling FastAPI services, relative to PROJECT_ROOT below.
# Override per-service with these env vars if your checkout uses different
# folder names (e.g. CROWD_COUNTING_DMCOUNT_DIR=my-dmcount-service).
MODELS = {
    "dmcount": {
        "label": "DM-Count",
        "base_url": "http://localhost:8001",
        "port": 8001,
        "description": "Density estimation + distribution matching. Balanced accuracy and speed.",
        "service_dir": os.environ.get("CROWD_COUNTING_DMCOUNT_DIR", "DMcount-counting-api 2"),
    },
    "bayesian": {
        "label": "Bayesian",
        "base_url": "http://localhost:8002",
        "port": 8002,
        "description": "Bayesian loss model. Strongest overall accuracy on dense crowds.",
        "service_dir": os.environ.get("CROWD_COUNTING_BAYESIAN_DIR", "bayesian-counting-api 2"),
    },
    "csrnet": {
        "label": "CSRNet",
        "base_url": "http://localhost:8003",
        "port": 8003,
        "description": "Dilated-convolution CNN. Fastest inference, good for dense scenes.",
        "service_dir": os.environ.get("CROWD_COUNTING_CSRNET_DIR", "csrnet-counting-api 2"),
    },
    "sfanet": {
        "label": "SFANet",
        "base_url": "http://localhost:8004",
        "port": 8004,
        "description": "Scale-adaptive attention network. Best on lower-density street scenes.",
        "service_dir": os.environ.get("CROWD_COUNTING_SFANET_DIR", "sfanet-counting-api 2"),
    },
}

DEFAULT_MODEL_KEY = "dmcount"

# Directory that contains the service folders above. Defaults to the parent
# of this UI project's folder; override if your services live elsewhere.
PROJECT_ROOT_OVERRIDE = os.environ.get("CROWD_COUNTING_PROJECT_ROOT")

HEALTH_CHECK_INTERVAL_MS = 12_000
HEALTH_CHECK_TIMEOUT_SECONDS = 2
PREDICT_TIMEOUT_SECONDS = 60

MAX_UPLOAD_SIZE_MB = 10
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
