from fastapi import APIRouter, Depends

from api.auth.dependencies import get_current_user_optional
from api.storage.sessions import SessionStore
from core.benchmark_engine import get_benchmarks_for_industry, _load_benchmarks, _MIN_COMPANIES

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])

_UNAVAILABLE = {"available": False, "reason": "insufficient_data", "company_count": 0}


@router.get("/industry/{industry_name}")
async def get_industry_aggregate(
    industry_name: str,
    current_user: dict = Depends(get_current_user_optional),
):
    data = _load_benchmarks()
    entry = data.get("industries", {}).get(industry_name)
    if not entry or entry.get("company_count", 0) < _MIN_COMPANIES:
        return {
            "available": False,
            "reason": "insufficient_data",
            "company_count": entry.get("company_count", 0) if entry else 0,
        }
    return {
        "available": True,
        "industry": industry_name,
        "company_count": entry["company_count"],
        "avg_overall_score": entry["avg_overall_score"],
        "avg_positive_pct": entry["avg_positive_pct"],
        "avg_negative_pct": entry["avg_negative_pct"],
        "avg_critical_pct": entry["avg_critical_pct"],
        "common_top_category": entry.get("common_top_category", ""),
        "score_distribution": entry.get("score_distribution", {}),
        "avg_total_reviews": entry.get("avg_total_reviews", 0.0),
    }


@router.get("/{session_id}")
async def get_session_benchmarks(
    session_id: str,
    current_user: dict = Depends(get_current_user_optional),
):
    try:
        store = SessionStore()
        session = store.get_session(session_id)
        if not session or not session.get("classification_done"):
            return _UNAVAILABLE

        profile = session.get("profile", {})
        industry = profile.get("industry", "")
        if not industry:
            return _UNAVAILABLE

        serialised = session.get("dashboard_data_serialised")
        if not serialised:
            return _UNAVAILABLE

        dd = store.deserialise_dashboard(serialised)
        sentiment = dd.get("sentiment", {})

        return get_benchmarks_for_industry(
            industry=industry,
            user_overall_score=float(sentiment.get("overall_score", 0.0)),
            user_positive_pct=float(sentiment.get("positive_pct", 0.0)),
            user_negative_pct=float(sentiment.get("negative_pct", 0.0)),
            user_critical_pct=float(dd.get("urgency", {}).get("critical_pct", 0.0)),
        )
    except Exception:
        return _UNAVAILABLE
