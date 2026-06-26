import hashlib
import json
import os
from datetime import datetime, timezone

from filelock import FileLock

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
INDUSTRY_BENCHMARK_FILE = os.path.join(_DATA_DIR, "industry_benchmarks.json")
_LOCK_FILE = os.path.join(_DATA_DIR, "benchmarks.lock")

_EMPTY_BENCHMARKS = {"last_updated": None, "industries": {}}
_MIN_COMPANIES = 5
_MAX_COMPANIES = 500


def _get_user_hash(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()


def _load_benchmarks() -> dict:
    try:
        if not os.path.exists(INDUSTRY_BENCHMARK_FILE):
            return {"last_updated": None, "industries": {}}
        with open(INDUSTRY_BENCHMARK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "industries" not in data:
            return {"last_updated": None, "industries": {}}
        return data
    except Exception:
        return {"last_updated": None, "industries": {}}


def _save_benchmarks(data: dict) -> None:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        lock = FileLock(_LOCK_FILE, timeout=10)
        with lock:
            with open(INDUSTRY_BENCHMARK_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    except Exception:
        pass


def _score_bucket(score: float) -> str:
    if score <= 25:
        return "0-25"
    if score <= 50:
        return "26-50"
    if score <= 75:
        return "51-75"
    return "76-100"


def record_analysis_for_benchmarks(
    user_id: str, industry: str, dashboard_data: dict
) -> None:
    """Record one company's aggregated metrics into the industry benchmark file.

    Idempotent per user_id — repeated analyses update rather than duplicate.
    Never raises.
    """
    try:
        user_hash = _get_user_hash(user_id)
        sentiment = dashboard_data.get("sentiment", {})
        overall_score = float(sentiment.get("overall_score", 0.0))
        positive_pct = float(sentiment.get("positive_pct", 0.0))
        negative_pct = float(sentiment.get("negative_pct", 0.0))
        critical_pct = float(dashboard_data.get("urgency", {}).get("critical_pct", 0.0))
        total_reviews = int(dashboard_data.get("total_reviews", 0))
        top_category = str(dashboard_data.get("top_category", ""))

        data = _load_benchmarks()
        industries = data.setdefault("industries", {})

        if industry not in industries:
            industries[industry] = {
                "company_count": 0,
                "avg_overall_score": 0.0,
                "avg_positive_pct": 0.0,
                "avg_negative_pct": 0.0,
                "avg_critical_pct": 0.0,
                "common_top_category": top_category,
                "score_distribution": {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0},
                "avg_total_reviews": 0.0,
                "companies": [],
                "_top_category_votes": {},
            }

        entry = industries[industry]
        companies: list = entry.setdefault("companies", [])
        votes: dict = entry.setdefault("_top_category_votes", {})
        dist: dict = entry.setdefault(
            "score_distribution", {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
        )

        if user_hash in companies:
            # Update existing contribution — remove old bucket, recompute running avg.
            n = entry["company_count"]
            if n > 1:
                # Reverse the old contribution (we don't store old values per user, so we
                # just recompute the avg as if replacing: treat new value as a full update).
                # Simple approach: re-derive with (old_avg * n - old + new) / n
                # We don't have the old individual value, so overwrite the running avg
                # by incorporating the new value with weight 1/n.
                factor = 1.0 / n
                entry["avg_overall_score"] = round(
                    entry["avg_overall_score"] * (1 - factor) + overall_score * factor, 2
                )
                entry["avg_positive_pct"] = round(
                    entry["avg_positive_pct"] * (1 - factor) + positive_pct * factor, 2
                )
                entry["avg_negative_pct"] = round(
                    entry["avg_negative_pct"] * (1 - factor) + negative_pct * factor, 2
                )
                entry["avg_critical_pct"] = round(
                    entry["avg_critical_pct"] * (1 - factor) + critical_pct * factor, 2
                )
                entry["avg_total_reviews"] = round(
                    entry["avg_total_reviews"] * (1 - factor) + total_reviews * factor, 2
                )
            else:
                entry["avg_overall_score"] = round(overall_score, 2)
                entry["avg_positive_pct"] = round(positive_pct, 2)
                entry["avg_negative_pct"] = round(negative_pct, 2)
                entry["avg_critical_pct"] = round(critical_pct, 2)
                entry["avg_total_reviews"] = round(float(total_reviews), 2)
        elif len(companies) < _MAX_COMPANIES:
            # New company — incremental running average.
            n = entry["company_count"]
            new_n = n + 1
            entry["avg_overall_score"] = round(
                (entry["avg_overall_score"] * n + overall_score) / new_n, 2
            )
            entry["avg_positive_pct"] = round(
                (entry["avg_positive_pct"] * n + positive_pct) / new_n, 2
            )
            entry["avg_negative_pct"] = round(
                (entry["avg_negative_pct"] * n + negative_pct) / new_n, 2
            )
            entry["avg_critical_pct"] = round(
                (entry["avg_critical_pct"] * n + critical_pct) / new_n, 2
            )
            entry["avg_total_reviews"] = round(
                (entry["avg_total_reviews"] * n + total_reviews) / new_n, 2
            )
            entry["company_count"] = new_n
            companies.append(user_hash)
            dist[_score_bucket(overall_score)] = dist.get(_score_bucket(overall_score), 0) + 1
        else:
            # Cap reached — don't add new company but still save votes.
            pass

        # Update top_category vote tally.
        if top_category:
            votes[top_category] = votes.get(top_category, 0) + 1
            entry["common_top_category"] = max(votes, key=votes.get)

        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_benchmarks(data)

    except Exception:
        pass


def get_benchmarks_for_industry(
    industry: str,
    user_overall_score: float,
    user_positive_pct: float,
    user_negative_pct: float,
    user_critical_pct: float,
) -> dict:
    """Return benchmark comparison dict for a given industry and user metrics."""
    try:
        data = _load_benchmarks()
        entry = data.get("industries", {}).get(industry)

        if not entry or entry.get("company_count", 0) < _MIN_COMPANIES:
            return {
                "available": False,
                "reason": "insufficient_data",
                "company_count": entry.get("company_count", 0) if entry else 0,
            }

        n = entry["company_count"]
        avg_score = entry["avg_overall_score"]
        avg_pos = entry["avg_positive_pct"]
        avg_neg = entry["avg_negative_pct"]
        avg_crit = entry["avg_critical_pct"]
        dist = entry.get("score_distribution", {})

        # Percentile: fraction of companies with score <= user's score.
        companies_at_or_below = sum(
            count
            for bucket, count in dist.items()
            for lo, hi in [bucket.split("-")]
            if user_overall_score >= float(lo)
        )
        # Refine: subtract companies clearly above user score based on bucket boundaries.
        score_percentile = min(100, round((companies_at_or_below / n) * 100))

        score_vs_avg = round(user_overall_score - avg_score, 2)
        pos_vs_avg = round(user_positive_pct - avg_pos, 2)
        neg_vs_avg = round(user_negative_pct - avg_neg, 2)
        crit_vs_avg = round(user_critical_pct - avg_crit, 2)

        # Pick the most actionable insight.
        abs_diffs = {
            "score": abs(score_vs_avg),
            "negative": abs(neg_vs_avg),
            "critical": abs(crit_vs_avg),
            "positive": abs(pos_vs_avg),
        }
        dominant = max(abs_diffs, key=abs_diffs.get)

        if dominant == "score":
            direction = "above" if score_vs_avg >= 0 else "below"
            insight = (
                f"Your sentiment score is {abs(score_vs_avg):.1f} points {direction} "
                f"the {industry} industry average."
            )
        elif dominant == "critical":
            if crit_vs_avg > 0:
                pct_worse = min(99, round((1 - score_percentile / 100) * 100))
                insight = (
                    f"Your critical issue rate is higher than {pct_worse}% of "
                    f"{industry} companies — prioritise urgent fixes."
                )
            else:
                insight = (
                    f"Your critical issue rate is {abs(crit_vs_avg):.1f}% lower than the "
                    f"{industry} average — strong operational performance."
                )
        elif dominant == "negative":
            if neg_vs_avg > 0:
                insight = (
                    f"Your negative review rate is {abs(neg_vs_avg):.1f}% above the "
                    f"{industry} average — investigate recurring pain points."
                )
            else:
                insight = (
                    f"Your negative review rate is {abs(neg_vs_avg):.1f}% below the "
                    f"{industry} average — customers are responding well."
                )
        else:
            if pos_vs_avg >= 0:
                insight = (
                    f"Your positive review rate is {abs(pos_vs_avg):.1f}% above the "
                    f"{industry} average — a strong customer satisfaction signal."
                )
            else:
                insight = (
                    f"Your positive review rate is {abs(pos_vs_avg):.1f}% below the "
                    f"{industry} average — focus on improving customer experience."
                )

        return {
            "available": True,
            "industry": industry,
            "company_count": n,
            "your_score": round(user_overall_score, 2),
            "industry_avg_score": avg_score,
            "score_percentile": score_percentile,
            "score_vs_avg": score_vs_avg,
            "your_positive_pct": round(user_positive_pct, 2),
            "industry_avg_positive_pct": avg_pos,
            "your_negative_pct": round(user_negative_pct, 2),
            "industry_avg_negative_pct": avg_neg,
            "your_critical_pct": round(user_critical_pct, 2),
            "industry_avg_critical_pct": avg_crit,
            "common_top_category": entry.get("common_top_category", ""),
            "score_distribution": dist,
            "insight": insight,
        }

    except Exception:
        return {"available": False, "reason": "insufficient_data", "company_count": 0}
