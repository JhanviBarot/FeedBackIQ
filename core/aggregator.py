import pandas as pd
from collections import Counter


def compute_sentiment_breakdown(df: pd.DataFrame) -> dict:
    total = len(df)
    counts = df["Sentiment"].value_counts().to_dict()

    positive = counts.get("positive", 0)
    negative = counts.get("negative", 0)
    neutral = counts.get("neutral", 0)

    return {
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral,
        "positive_pct": round((positive / total) * 100, 1) if total else 0,
        "negative_pct": round((negative / total) * 100, 1) if total else 0,
        "neutral_pct": round((neutral / total) * 100, 1) if total else 0,
        "overall_score": round(((positive - negative) / total) * 100 + 50, 1)
        if total
        else 0,
    }


def compute_category_breakdown(df: pd.DataFrame) -> list:
    counts = df["Primary Category"].value_counts()
    total = len(df)

    breakdown = []
    for category, count in counts.items():
        breakdown.append(
            {
                "category": category,
                "count": int(count),
                "pct": round((count / total) * 100, 1) if total else 0,
            }
        )

    return sorted(breakdown, key=lambda x: x["count"], reverse=True)


def compute_urgency_breakdown(df: pd.DataFrame) -> dict:
    counts = df["Urgency"].value_counts().to_dict()
    total = len(df)

    critical = counts.get("critical", 0)
    medium = counts.get("medium", 0)
    low = counts.get("low", 0)

    return {
        "critical_count": critical,
        "medium_count": medium,
        "low_count": low,
        "critical_pct": round((critical / total) * 100, 1) if total else 0,
    }


def compute_urgency_category_matrix(df: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.crosstab(df["Primary Category"], df["Urgency"])

    for level in ["critical", "medium", "low"]:
        if level not in matrix.columns:
            matrix[level] = 0

    matrix = matrix[["critical", "medium", "low"]]
    matrix = matrix.sort_values("critical", ascending=False)

    return matrix


def compute_emotion_breakdown(df: pd.DataFrame) -> list:
    counts = df["Emotion"].value_counts()
    total = len(df)

    breakdown = []
    for emotion, count in counts.items():
        breakdown.append(
            {
                "emotion": emotion,
                "count": int(count),
                "pct": round((count / total) * 100, 1) if total else 0,
            }
        )

    return sorted(breakdown, key=lambda x: x["count"], reverse=True)


def compute_multi_aspect_stats(df: pd.DataFrame) -> dict:
    total = len(df)
    multi_aspect = int((df["Secondary Category"] != "—").sum())

    return {
        "multi_aspect_count": multi_aspect,
        "multi_aspect_pct": round((multi_aspect / total) * 100, 1) if total else 0,
        "single_aspect_count": total - multi_aspect,
    }


def compute_top_issues(df: pd.DataFrame, top_n: int = 5) -> list:
    negative_df = df[df["Sentiment"] == "negative"]

    if negative_df.empty:
        return []

    grouped = (
        negative_df.groupby("Primary Category")
        .agg(
            count=("Primary Category", "count"),
            critical_count=("Urgency", lambda x: (x == "critical").sum()),
            example=("Core Issue", "first"),
            example_list=("Core Issue", lambda x: list(x)[:3]),
        )
        .reset_index()
        .rename(columns={"Primary Category": "category"})
    )

    grouped = grouped.sort_values(
        by=["critical_count", "count"], ascending=[False, False]
    )

    top = grouped.head(top_n)

    return [
        {
            "category": row["category"],
            "count": int(row["count"]),
            "critical_count": int(row["critical_count"]),
            # `example` stays a string for backward compatibility (PDF, frontend).
            # `example_list` is additive: up to 3 distinct complaints for richer RAG retrieval.
            "example": row["example"],
            "example_list": list(row["example_list"]),
        }
        for _, row in top.iterrows()
    ]
def compute_confidence_breakdown(df: pd.DataFrame) -> dict:
    counts = df["Confidence"].value_counts().to_dict()
    total = len(df)

    low = counts.get("low", 0)

    return {
        "high_count": counts.get("high", 0),
        "medium_count": counts.get("medium", 0),
        "low_count": low,
        "low_pct": round((low / total) * 100, 1) if total else 0,
    }


def get_top_category(df: pd.DataFrame) -> str:
    if df.empty:
        return "—"
    return df["Primary Category"].value_counts().idxmax()


def build_dashboard_data(df: pd.DataFrame) -> dict:
    sentiment = compute_sentiment_breakdown(df)
    urgency = compute_urgency_breakdown(df)
    confidence = compute_confidence_breakdown(df)

    return {
        "total_reviews": len(df),
        "sentiment": sentiment,
        "categories": compute_category_breakdown(df),
        "urgency": urgency,
        "urgency_matrix": compute_urgency_category_matrix(df),
        "emotions": compute_emotion_breakdown(df),
        "multi_aspect": compute_multi_aspect_stats(df),
        "top_issues": compute_top_issues(df),
        "confidence": confidence,
        "top_category": get_top_category(df),
        "health_score_inputs": {
            "positive_pct": sentiment["positive_pct"],
            "critical_pct": urgency["critical_pct"],
            "low_confidence_pct": confidence["low_pct"],
        },
    }
