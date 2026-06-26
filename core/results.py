import pandas as pd


def format_aspects(aspects: list) -> str:
    if not aspects:
        return ""
    lines = []
    for a in aspects:
        emoji_map = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}
        icon = emoji_map.get(a["sentiment"], "⚪")
        lines.append(f"{icon} {a['category']} → {a['sentiment']}")
    return "\n".join(lines)


def build_results_dataframe(all_results: list, reviews: list) -> pd.DataFrame:
    review_map = {r["id"]: r["text"] for r in reviews}
    rows = []
    for result in all_results:
        rows.append({
            "ID": result["id"],
            "Review": review_map.get(result["id"], ""),
            "Sentiment": result["sentiment"],
            "Primary Category": result["primary_category"],
            "Secondary Category": result.get("secondary_category") or "—",
            "Aspect Breakdown": format_aspects(result.get("aspects", [])),
            "Urgency": result["urgency"],
            "Emotion": result["emotion"],
            "Core Issue": result["core_issue"],
            "Confidence": result["confidence"],
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("ID").reset_index(drop=True)
    return df
