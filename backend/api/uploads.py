import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.api.deps import get_current_user
from backend.core.uploads import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, UPLOAD_DIR, save_upload
from backend.models.user import User

_SAFE_FILENAME = re.compile(r"^[a-f0-9]{32}\.(jpg|png|webp)$")

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/photo")
async def upload_photo(
    file: UploadFile,
    _user: User = Depends(get_current_user),
) -> dict:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unsupported image type")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "file too large")

    path = save_upload(content, file.content_type)
    filename = path.rsplit("/", 1)[-1]
    return {"path": path, "url": f"/api/uploads/{filename}"}


@router.get("/{filename}")
async def get_photo(filename: str) -> FileResponse:
    # Intentionally unauthenticated: an <img src> can't send the `tma`
    # header, so access relies on the filename being an unguessable
    # UUID (see save_upload). Uploading still requires initData (above).
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    path = UPLOAD_DIR / filename
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    return FileResponse(path)
