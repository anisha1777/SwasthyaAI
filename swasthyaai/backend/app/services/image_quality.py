from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError


# ------------------------------------------------------------
# Configurable engineering thresholds
# These are implementation thresholds, not clinical standards.
# They can be tuned later using your validation data.
# ------------------------------------------------------------

MIN_WIDTH = 160
MIN_HEIGHT = 160

MIN_BLUR_SCORE = 40.0

MIN_BRIGHTNESS = 30.0
MAX_BRIGHTNESS = 225.0

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def calculate_blur_score(image: Image.Image) -> float:
    """
    Calculate a simple Laplacian-variance style blur score.

    Higher score  -> sharper image
    Lower score   -> blurrier image
    """

    gray = image.convert("L")
    array = np.asarray(gray, dtype=np.float32)

    if array.shape[0] < 3 or array.shape[1] < 3:
        return 0.0

    center = array[1:-1, 1:-1]

    laplacian = (
        array[:-2, 1:-1]
        + array[2:, 1:-1]
        + array[1:-1, :-2]
        + array[1:-1, 2:]
        - 4 * center
    )

    return float(np.var(laplacian))


def check_image_quality(
    image_path: str,
) -> dict:
    """
    Validate image resolution, format, size, blur and brightness.

    Returns a machine-readable result.
    """

    path = Path(image_path)

    # --------------------------------------------------------
    # File existence
    # --------------------------------------------------------

    if not path.exists():
        return {
            "quality_status": "FAIL",
            "reason_code": "FILE_NOT_FOUND",
            "message": "Image file was not found.",
        }

    # --------------------------------------------------------
    # File extension
    # --------------------------------------------------------

    extension = path.suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return {
            "quality_status": "FAIL",
            "reason_code": "UNSUPPORTED_FORMAT",
            "message": "Unsupported image format.",
        }

    # --------------------------------------------------------
    # File size
    # --------------------------------------------------------

    file_size = path.stat().st_size

    if file_size == 0:
        return {
            "quality_status": "FAIL",
            "reason_code": "EMPTY_FILE",
            "message": "Uploaded image is empty.",
        }

    if file_size > MAX_FILE_SIZE:
        return {
            "quality_status": "FAIL",
            "reason_code": "FILE_TOO_LARGE",
            "message": "Image size exceeds the 10 MB limit.",
        }

    # --------------------------------------------------------
    # Open image
    # --------------------------------------------------------

    try:
        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:
            image = image.convert("RGB")

            width, height = image.size

            # ------------------------------------------------
            # Resolution
            # ------------------------------------------------

            if width < MIN_WIDTH or height < MIN_HEIGHT:
                return {
                    "quality_status": "FAIL",
                    "reason_code": "RESOLUTION_TOO_LOW",
                    "message": (
                        f"Image resolution is too low. "
                        f"Minimum required resolution is "
                        f"{MIN_WIDTH}x{MIN_HEIGHT} pixels."
                    ),
                    "metrics": {
                        "width": width,
                        "height": height,
                    },
                }

            # ------------------------------------------------
            # Brightness
            # ------------------------------------------------

            pixels = np.asarray(image, dtype=np.float32)

            grayscale = (
                0.299 * pixels[:, :, 0]
                + 0.587 * pixels[:, :, 1]
                + 0.114 * pixels[:, :, 2]
            )

            brightness = float(np.mean(grayscale))

            if brightness < MIN_BRIGHTNESS:
                return {
                    "quality_status": "FAIL",
                    "reason_code": "IMAGE_TOO_DARK",
                    "message": (
                        "Image is too dark. "
                        "Please capture the image in better lighting."
                    ),
                    "metrics": {
                        "width": width,
                        "height": height,
                        "brightness": round(brightness, 2),
                    },
                }

            if brightness > MAX_BRIGHTNESS:
                return {
                    "quality_status": "FAIL",
                    "reason_code": "IMAGE_TOO_BRIGHT",
                    "message": (
                        "Image is overexposed. "
                        "Please avoid direct or excessive lighting."
                    ),
                    "metrics": {
                        "width": width,
                        "height": height,
                        "brightness": round(brightness, 2),
                    },
                }

            # ------------------------------------------------
            # Blur
            # ------------------------------------------------

            blur_score = calculate_blur_score(image)

            if blur_score < MIN_BLUR_SCORE:
                return {
                    "quality_status": "FAIL",
                    "reason_code": "IMAGE_TOO_BLURRY",
                    "message": (
                        "Image is too blurry. "
                        "Please hold the camera steady and recapture."
                    ),
                    "metrics": {
                        "width": width,
                        "height": height,
                        "brightness": round(brightness, 2),
                        "blur_score": round(blur_score, 2),
                    },
                }

            # ------------------------------------------------
            # PASS
            # ------------------------------------------------

            return {
                "quality_status": "PASS",
                "reason_code": "IMAGE_QUALITY_OK",
                "message": "Image passed quality checks.",
                "metrics": {
                    "width": width,
                    "height": height,
                    "brightness": round(brightness, 2),
                    "blur_score": round(blur_score, 2),
                    "file_size": file_size,
                },
            }

    except UnidentifiedImageError:
        return {
            "quality_status": "FAIL",
            "reason_code": "INVALID_IMAGE",
            "message": "Uploaded file is not a valid image.",
        }

    except Exception as exc:
        return {
            "quality_status": "FAIL",
            "reason_code": "IMAGE_VALIDATION_ERROR",
            "message": f"Unable to validate image: {exc}",
        }
