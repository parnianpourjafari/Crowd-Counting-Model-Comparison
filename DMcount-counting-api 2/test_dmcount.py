from pathlib import Path

from app.dmcount_service import predict_count

IMAGE_PATH = Path("test_images/test.jpg")


def main() -> None:
    result = predict_count(IMAGE_PATH)

    print("Model:", result["model"])
    print("Weights:", result["model_weights"])
    print("Estimated count:", result["estimated_count"])
    print("Rounded count:", result["rounded_count"])
    print("Density map shape:", tuple(result["density_map_shape"]))
    print(
        "Density map saved to:",
        Path("outputs/density_maps") / result["density_map_filename"],
    )


if __name__ == "__main__":
    main()
