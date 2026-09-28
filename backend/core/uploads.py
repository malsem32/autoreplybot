import re
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


_SAFE_FILENAME = re.compile(r"^[a-f0-9]{32}\.(jpg|png|webp)$")


def is_safe_filename(filename: str) -> bool:
    return bool(_SAFE_FILENAME.match(filename))


def resolve_upload_ref(ref: str) -> str:
    """Turns a photo reference from the Mini App — the `path` returned by
    upload, its `/api/uploads/<name>` URL, or the bare filename — into the
    on-disk path under UPLOAD_DIR.

    Only uploaded (UUID-named) files are accepted: without this, a crafted
    request could make the worker send any file readable in its container
    (e.g. "/etc/passwd") into a chat. Raises ValueError otherwise."""
    filename = ref.rstrip("/").rsplit("/", 1)[-1]
    if not is_safe_filename(filename):
        raise ValueError("неизвестное фото — загрузите его заново")
    path = UPLOAD_DIR / filename
    if not path.is_file():
        raise ValueError("фото не найдено на сервере — загрузите его заново")
    return str(path)


def photo_url(path: str) -> str:
    return f"/api/uploads/{path.rsplit('/', 1)[-1]}"


def delete_uploads(paths: list[str] | None, keep: list[str] | None = None) -> None:
    """Deletes photo files no longer referenced (AGENTS.md 4.11)."""
    keep_set = set(keep or [])
    for path in paths or []:
        if path not in keep_set:
            delete_upload(path)
