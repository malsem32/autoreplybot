import uuid
from pathlib import Path

UPLOAD_DIR = Path("/app/uploads")
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB, matches Telegram's photo limit headroom

_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def save_upload(content: bytes, content_type: str) -> str:
    """Writes an uploaded photo to the shared uploads volume and returns its
    path. Both backend and worker containers mount this volume (see
    docker-compose.yml) so the broadcaster/responder can read it back."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = _EXTENSIONS[content_type]
    filename = f"{uuid.uuid4().hex}{extension}"
    path = UPLOAD_DIR / filename
    path.write_bytes(content)
    return str(path)


def delete_upload(path: str | None) -> None:
    if not path:
        return
    Path(path).unlink(missing_ok=True)
