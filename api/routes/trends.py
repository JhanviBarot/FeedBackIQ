from fastapi import APIRouter, Depends

from api.auth.dependencies import get_current_user, get_current_user_optional
from api.storage.users import UserStore
from api.storage.sessions import SessionStore
from core.trend_engine import compute_trends

router = APIRouter(prefix="/trends", tags=["Trends"])


@router.get("/me")
async def get_my_trends(
    current_user: dict = Depends(get_current_user),
):
    result = compute_trends(current_user["user_id"], UserStore(), SessionStore())
    if not result.get("available"):
        result["message"] = "Analyse at least 2 batches of reviews to see trends."
    return result


@router.get("/{session_id}/context")
async def get_session_trend_context(
    session_id: str,
    current_user: dict = Depends(get_current_user_optional),
):
    session_store = SessionStore()
    session = session_store.get_session(session_id)

    if not session or not session.get("user_id"):
        return {"available": False, "session_id": session_id}

    result = compute_trends(session["user_id"], UserStore(), session_store)
    if not result.get("available"):
        result["message"] = "Analyse at least 2 batches of reviews to see trends."
    result["session_id"] = session_id
    return result
