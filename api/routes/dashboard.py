from fastapi import APIRouter, HTTPException, Depends, status
from api.models import DashboardResponse
from api.storage.sessions import SessionStore
from api.auth.dependencies import get_current_user_optional

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/{session_id}", response_model=DashboardResponse,
            summary="Get full dashboard data for a session")
async def get_dashboard(
    session_id: str,
    current_user: dict = Depends(get_current_user_optional),
):
    store = SessionStore()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found or expired",
        )

    if current_user and session.get("user_id"):
        if session["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This session belongs to a different user",
            )

    if not session.get("classification_done"):
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Analysis not yet complete for this session. "
                   "Run POST /analyse/text or /analyse/file first.",
        )

    serialised = session.get("dashboard_data_serialised")
    if not serialised:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dashboard data missing from session. Re-run the analysis.",
        )

    return DashboardResponse(
        session_id=session_id,
        profile=session["profile"],
        dashboard_data=serialised,
        classification_done=True,
        total_classified=session.get("total_classified", 0),
    )
