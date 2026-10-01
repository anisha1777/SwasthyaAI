from app.services.image_quality import check_image_quality


def test_image_quality():
    result = check_image_quality("test_images/jaundice_test.jpg")

    assert result["quality_status"] == "PASS"
    assert result["reason_code"] == "IMAGE_QUALITY_OK"

    metrics = result["metrics"]

    assert metrics["width"] >= 160
    assert metrics["height"] >= 160
    assert metrics["file_size"] > 0
