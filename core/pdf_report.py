import base64, io, os
from datetime import datetime
from typing import Optional
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

from .charts import (
    build_sentiment_donut,
    build_emotion_bar,
    build_category_bar,
    build_urgency_heatmap,
    build_aspect_summary,
)

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fig_to_base64(fig, width: int = 600, height: int = 350) -> str:
    """Render a Plotly figure to a PNG base64 string using matplotlib Agg."""
    if fig is None:
        return ""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        fig_dict = fig.to_dict()
        data = fig_dict.get("data", [])
        if not data:
            return ""

        trace = data[0]
        trace_type = trace.get("type", "scatter")

        fig_mpl, ax = plt.subplots(figsize=(width / 100, height / 100))
        fig_mpl.patch.set_facecolor("white")
        ax.set_facecolor("white")

        if trace_type == "pie":
            labels = trace.get("labels", [])
            values = list(trace.get("values", []))
            chart_colors = trace.get("marker", {}).get("colors", None)
            hole = float(trace.get("hole", 0))
            if not values or not any(v > 0 for v in values):
                values = [1]
                labels = ["No data"]
                chart_colors = ["#B5B0A3"]
            ax.pie(
                values, labels=labels, colors=chart_colors,
                autopct=lambda p: f"{p:.0f}%" if p > 5 else "",
                startangle=90, pctdistance=0.75,
                wedgeprops={"linewidth": 2, "edgecolor": "white"},
                textprops={"fontsize": 9},
            )
            if hole > 0:
                ax.add_patch(plt.Circle((0, 0), hole, color="white"))

        elif trace_type == "bar":
            orientation = trace.get("orientation", "v")
            x_vals = list(trace.get("x", []))
            y_vals = list(trace.get("y", []))
            colors_raw = trace.get("marker", {}).get("color", "#0F6E56")
            bar_colors = colors_raw if isinstance(colors_raw, list) else colors_raw
            if orientation == "h":
                bars = ax.barh(y_vals, x_vals, color=bar_colors,
                               edgecolor="white", linewidth=0.5)
                for bar, val in zip(bars, x_vals):
                    ax.text(
                        max(float(val) * 1.02, 0.1),
                        bar.get_y() + bar.get_height() / 2,
                        str(val), va="center", fontsize=7,
                    )
                ax.set_xlabel("Count", fontsize=8)
            else:
                ax.bar(x_vals, y_vals, color=bar_colors,
                       edgecolor="white", linewidth=0.5)
                ax.set_ylabel("Count", fontsize=8)
            ax.tick_params(axis="both", labelsize=7)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

        elif trace_type == "heatmap":
            z = trace.get("z", [[1]])
            x_labels = trace.get("x", ["Critical", "Medium", "Low"])
            y_labels = trace.get("y", [])
            z_array = np.array(z, dtype=float)
            ax.imshow(z_array, cmap="RdYlGn_r", aspect="auto",
                      vmin=0, vmax=max(float(z_array.max()), 1))
            if x_labels:
                ax.set_xticks(range(len(x_labels)))
                ax.set_xticklabels(x_labels, fontsize=8)
            if y_labels:
                ax.set_yticks(range(len(y_labels)))
                ax.set_yticklabels(y_labels, fontsize=7)
            for i in range(len(z_array)):
                for j in range(len(z_array[i])):
                    val = int(z_array[i][j])
                    tc = "white" if val > float(z_array.max()) * 0.6 else "black"
                    ax.text(j, i, str(val), ha="center", va="center",
                            fontsize=10, color=tc, fontweight="bold")
        else:
            ax.text(0.5, 0.5, f"Chart ({trace_type})", ha="center", va="center",
                    transform=ax.transAxes, fontsize=10, color="gray")

        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        fig_mpl.savefig(buf, format="png", dpi=100,
                        bbox_inches="tight", facecolor="white")
        plt.close(fig_mpl)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    except Exception:
        return ""


def _health_colour(score: int) -> str:
    """Return a hex colour string based on health score thresholds."""
    if score >= 75:
        return "#27AE60"
    if score >= 25:
        return "#E67E22"
    return "#C0392B"


def _truncate(text: str, length: int) -> str:
    if not text:
        return ""
    s = str(text)
    if len(s) <= length:
        return s
    return s[:length] + "…"


def _score_colour(score: int) -> str:
    if score >= 75:
        return "#27AE60"
    if score >= 50:
        return "#E67E22"
    return "#C0392B"


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_pdf(
    dashboard_data: dict,
    action_plan: dict,
    profile: dict,
    results_df: pd.DataFrame,
) -> bytes:
    """Build the complete PDF and return it as bytes. Raises RuntimeError on failure."""
    try:
        has_action_plan = bool(action_plan.get("success") and action_plan.get("result"))
        health_score = int(action_plan.get("health_score", 0))
        health_label = action_plan.get("health_label", "—")
        result = action_plan.get("result") or {}

        sentiment = dashboard_data.get("sentiment", {})
        overall_score = int(sentiment.get("overall_score", 0))

        context = {
            "profile": profile,
            "dashboard_data": dashboard_data,
            "has_action_plan": has_action_plan,
            "health_score": health_score,
            "health_label": health_label,
            "health_colour": _health_colour(health_score),
            "generated_date": datetime.now().strftime("%d %B %Y"),
            "positive_pct": sentiment.get("positive_pct", 0.0),
            "negative_pct": sentiment.get("negative_pct", 0.0),
            "neutral_pct": sentiment.get("neutral_pct", 0.0),
            "overall_score": overall_score,
            "score_colour": _score_colour(overall_score),
            "critical_count": dashboard_data.get("urgency", {}).get("critical_count", 0),
            "top_category": str(dashboard_data.get("top_category", "—")),
            "categories": dashboard_data.get("categories", []),
            "top_issues": dashboard_data.get("top_issues", []),
            "emotions": dashboard_data.get("emotions", []),
            "urgency": dashboard_data.get("urgency", {}),
            "multi_aspect": dashboard_data.get("multi_aspect", {}),
            "total_reviews": dashboard_data.get("total_reviews", 0),
            "rows": results_df.head(200).to_dict("records"),
            "total_rows": len(results_df),
            "chart_sentiment": _fig_to_base64(
                build_sentiment_donut(sentiment), 500, 350),
            "chart_emotion": _fig_to_base64(
                build_emotion_bar(dashboard_data.get("emotions", [])), 500, 350),
            "chart_category": _fig_to_base64(
                build_category_bar(dashboard_data.get("categories", [])), 900, 320),
            "chart_heatmap": _fig_to_base64(
                build_urgency_heatmap(dashboard_data.get("urgency_matrix")), 900, 300),
            "chart_aspect": _fig_to_base64(
                build_aspect_summary(results_df), 500, 200),
            "recommendations": sorted(
                result.get("recommendations", []),
                key=lambda r: r.get("rank", 99),
            ),
            "quick_win": result.get("quick_win"),
            "key_strengths": result.get("key_strengths", []),
            "executive_summary": result.get("executive_summary", ""),
            "data_quality_note": result.get("data_quality_note"),
        }

        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        template = env.get_template("pdf_report.html")
        html_content = template.render(**context)

        buf = io.BytesIO()
        pisa_result = pisa.CreatePDF(html_content, dest=buf, encoding="utf-8")

        if pisa_result.err:
            raise RuntimeError(f"xhtml2pdf error code: {pisa_result.err}")

        pdf_bytes = buf.getvalue()
        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
            raise RuntimeError("PDF generation produced invalid output")

        return pdf_bytes

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}") from e
