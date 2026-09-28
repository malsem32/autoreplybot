from fastapi import HTTPException, status

from backend.core.uploads import resolve_upload_ref
from backend.models.user import User
from backend.services import pro


def resolve_photos(refs: list[str], user: User) -> list[str]:
    """Validates photo refs from the Mini App against the user's plan and
    maps them to on-disk upload paths (see resolve_upload_ref)."""
    unique_refs = list(dict.fromkeys(r for r in refs if r))
    limit = pro.max_photos(user)
    if len(unique_refs) > limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Альбом из {len(unique_refs)} фото доступен в Pro (без Pro — {limit} фото)",
        )
    try:
        return [resolve_upload_ref(r) for r in unique_refs]
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc).capitalize()) from exc
