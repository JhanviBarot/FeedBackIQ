"""Group classified reviews into thematic clusters per category.

Reviews are first grouped by ``Primary Category``; within each category we
run Agglomerative Clustering (cosine distance, average linkage) over sentence
embeddings of the review text to surface recurring themes. Agglomerative with
a distance threshold suits small groups of short, semantically similar reviews
far better than density-based HDBSCAN, which tends to mark such reviews as
noise. Reviews left in singleton clusters, and reviews in categories too small
to cluster, are returned as "unique".

Design guarantees:
- Critical-urgency reviews are never dropped — they always appear either in a
  cluster or in the unique list.
- For every category, the count of reviews across clusters plus unique reviews
  reconciles exactly to the category total.
- This module never raises. On any failure it returns
  ``{"available": False, "error": <message>}``.
"""

from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from core.rag.embedder import embed_texts

# Below this many total reviews, clustering adds no signal — skip entirely.
MIN_REVIEWS_FOR_CLUSTERING = 15
# A category needs at least this many reviews before we try to cluster it.
MIN_CATEGORY_SIZE = 4
# A theme needs at least this many reviews; smaller clusters dissolve to unique.
MIN_CLUSTER_SIZE = 2
# Cosine distance threshold for Agglomerative Clustering. Lower = tighter/more
# clusters, higher = looser/fewer. 0.45 best groups short, similar reviews (e.g.
# slow-delivery complaints) into a single theme without scattering them.
CLUSTER_DISTANCE_THRESHOLD = 0.45


def _critical_mask(category_df: pd.DataFrame) -> pd.Series:
    return category_df["Urgency"].astype(str).str.lower() == "critical"


def _row_to_unique(row: pd.Series) -> dict:
    return {
        "quote": row["Review"],
        "review_id": row["ID"],
        "urgency": row["Urgency"],
        "sentiment": row["Sentiment"],
    }


def _dominant_sentiment(sentiments: list) -> str:
    """Most common sentiment among a cluster's members."""
    if not sentiments:
        return "neutral"
    return Counter(s for s in sentiments).most_common(1)[0][0]


def _representative_position(positions: list, embeddings: np.ndarray,
                             candidates: list = None) -> int:
    """Row position of the member closest to the cluster's mean embedding.

    The centroid is always computed over the whole cluster, but the chosen
    representative is restricted to ``candidates`` when given — so the theme
    quote we surface matches the cluster's dominant sentiment rather than an
    off-tone outlier.
    """
    centroid = embeddings[positions].mean(axis=0)
    cand = candidates if candidates else positions
    cand_vecs = embeddings[cand]
    centroid_norm = np.linalg.norm(centroid)
    cand_norms = np.linalg.norm(cand_vecs, axis=1)
    denom = cand_norms * centroid_norm
    denom[denom == 0] = 1e-12
    sims = cand_vecs @ centroid / denom
    return cand[int(np.argmax(sims))]


def _cluster_single_category(category: str, category_df: pd.DataFrame) -> dict:
    """Cluster one category's reviews. Returns clusters + unique reviews.

    Always reconciles: len(unique) + sum(cluster sizes) == len(category_df).
    """
    from sklearn.cluster import AgglomerativeClustering

    total = len(category_df)

    # Too small to cluster meaningfully — everything is unique.
    if total < MIN_CATEGORY_SIZE:
        return {
            "category": category,
            "total": total,
            "clusters": [],
            "unique": [_row_to_unique(r) for _, r in category_df.iterrows()],
        }

    texts = category_df["Review"].fillna("").astype(str).tolist()
    embeddings = np.asarray(embed_texts(texts), dtype=float)

    clusterer = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=CLUSTER_DISTANCE_THRESHOLD,
    )
    labels = clusterer.fit_predict(embeddings)

    # Group row positions by cluster label.
    grouped = defaultdict(list)
    for pos, label in enumerate(labels):
        grouped[int(label)].append(pos)

    clusters = []
    unique = []
    for label, positions in grouped.items():
        rows = category_df.iloc[positions]
        # Dissolve singletons (below MIN_CLUSTER_SIZE) into unique reviews.
        if len(positions) < MIN_CLUSTER_SIZE:
            unique.extend(_row_to_unique(r) for _, r in rows.iterrows())
            continue
        # Representative review = the one closest to the cluster centroid, drawn
        # from the dominant-sentiment members so the quote matches the dot.
        sentiments = rows["Sentiment"].astype(str).tolist()
        dominant = _dominant_sentiment(sentiments)
        dominant_positions = [
            p for p, s in zip(positions, sentiments) if s == dominant
        ]
        rep_pos = _representative_position(positions, embeddings, dominant_positions)
        rep_row = category_df.iloc[rep_pos]
        clusters.append(
            {
                "theme_quote": rep_row["Review"],
                "count": len(positions),
                "dominant_sentiment": dominant,
                "review_ids": [r["ID"] for _, r in rows.iterrows()],
                # Internal-only: drives critical-first ordering, not part of the
                # public contract.
                "critical_count": int(_critical_mask(rows).sum()),
            }
        )

    # Sort clusters by count descending, breaking ties toward more critical.
    clusters.sort(key=lambda c: (c["count"], c["critical_count"]), reverse=True)

    return {
        "category": category,
        "total": total,
        "clusters": clusters,
        "unique": unique,
    }


def cluster_reviews_by_category(results_df: pd.DataFrame) -> dict:
    """Cluster reviews within each Primary Category using Agglomerative Clustering.

    Returns a dict. On success::

        {
            "available": True,
            "total_reviews": int,
            "categories": {
                <category name>: {
                    "total": int,
                    "clusters": [
                        {theme_quote, count, dominant_sentiment, review_ids},
                        ...
                    ],
                    "unique": [
                        {quote, review_id, urgency, sentiment}, ...
                    ],
                },
                ...
            },
        }

    On any failure (including too few reviews to bother)::

        {"available": False, "error": <message>}
    """
    try:
        if results_df is None or results_df.empty:
            return {"available": False, "error": "No reviews to cluster."}

        required = {"ID", "Review", "Primary Category", "Sentiment", "Urgency"}
        missing = required - set(results_df.columns)
        if missing:
            return {
                "available": False,
                "error": f"Missing required columns: {', '.join(sorted(missing))}",
            }

        total_reviews = len(results_df)
        if total_reviews < MIN_REVIEWS_FOR_CLUSTERING:
            return {
                "available": False,
                "error": (
                    f"Need at least {MIN_REVIEWS_FOR_CLUSTERING} reviews to "
                    f"cluster; got {total_reviews}."
                ),
            }

        categories = {}
        for category, category_df in results_df.groupby("Primary Category"):
            result = _cluster_single_category(str(category), category_df)

            # Reconciliation guard: clusters + unique must equal the total.
            clustered = sum(c["count"] for c in result["clusters"])
            accounted = clustered + len(result["unique"])
            if accounted != result["total"]:
                return {
                    "available": False,
                    "error": (
                        f"Reconciliation failed for category '{category}': "
                        f"{accounted} accounted vs {result['total']} total."
                    ),
                }

            categories[str(category)] = {
                "total": result["total"],
                "clusters": result["clusters"],
                "unique": result["unique"],
            }

        # Critical-safety guard: every critical review in the input must be
        # present somewhere in the output (clustered or unique).
        input_critical_ids = set(
            results_df.loc[_critical_mask(results_df), "ID"].tolist()
        )
        output_ids = set()
        for cat in categories.values():
            for cluster in cat["clusters"]:
                output_ids.update(cluster["review_ids"])
            output_ids.update(u["review_id"] for u in cat["unique"])
        dropped_critical = input_critical_ids - output_ids
        if dropped_critical:
            return {
                "available": False,
                "error": (
                    f"Critical reviews would be dropped: "
                    f"{sorted(dropped_critical)}."
                ),
            }

        return {
            "available": True,
            "categories": categories,
            "total_reviews": total_reviews,
        }

    except Exception as exc:  # never raises
        return {"available": False, "error": str(exc)}
