from app.ml.inference import predict


def test_jaundice_inference():
    result = predict(
        "test_images/jaundice_test.jpg",
        "jaundice"
    )

    assert result["screening_type"] == "jaundice"
    assert result["prediction"] in ["Jaundice", "Normal_Eye"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["model_version"] == "jaundice-efficientnet-b5-v1"


def test_skin_inference():
    result = predict(
        "test_images/skin_test.jpg",
        "skin"
    )

    assert result["screening_type"] == "skin"
    assert result["prediction"] in ["AD", "CD", "EC", "SC", "SD", "TC"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["model_version"] == "skin-efficientnet-b5-v1"
