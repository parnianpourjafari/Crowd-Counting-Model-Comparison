import numpy as np
from PIL import Image

import app.bayesian_service as service
from app.config import DENSITY_MAP_DIR


def test_predict_count_saves_density_at_native_size(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "crowd.jpg"
    Image.new("RGB", (32, 24), "white").save(image_path)

    class FakeModel:
        def eval(self):
            return self

    density = np.arange(24, dtype=np.float32).reshape(4, 6)

    monkeypatch.setattr(service, "get_model", lambda: FakeModel())
    monkeypatch.setattr(
        service.LWCC,
        "get_count",
        lambda *args, **kwargs: (9.6, density),
    )

    result = service.predict_count(image_path)
    output_path = DENSITY_MAP_DIR / result["density_map_filename"]

    try:
        assert result["model"] == "Bayesian Crowd Counting"
        assert result["estimated_count"] == 9.6
        assert result["rounded_count"] == 10
        assert result["density_map_shape"] == [4, 6]

        with Image.open(output_path) as saved_density:
            assert saved_density.size == (6, 4)
    finally:
        output_path.unlink(missing_ok=True)
