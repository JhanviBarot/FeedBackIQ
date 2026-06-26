import io
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from api.storage.sessions import SessionStore
from api.auth.dependencies import get_current_user_optional
from core.pdf_report import generate_pdf

router = APIRouter(prefix="/report", tags=["Report"])


@router.get("/{session_id}", summary="Download PDF report for a session")
async def download_report(
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
            detail="Run analysis first before downloading report",
        )

    results_df = store.get_results_df(session)
    if results_df is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Results data missing. Re-run the analysis.",
        )

    dashboard_data = store.get_dashboard_data(session)
    if not dashboard_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dashboard data missing. Re-run the analysis.",
        )

    action_plan = session.get("action_plan") or {
        "success": False,
        "result": None,
        "health_score": 0,
        "health_label": "—",
        "error": "Not generated",
    }

    try:
        pdf_bytes = generate_pdf(
            dashboard_data=dashboard_data,
            action_plan=action_plan,
            profile=session["profile"],
            results_df=results_df,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}",
        )

    filename = f"feedbackiq_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
