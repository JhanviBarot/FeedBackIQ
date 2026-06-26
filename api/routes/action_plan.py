from fastapi import APIRouter, HTTPException, Depends, Request, status
from api.models import ActionPlanResponse
from api.storage.sessions import SessionStore
from api.auth.dependencies import get_current_user_optional
from core.action_plan import generate_action_plan
from api.middleware.rate_limiter import limiter

router = APIRouter(prefix="/action-plan", tags=["Action Plan"])


@router.post("/{session_id}", response_model=ActionPlanResponse,
             summary="Generate AI action plan for a completed session")
@limiter.limit("10/minute")
async def create_action_plan(
    request: Request,
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
            detail="Run analysis first before generating action plan",
        )

    dashboard_data = store.get_dashboard_data(session)
    if not dashboard_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dashboard data missing. Re-run the analysis.",
        )

    profile = session["profile"]
    result = generate_action_plan(dashboard_data, profile)

    store.update_session(session_id, {"action_plan": result})

    return ActionPlanResponse(
        session_id=session_id,
        success=result.get("success", False),
        result=result.get("result"),
        health_score=result.get("health_score", 0),
        health_label=result.get("health_label", "Unknown"),
        provider=result.get("provider"),
        error=result.get("error"),
    )
