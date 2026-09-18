from fastapi import Header, HTTPException, status

from backend.core.security import InitDataError, decode_admin_token


async def get_current_admin(authorization: str = Header(...)) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid authorization scheme")
    try:
        return decode_admin_token(token)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
