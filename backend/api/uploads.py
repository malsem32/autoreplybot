from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.core.rate_limit import rate_limit
from backend.core.uploads import (
    ALLOWED_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
    UPLOAD_DIR,
    is_safe_filename,
    photo_url,
    save_upload,
)
from backend.models.user import User

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/photo")
async def upload_photo(
    file: UploadFile,
    _user: User = Depends(rate_limit("uploads", limit=60, window_seconds=600)),
) -> dict:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Поддерживаются только JPEG, PNG и WebP")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл слишком большой (максимум 10 МБ)")

    path = save_upload(content, file.content_type)
    return {"path": path, "url": photo_url(path)}


@router.get("/{filename}")
async def get_photo(filename: str) -> FileResponse:
    # Intentionally unauthenticated: an <img src> can't send the `tma`
    # header, so access relies on the filename being an unguessable
    # UUID (see save_upload). Uploading still requires initData (above).
    if not is_safe_filename(filename):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не найден")
    path = UPLOAD_DIR / filename
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не найден")
    return FileResponse(path)
