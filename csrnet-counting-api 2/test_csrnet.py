from pathlib import Path

from app.csrnet_service import predict_count

BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "test_images" / "test.jpg"


def main() -> None:
    result = predict_count(IMAGE_PATH)

    print(f"Model: {result['model']}")
    print(f"Weights: {result['model_weights']}")
    print(f"Training dataset: {result['training_dataset']}")
    print(f"Estimated count: {result['estimated_count']}")
    print(f"Rounded count: {result['rounded_count']}")
    print(f"Density map shape: {tuple(result['density_map_shape'])}")
    print(f"Density map file: {result['density_map_filename']}")


if __name__ == "__main__":
    main()
