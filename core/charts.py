import plotly.graph_objects as go

COLOR_POSITIVE = "#0F6E56"
COLOR_NEGATIVE = "#C0392B"
COLOR_NEUTRAL = "#B5B0A3"

EMOTION_COLORS = {
    "happy": "#0F6E56",
    "satisfied": "#3FA88A",
    "surprised": "#D8A33D",
    "neutral": "#B5B0A3",
    "confused": "#8E7CC3",
    "disappointed": "#C97A3D",
    "frustrated": "#C0392B",
    "angry": "#8B1E1E",
}


def build_sentiment_donut(sentiment_data: dict) -> go.Figure:
    labels = ["Positive", "Negative", "Neutral"]
    values = [
        sentiment_data["positive_count"],
        sentiment_data["negative_count"],
        sentiment_data["neutral_count"],
    ]
    colors = [COLOR_POSITIVE, COLOR_NEGATIVE, COLOR_NEUTRAL]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                textinfo="label+percent",
                textfont=dict(size=13),
                hovertemplate="%{label}: %{value} reviews (%{percent})<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
        height=320,
        annotations=[
            dict(
                text=f"{sentiment_data['positive_pct']}%<br>Positive",
                x=0.5,
                y=0.5,
                font=dict(size=16, color="#1A1A1A"),
                showarrow=False,
            )
        ],
    )

    return fig


def build_emotion_bar(emotion_data: list) -> go.Figure:
    emotions = [e["emotion"] for e in emotion_data]
    counts = [e["count"] for e in emotion_data]
    colors = [EMOTION_COLORS.get(e, "#B5B0A3") for e in emotions]
    labels = [e.capitalize() for e in emotions]

    fig = go.Figure(
        data=[
            go.Bar(
                x=counts,
                y=labels,
                orientation="h",
                marker=dict(color=colors),
                text=counts,
                textposition="outside",
                hovertemplate="%{y}: %{x} reviews<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=10, r=30, t=30, b=10),
        height=320,
        xaxis=dict(title=None, showgrid=True, gridcolor="#EEEEEA"),
        yaxis=dict(title=None, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig

def build_category_bar(category_data: list) -> go.Figure:
    categories = [c["category"] for c in category_data]
    counts = [c["count"] for c in category_data]

    fig = go.Figure(
        data=[
            go.Bar(
                x=counts,
                y=categories,
                orientation="h",
                marker=dict(color="#0F6E56"),
                text=counts,
                textposition="outside",
                hovertemplate="%{y}: %{x} reviews<extra></extra>",
            )
        ]
    )

    chart_height = max(280, 40 * len(categories))

    fig.update_layout(
        margin=dict(l=10, r=30, t=30, b=10),
        height=chart_height,
        xaxis=dict(title=None, showgrid=True, gridcolor="#EEEEEA"),
        yaxis=dict(title=None, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def build_urgency_heatmap(urgency_matrix) -> go.Figure:
    import pandas as _pd
    if urgency_matrix is None or not isinstance(urgency_matrix, _pd.DataFrame) or urgency_matrix.empty:
        return None
    # Ensure required columns exist (guards against deserialization edge cases)
    for level in ["critical", "medium", "low"]:
        if level not in urgency_matrix.columns:
            urgency_matrix = urgency_matrix.copy()
            urgency_matrix[level] = 0
    categories = urgency_matrix.index.tolist()
    urgency_levels = ["critical", "medium", "low"]
    z_values = urgency_matrix[urgency_levels].values

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=["Critical", "Medium", "Low"],
            y=categories,
            colorscale=[[0.0, "#FAFAF8"], [0.5, "#E8B4A8"], [1.0, "#8B1E1E"]],
            text=z_values,
            texttemplate="%{text}",
            textfont=dict(size=13),
            hovertemplate="%{y} — %{x}: %{z} reviews<extra></extra>",
            showscale=False,
            xgap=3,
            ygap=3,
        )
    )

    chart_height = max(280, 45 * len(categories))

    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=chart_height,
        xaxis=dict(side="top", title=None),
        yaxis=dict(title=None, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig

def build_aspect_summary(df) -> go.Figure:
    multi_count = int((df["Secondary Category"] != "—").sum())
    single_count = len(df) - multi_count

    fig = go.Figure(
        data=[
            go.Bar(
                x=[single_count, multi_count],
                y=["Single-issue reviews", "Multi-issue reviews"],
                orientation="h",
                marker=dict(color=["#B5B0A3", "#0F6E56"]),
                text=[single_count, multi_count],
                textposition="outside",
                hovertemplate="%{y}: %{x} reviews<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=10, r=30, t=10, b=10),
        height=140,
        xaxis=dict(title=None, showgrid=True, gridcolor="#EEEEEA"),
        yaxis=dict(title=None),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig