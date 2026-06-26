import io
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from api.storage.sessions import SessionStore
from api.auth.dependencies import get_current_user_optional

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/{session_id}", summary="Download classified results as CSV")
async def export_csv(
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
            detail="Run analysis first before exporting",
        )

    results_df = store.get_results_df(session)
    if results_df is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Results data missing. Re-run the analysis.",
        )

    csv_bytes = results_df.to_csv(index=False).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="feedbackiq_results.csv"'
        },
    )
