from datetime import datetime, timezone
from typing import List, Dict


def get_session_data_for_trends(user_store, session_store, user_id: str) -> List[Dict]:
    """Load and normalize all completed session data for a user, sorted ascending by date.

    Exceptions from user_store/session_store propagate up — callers handle them.
    Per-session decode failures are skipped silently.
    """
    user = user_store.get_user(user_id)
    if not user:
        return []

    result = []
    for entry in user.get("session_history", []):
        try:
            session_id = entry.get("session_id")
            if not session_id:
                continue

            session = session_store.get_session(session_id)
            if not session or not session.get("classification_done"):
                continue

            serialised = session.get("dashboard_data_serialised")
            if not serialised:
                continue

            dd = session_store.deserialise_dashboard(serialised)

            sentiment = dd.get("sentiment", {})
            categories = dd.get("categories", [])
            urgency = dd.get("urgency", {})
            top_issues = dd.get("top_issues", [])

            result.append({
                "session_id": session_id,
                "created_at": entry.get("created_at", ""),
                "label": entry.get("label", ""),
                "total_reviews": entry.get("total_reviews", 0),
                "overall_score": float(entry.get("overall_score", 0.0)),
                "sentiment": {
                    "positive_pct": float(sentiment.get("positive_pct", 0.0)),
                    "negative_pct": float(sentiment.get("negative_pct", 0.0)),
                    "neutral_pct": float(sentiment.get("neutral_pct", 0.0)),
                },
                "categories": [
                    {
                        "category": c.get("category", ""),
                        "count": c.get("count", 0),
                        "pct": float(c.get("pct", 0.0)),
                    }
                    for c in categories
                ],
                "urgency": {
                    "critical_count": urgency.get("critical_count", 0),
                    "critical_pct": float(urgency.get("critical_pct", 0.0)),
                },
                "top_issues": [
                    {
                        "category": iss.get("category", ""),
                        "count": iss.get("count", 0),
                        "critical_count": iss.get("critical_count", 0),
                    }
                    for iss in top_issues
                ],
                "top_category": dd.get("top_category", ""),
            })
        except Exception:
            continue

    result.sort(key=lambda x: x.get("created_at", ""))
    return result


def compute_sentiment_trajectory(sessions: List[Dict]) -> Dict:
    """Compute overall score trajectory across sessions."""
    points = [
        {
            "session_id": s["session_id"],
            "label": s["label"],
            "created_at": s["created_at"],
            "overall_score": s["overall_score"],
            "positive_pct": s["sentiment"]["positive_pct"],
            "negative_pct": s["sentiment"]["negative_pct"],
        }
        for s in sessions
    ]

    if len(sessions) < 2:
        return {"points": points, "trend": "insufficient_data", "change": 0.0}

    change = round(sessions[-1]["overall_score"] - sessions[0]["overall_score"], 2)

    if change > 5:
        trend = "improving"
    elif change < -5:
        trend = "declining"
    else:
        trend = "stable"

    return {"points": points, "trend": trend, "change": change}


def compute_category_drift(sessions: List[Dict]) -> Dict:
    """Compare category percentage volumes between first and latest session."""
    empty = {
        "growing": [],
        "shrinking": [],
        "stable": [],
        "new_categories": [],
        "dropped_categories": [],
    }

    if len(sessions) < 2:
        return empty

    first_cats = {c["category"]: c["pct"] for c in sessions[0].get("categories", [])}
    latest_cats = {c["category"]: c["pct"] for c in sessions[-1].get("categories", [])}

    new_categories = sorted(set(latest_cats) - set(first_cats))
    dropped_categories = sorted(set(first_cats) - set(latest_cats))

    growing, shrinking, stable = [], [], []

    for cat in set(first_cats) & set(latest_cats):
        change = round(latest_cats[cat] - first_cats[cat], 2)
        item = {
            "category": cat,
            "first_pct": first_cats[cat],
            "latest_pct": latest_cats[cat],
            "change": change,
        }
        if change > 5:
            growing.append(item)
        elif change < -5:
            shrinking.append(item)
        else:
            stable.append(item)

    growing.sort(key=lambda x: x["change"], reverse=True)
    shrinking.sort(key=lambda x: x["change"])
    stable.sort(key=lambda x: x["category"])

    return {
        "growing": growing,
        "shrinking": shrinking,
        "stable": stable,
        "new_categories": new_categories,
        "dropped_categories": dropped_categories,
    }


def compute_emerging_issues(sessions: List[Dict]) -> Dict:
    """Compare top issue critical counts between the previous and latest session."""
    empty = {"emerging": [], "resolved": [], "unchanged": []}

    if len(sessions) < 2:
        return empty

    prev_issues = {
        iss["category"]: iss["critical_count"]
        for iss in sessions[-2].get("top_issues", [])
    }
    latest_issues = {
        iss["category"]: iss["critical_count"]
        for iss in sessions[-1].get("top_issues", [])
    }

    all_cats = set(prev_issues) | set(latest_issues)
    emerging, resolved, unchanged = [], [], []

    for cat in all_cats:
        prev_c = prev_issues.get(cat, 0)
        curr_c = latest_issues.get(cat, 0)
        change = curr_c - prev_c

        if change > 0:
            emerging.append({
                "category": cat,
                "previous_critical": prev_c,
                "current_critical": curr_c,
                "change": change,
            })
        elif curr_c == 0 and prev_c > 0:
            resolved.append({
                "category": cat,
                "previous_critical": prev_c,
                "current_critical": curr_c,
            })
        else:
            unchanged.append(cat)

    emerging.sort(key=lambda x: x["change"], reverse=True)
    return {"emerging": emerging, "resolved": resolved, "unchanged": sorted(unchanged)}


def compute_trends(user_id: str, user_store, session_store) -> Dict:
    """Orchestrate all trend computations. Never raises — returns available=False on error."""
    try:
        sessions = get_session_data_for_trends(user_store, session_store, user_id)

        if len(sessions) < 2:
            return {
                "available": False,
                "session_count": len(sessions),
                "sessions_analysed": len(sessions),
                "sentiment_trajectory": compute_sentiment_trajectory(sessions),
                "category_drift": compute_category_drift(sessions),
                "emerging_issues": compute_emerging_issues(sessions),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "available": True,
            "session_count": len(sessions),
            "sessions_analysed": len(sessions),
            "sentiment_trajectory": compute_sentiment_trajectory(sessions),
            "category_drift": compute_category_drift(sessions),
            "emerging_issues": compute_emerging_issues(sessions),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        return {"available": False, "session_count": 0, "error": str(exc)}
