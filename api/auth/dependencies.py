from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from api.auth.tokens import decode_token
from api.storage.users import UserStore

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=True,
)

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False,
)


def _get_store() -> UserStore:
    return UserStore()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    store: UserStore = Depends(_get_store),
) -> dict:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise exc
    if payload.get("type") != "access":
        raise exc
    user_id: str = payload.get("sub")
    if not user_id:
        raise exc
    user = store.get_user(user_id)
    if user is None:
        raise exc
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    store: UserStore = Depends(_get_store),
) -> Optional[dict]:
    if not token:
        return None
    try:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return store.get_user(user_id)
    except Exception:
        return None
