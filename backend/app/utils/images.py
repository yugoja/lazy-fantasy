from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image

UPLOADS_DIR = Path("uploads")
AVATARS_DIR = UPLOADS_DIR / "avatars"
LEAGUES_DIR = UPLOADS_DIR / "leagues"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2MB


def save_upload(
    file_bytes: bytes,
    content_type: str,
    dest_path: Path,
    max_size: tuple[int, int],
) -> None:
    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be under 2MB",
        )
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are allowed",
        )
    try:
        img = Image.open(BytesIO(file_bytes))
        img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process image",
        )
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, format="JPEG", quality=85, optimize=True)
