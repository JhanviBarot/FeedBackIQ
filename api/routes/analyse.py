import os
import tempfile
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse

from api.middleware.rate_limiter import limiter

from api.models import AnalyseResponse, PreprocessingSummary
from api.storage.sessions import SessionStore
from api.storage.users import UserStore
from api.auth.dependencies import get_current_user_optional
from core.preprocessing import preprocess
from core.classifier_async import classify_all_batches_async
from core.benchmark_engine import record_analysis_for_benchmarks
from core.webhook_engine import check_alert_conditions, dispatch_webhooks_async
from core.aggregator import build_dashboard_data
from core.results import build_results_dataframe
from core.file_input import (parse_uploaded_file, extract_review_lines,
                              lines_to_raw_text)

router = APIRouter(prefix="/analyse", tags=["Analysis"])

BATCH_SIZE = 15


def _build_batches(reviews: list) -> list:
    return [reviews[i:i + BATCH_SIZE]
            for i in range(0, len(reviews), BATCH_SIZE)]


def _record_user_history(user_id: str, session_id: str,
                          total_classified: int,
                          overall_score: float) -> None:
    try:
        user_store = UserStore()
        summary = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_reviews": total_classified,
            "overall_score": round(overall_score, 1),
            "label": f"Analysis — {datetime.now().strftime('%d %b %Y')}",
        }
        user_store.add_session_to_history(user_id, summary)
    except Exception:
        pass


async def _run_analysis(session_id: str, raw_text: str,
                        current_user) -> AnalyseResponse:
    session_store = SessionStore()
    session = session_store.get_session(session_id)
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

    profile = session["profile"]

    # 1. Preprocessing
    prep_result = preprocess(raw_text)
    if prep_result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=prep_result["error"],
        )

    reviews = prep_result["reviews"]
    quality = prep_result.get("report", {})

    # 2. Classification
    batches = _build_batches(reviews)
    (
        all_results,
        failed_batches,
        total_classified,
        total_failed,
        gemini_fallback_count,
    ) = await classify_all_batches_async(batches, profile)

    if total_classified == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Classification failed for all batches. "
                   "Check your API keys and try again.",
        )

    # 3. Build results DataFrame
    results_df = build_results_dataframe(all_results, reviews)

    # 4. Aggregate dashboard data
    dashboard_data = build_dashboard_data(results_df)

    # 5. Store in session
    session_store.update_session(session_id, {
        "preprocessing_result": quality,
        "results_records": results_df.to_dict("records"),
        "results_columns": list(results_df.columns),
        "dashboard_data_serialised": SessionStore.serialise_dashboard(
            dashboard_data),
        "classification_done": True,
        "failed_batches": failed_batches,
        "total_classified": total_classified,
        "gemini_fallback_count": gemini_fallback_count,
    })

    # 6. Record to user history if authenticated
    if current_user:
        _record_user_history(
            current_user["user_id"], session_id, total_classified,
            dashboard_data["sentiment"]["overall_score"],
        )
        try:
            record_analysis_for_benchmarks(
                current_user["user_id"], profile["industry"], dashboard_data
            )
        except Exception:
            pass

        # 7. Webhook alert dispatch (fire-and-forget)
        try:
            _previous_dd = None
            _u = UserStore().get_user(current_user["user_id"])
            if _u:
                _hist = _u.get("session_history", [])
                # history[0] is current; history[1] is the previous analysis
                if len(_hist) > 1:
                    _prev_sid = _hist[1].get("session_id")
                    if _prev_sid:
                        _prev_sess = session_store.get_session(_prev_sid)
                        if _prev_sess and _prev_sess.get("classification_done"):
                            _ser = _prev_sess.get("dashboard_data_serialised")
                            if _ser:
                                _previous_dd = session_store.deserialise_dashboard(_ser)
            _triggered = check_alert_conditions(
                session_id, profile, dashboard_data, _previous_dd
            )
            if _triggered:
                dispatch_webhooks_async(
                    current_user["user_id"], session_id, profile, _triggered
                )
        except Exception:
            pass

    return AnalyseResponse(
        session_id=session_id,
        total_classified=total_classified,
        total_failed=total_failed,
        gemini_fallback_count=gemini_fallback_count,
        failed_batches=failed_batches,
        preprocessing=PreprocessingSummary(
            input_count=quality.get("input_count", 0),
            final_count=quality.get("final_count", 0),
            noise_removed=quality.get("noise_removed", 0),
            exact_duplicates_removed=quality.get("exact_duplicates_removed", 0),
            near_duplicates_removed=quality.get("near_duplicates_removed", 0),
            short_removed=quality.get("short_removed", 0),
        ),
    )


@router.post("/text", response_model=AnalyseResponse,
             summary="Analyse pasted review text")
@limiter.limit("5/minute")
async def analyse_text(
    request: Request,
    session_id: str = Form(...),
    raw_text: str = Form(...),
    current_user: dict = Depends(get_current_user_optional),
):
    if len(raw_text.encode("utf-8")) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Text payload exceeds 5MB limit",
        )
    return await _run_analysis(session_id, raw_text, current_user)


@router.post("/file", response_model=AnalyseResponse,
             summary="Analyse uploaded CSV or Excel file")
@limiter.limit("5/minute")
async def analyse_file(
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    column: str = Form(default=""),
    current_user: dict = Depends(get_current_user_optional),
):
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 10MB limit",
        )

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Use .csv, .xlsx, or .xls",
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            parse_result = parse_uploaded_file(f, filename)

        if parse_result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=parse_result["error"],
            )

        df = parse_result["dataframe"]
        detected_col = parse_result.get("detected_column", "")

        review_col = column.strip() if column.strip() else detected_col
        if not review_col:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not detect review column. "
                       "Pass 'column' parameter to specify it manually.",
            )
        if review_col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Column '{review_col}' not found in file. "
                       f"Available: {list(df.columns)}",
            )

        lines_result = extract_review_lines(df, review_col)
        if lines_result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=lines_result["error"],
            )
        raw_text = lines_to_raw_text(lines_result["raw_text_lines"])

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return await _run_analysis(session_id, raw_text, current_user)
