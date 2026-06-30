from fastapi import APIRouter, HTTPException, Depends, status
from api.storage.sessions import SessionStore
from api.auth.dependencies import get_current_user_optional
from core.clustering_engine import cluster_reviews_by_category

router = APIRouter(prefix="/clusters", tags=["Clusters"])


@router.get("/{session_id}",
            summary="Get within-category review theme clusters for a session")
async def get_clusters(
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

    results_df = store.get_results_df(session)
    if results_df is None or results_df.empty:
        return {"available": False, "reason": "no_data"}

    # cluster_reviews_by_category never raises — it returns its own
    # available flag with either clustered categories or an error reason.
    return cluster_reviews_by_category(results_df)
