from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from api.models import (CreateSessionRequest, CreateSessionResponse,
                        SessionsListResponse, SessionSummary)
from api.storage.sessions import SessionStore
from api.auth.dependencies import get_current_user_optional

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _validate_categories(categories: list) -> None:
    def overlap(a: str, b: str) -> float:
        wa, wb = set(a.lower().split()), set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / max(len(wa), len(wb))

    for i in range(len(categories)):
        for j in range(i + 1, len(categories)):
            a, b = categories[i].strip(), categories[j].strip()
            if overlap(a, b) >= 0.6:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Categories '{a}' and '{b}' are too similar. "
                           f"Use more distinct names.",
                )


@router.post("", response_model=CreateSessionResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new analysis session")
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    categories = [c.strip() for c in request.categories if c.strip()]
    if len(categories) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least 2 non-empty categories required",
        )
    _validate_categories(categories)

    profile = {
        "company_name": request.company_name.strip(),
        "industry": request.industry.strip(),
        "categories": categories,
        "description": (request.description or "").strip(),
        "urgency_definition": (request.urgency_definition or "").strip(),
    }
    user_id = current_user["user_id"] if current_user else None

    store = SessionStore()
    session_id = store.create_session(profile, user_id=user_id)

    return CreateSessionResponse(
        session_id=session_id,
        profile=profile,
        created_at=datetime.now(timezone.utc).isoformat(),
        user_id=user_id,
    )


@router.get("", response_model=SessionsListResponse,
            summary="List current user's analysis sessions")
async def list_sessions(
    current_user: dict = Depends(get_current_user_optional),
):
    if not current_user:
        return SessionsListResponse(sessions=[], total=0)

    history = current_user.get("session_history", [])
    sessions = [
        SessionSummary(
            session_id=item.get("session_id", ""),
            label=item.get("label", "Analysis"),
            created_at=item.get("created_at", ""),
            total_reviews=item.get("total_reviews", 0),
            overall_score=item.get("overall_score", 0.0),
        )
        for item in history
    ]
    return SessionsListResponse(sessions=sessions, total=len(sessions))
