from fastapi import APIRouter, Depends

from backend.api.deps import get_current_user
from backend.models.user import User

router = APIRouter(prefix="/api/dialogs", tags=["dialogs"])


@router.get("/{account_id}")
async def list_dialogs(account_id: int, user: User = Depends(get_current_user)) -> list[dict]:
    # TODO: fetch live dialogs from the running Pyrogram client via workers.client_manager
    # once that pool exposes a query interface; placeholder keeps the route contract stable.
    return []
