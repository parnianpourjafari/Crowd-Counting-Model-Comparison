from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

import app.main as main_module
from app.config import UPLOAD_DIR

client = TestClient(main_module.app)


def make_test_image() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 24), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_rejects_non_image_content() -> None:
    response = client.post(
        "/predict",
        files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
    )
    assert response.status_code == 400


def test_prediction_response_and_upload_cleanup(monkeypatch) -> None:
    def fake_predict_count(_image_path):
        return {
            "model": "DM-Count",
            "model_weights": "SHA",
            "training_dataset": "ShanghaiTech Part A (SHA)",
            "method": "Density Estimation + Distribution Matching",
            "task": "Crowd Counting",
            "estimated_count": 12.4,
            "rounded_count": 12,
            "density_map_shape": [8, 12],
            "density_map_filename": "fake_density.png",
        }

    monkeypatch.setattr(main_module, "predict_count", fake_predict_count)

    before = {path.name for path in UPLOAD_DIR.iterdir() if path.is_file()}

    response = client.post(
        "/predict",
        files={"file": ("crowd.jpg", make_test_image(), "image/jpeg")},
    )

    after = {path.name for path in UPLOAD_DIR.iterdir() if path.is_file()}

    assert response.status_code == 200
    result = response.json()
    assert result["estimated_count"] == 12.4
    assert result["rounded_count"] == 12
    assert result["density_map_shape"] == [8, 12]
    assert result["density_map_url"].endswith("fake_density.png")
    assert before == after
