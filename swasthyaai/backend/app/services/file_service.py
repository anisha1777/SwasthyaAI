from pathlib import Path
import secrets

from fastapi import UploadFile, HTTPException
from PIL import Image


ALLOWED_TYPES = {
    "image/jpeg",
    "image/png"
}

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png"
}


def safe_extension(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image extension"
        )

    return ext


async def save_upload(
    upload: UploadFile,
    base_dir: str,
    max_bytes: int
):
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG/PNG images are accepted"
        )

    ext = safe_extension(upload.filename or "")

    data = await upload.read()

    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds maximum allowed size"
        )

    Path(base_dir).mkdir(
        parents=True,
        exist_ok=True
    )

    filename = secrets.token_hex(16) + ext

    path = Path(base_dir) / filename

    path.write_bytes(data)

    try:
        with Image.open(path) as img:
            width, height = img.size
            img.verify()

    except Exception:
        path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image"
        )

    return str(path), len(data), width, height
