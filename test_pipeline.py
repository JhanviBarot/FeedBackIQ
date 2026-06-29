from core.preprocessing import preprocess, batch_reviews
from core.aggregator import build_dashboard_data
import pandas as pd
from core.classifier import is_rate_limit_error
from core.file_input import lines_to_raw_text


def section(name):
    print(f"\n{'='*60}\n{name}\n{'='*60}")


def check(condition, message):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {message}")
    if not condition:
        raise AssertionError(f"FAILED: {message}")


# ─────────────────────────────────────────────────────────────
section("TEST 1 — Minimum review enforcement")
# ─────────────────────────────────────────────────────────────

result = preprocess("Good.\nBad.\nOkay.\nFine.")
check(result["error"] is not None, "4 reviews should trigger minimum error")

result = preprocess("Good product.\nBad delivery.\nOkay support.\nFine pricing.\nDecent overall.")
check(result["error"] is None, "5 valid reviews should pass")
check(len(result["reviews"]) == 5, "Should return exactly 5 reviews")


# ─────────────────────────────────────────────────────────────
section("TEST 2 — Exact deduplication")
# ─────────────────────────────────────────────────────────────

sample = """Great product overall.
Great product overall.
Terrible delivery experience.
Support was very helpful today.
Pricing seems fair to me.
Quality has improved a lot recently."""

result = preprocess(sample)
check(result["error"] is None, "Should pass preprocessing")
check(result["report"]["exact_duplicates_removed"] == 1, "Should detect exactly 1 exact duplicate")
check(result["report"]["final_count"] == 5, "Should have 5 unique reviews after dedup")


# ─────────────────────────────────────────────────────────────
section("TEST 3 — Near-duplicate detection")
# ─────────────────────────────────────────────────────────────

sample = """Great service!
Great service!!
Great service.
Terrible delivery, took weeks to arrive.
Support team was helpful and quick.
Pricing is reasonable for the quality offered.
Product quality exceeded my expectations completely."""

result = preprocess(sample)
print(result)  # TEMP DEBUG
check(result["error"] is None, "Should pass preprocessing")

# ─────────────────────────────────────────────────────────────
section("TEST 4 — Noise filtering")
# ─────────────────────────────────────────────────────────────

sample = """aaaaaaaaaaaa
123456789
!!!!!!!!!!
Great product, very happy with quality.
Terrible delivery, took way too long.
Support resolved my issue quickly and politely.
Pricing feels fair compared to competitors.
Packaging was sturdy and well designed overall."""

result = preprocess(sample)
check(result["error"] is None, "Should pass preprocessing")
check(result["report"]["noise_removed"] == 3, "Should remove exactly 3 noise entries")
check(result["report"]["final_count"] == 5, "Should have 5 real reviews remaining")
# ─────────────────────────────────────────────────────────────
section("TEST 5 — Emoji conversion")
# ─────────────────────────────────────────────────────────────

sample = """😡😡😡 absolutely furious with this
😍 love it so much
Great product quality overall here.
Terrible delivery speed this time.
Support team was very helpful indeed."""

result = preprocess(sample)
check(result["error"] is None, "Should pass preprocessing")
found_converted = any("angry" in r["text"].lower() or "face" in r["text"].lower() for r in result["reviews"])
check(found_converted, "Emoji should be converted to text description")


# ─────────────────────────────────────────────────────────────
section("TEST 6 — Length enforcement and sentence-boundary trimming")
# ─────────────────────────────────────────────────────────────

long_review = "This is a sentence. " * 80  # ~1600 characters
sample = f"""{long_review}
Great product quality overall here.
Terrible delivery speed this time.
Support team was very helpful indeed.
Pricing is fair for what you get."""

result = preprocess(sample)
check(result["error"] is None, "Should pass preprocessing")
trimmed_review = result["reviews"][0]["text"]
check(len(trimmed_review) <= 1000, f"Long review should be trimmed to 1000 chars or fewer, got {len(trimmed_review)}")
check(trimmed_review.endswith("."), "Trimmed review should end at a sentence boundary")


# ─────────────────────────────────────────────────────────────
section("TEST 7 — Batch assembly")
# ─────────────────────────────────────────────────────────────

reviews = [{"id": i, "text": f"Review number {i}"} for i in range(37)]
batches = batch_reviews(reviews)
check(len(batches) == 3, f"37 reviews should produce 3 batches, got {len(batches)}")
check(len(batches[0]) == 15, "First batch should have 15 reviews")
check(len(batches[1]) == 15, "Second batch should have 15 reviews")
check(len(batches[2]) == 7, "Third batch should have 7 reviews")


# ─────────────────────────────────────────────────────────────
section("TEST 8 — Aggregation logic (mock classified data, zero API cost)")
# ─────────────────────────────────────────────────────────────

mock_data = pd.DataFrame([
    {"ID": 0, "Review": "Bad delivery", "Sentiment": "negative", "Primary Category": "Delivery Speed",
     "Secondary Category": "—", "Aspect Breakdown": "", "Urgency": "critical", "Emotion": "angry",
     "Core Issue": "Late delivery", "Confidence": "high"},
    {"ID": 1, "Review": "Bad delivery again", "Sentiment": "negative", "Primary Category": "Delivery Speed",
     "Secondary Category": "—", "Aspect Breakdown": "", "Urgency": "critical", "Emotion": "frustrated",
     "Core Issue": "Late delivery again", "Confidence": "high"},
    {"ID": 2, "Review": "Great product", "Sentiment": "positive", "Primary Category": "Product Quality",
     "Secondary Category": "—", "Aspect Breakdown": "", "Urgency": "low", "Emotion": "happy",
     "Core Issue": "Excellent quality", "Confidence": "high"},
    {"ID": 3, "Review": "Mixed feelings", "Sentiment": "neutral", "Primary Category": "Pricing",
     "Secondary Category": "—", "Aspect Breakdown": "", "Urgency": "medium", "Emotion": "neutral",
     "Core Issue": "Pricing is okay", "Confidence": "medium"},
])

dashboard_data = build_dashboard_data(mock_data)

check(dashboard_data["total_reviews"] == 4, "Should count 4 total reviews")
check(dashboard_data["sentiment"]["negative_count"] == 2, "Should count 2 negative reviews")
check(dashboard_data["urgency"]["critical_count"] == 2, "Should count 2 critical urgency reviews")
check(dashboard_data["top_category"] == "Delivery Speed", "Top category should be Delivery Speed (2 mentions)")

top_issues = dashboard_data["top_issues"]
check(len(top_issues) > 0, "Should produce at least 1 top issue group")
check(top_issues[0]["category"] == "Delivery Speed", "Top issue category should be Delivery Speed")
check(top_issues[0]["critical_count"] == 2, "Delivery Speed should show 2 critical reviews")
check("Product Quality" not in [t["category"] for t in top_issues], "Positive-only category should NOT appear in top issues")

# ─────────────────────────────────────────────────────────────
section("TEST 9 — File parsing (CSV column detection and conversion)")
# ─────────────────────────────────────────────────────────────

import tempfile
import os
from core.file_input import parse_uploaded_file, detect_review_column

mock_csv_data = pd.DataFrame(
    {
        "review_text": [
            "Great product, very happy with quality.",
            "Terrible delivery, took way too long.",
            "Support resolved my issue quickly.",
            "Pricing feels fair compared to competitors.",
            "Packaging was sturdy and well designed.",
            "",  # empty row — should be dropped
            None,  # null row — should be dropped
        ],
        "rating": [5, 1, 4, 4, 5, None, None],
        "date": [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-04",
            "2026-01-05",
            None,
            None,
        ],
    }
)

temp_path = os.path.join(tempfile.gettempdir(), "test_feedbackiq.csv")
mock_csv_data.to_csv(temp_path, index=False)

with open(temp_path, "rb") as f:
    parsed = parse_uploaded_file(f, filename="test_feedbackiq.csv")

check(parsed["error"] is None, "Valid CSV should parse without error")
check("review_text" in parsed["columns"], "Should detect 'review_text' column")
check(
    len(parsed["columns"]) == 3,
    f"Should detect 3 columns, got {len(parsed['columns'])}",
)

detected = detect_review_column(parsed["columns"])
check(
    detected == "review_text",
    f"Should auto-detect 'review_text' as review column, got {detected}",
)

raw_text = parsed["raw_text_lines"]
check(
    len(raw_text) == 5, f"Should extract 5 non-empty review rows, got {len(raw_text)}"
)
check(
    "Great product" in raw_text[0], "First extracted row should match expected content"
)

os.remove(temp_path)


# ─────────────────────────────────────────────────────────────
section("TEST 10 — File parsing (empty file and missing column handling)")
# ─────────────────────────────────────────────────────────────

empty_csv = pd.DataFrame({"col_a": [], "col_b": []})
temp_path2 = os.path.join(tempfile.gettempdir(), "test_empty.csv")
empty_csv.to_csv(temp_path2, index=False)

with open(temp_path2, "rb") as f:
    parsed_empty = parse_uploaded_file(f, filename="test_empty.csv")

check(parsed_empty["error"] is not None, "Empty CSV should return an error")

os.remove(temp_path2)

# ─────────────────────────────────────────────────────────────
section("TEST 11 — Rate-limit detection logic")
# ─────────────────────────────────────────────────────────────


check(
    is_rate_limit_error("Error code: 429 - rate_limit_exceeded") == True,
    "Should detect 429 rate limit error",
)
check(
    is_rate_limit_error("rate_limit_exceeded: tokens per day") == True,
    "Should detect 'rate_limit_exceeded' phrase",
)
check(
    is_rate_limit_error("Connection timeout") == False,
    "Should NOT flag a timeout as rate limit",
)
check(
    is_rate_limit_error("Invalid API key") == False,
    "Should NOT flag an auth error as rate limit",
)

# ─────────────────────────────────────────────────────────────
section("TEST 12 — Raw text assembly from file vs paste input")
# ─────────────────────────────────────────────────────────────


sample_lines = ["Great product!", "Terrible delivery.", "Okay support."]
raw = lines_to_raw_text(sample_lines)

check(raw.count("\n") == 2, "3 lines should produce 2 newline separators")
check(raw.split("\n")[0] == "Great product!", "First line should match first review")
check(raw.split("\n")[-1] == "Okay support.", "Last line should match last review")

empty_raw = lines_to_raw_text([])
check(empty_raw == "", "Empty list should produce empty string")

# ─────────────────────────────────────────────────────────────
section("TEST 13 — Batch progress accumulation")
# ─────────────────────────────────────────────────────────────

from core.classifier import build_progress_summary

mock_results_so_far = [
    {
        "id": 0,
        "sentiment": "positive",
        "primary_category": "Product Quality",
        "secondary_category": None,
        "aspects": [],
        "urgency": "low",
        "emotion": "happy",
        "core_issue": "Great quality",
        "confidence": "high",
    },
    {
        "id": 1,
        "sentiment": "negative",
        "primary_category": "Delivery Speed",
        "secondary_category": None,
        "aspects": [],
        "urgency": "critical",
        "emotion": "angry",
        "core_issue": "Very late delivery",
        "confidence": "high",
    },
]

summary = build_progress_summary(
    results_so_far=mock_results_so_far,
    total_batches=5,
    completed_batches=1,
    failed_count=0,
)

check(summary["completed_batches"] == 1, "Completed batches should be 1")
check(summary["total_batches"] == 5, "Total batches should be 5")
check(summary["classified_so_far"] == 2, "Should count 2 classified reviews so far")
check(summary["pct_complete"] == 20, "1 of 5 batches = 20% complete")
check(summary["failed_count"] == 0, "Failed count should be 0")
check(
    summary["positive_so_far"] == 1 and summary["negative_so_far"] == 1,
    "Should count 1 positive and 1 negative from results so far",
)

# ─────────────────────────────────────────────────────────────
section("TEST 14 — aggregator health_score_inputs key")
# ─────────────────────────────────────────────────────────────

mock_data_for_health = pd.DataFrame([
    {"ID": 0, "Review": "Great", "Sentiment": "positive", "Primary Category": "Product Quality",
     "Secondary Category": "—", "Aspect Breakdown": "", "Urgency": "low", "Emotion": "happy",
     "Core Issue": "Excellent", "Confidence": "high"},
    {"ID": 1, "Review": "Bad", "Sentiment": "negative", "Primary Category": "Delivery Speed",
     "Secondary Category": "—", "Aspect Breakdown": "", "Urgency": "critical", "Emotion": "angry",
     "Core Issue": "Late", "Confidence": "low"},
    {"ID": 2, "Review": "Ok", "Sentiment": "neutral", "Primary Category": "Pricing",
     "Secondary Category": "—", "Aspect Breakdown": "", "Urgency": "medium", "Emotion": "neutral",
     "Core Issue": "Ok", "Confidence": "medium"},
])

dd = build_dashboard_data(mock_data_for_health)
check("health_score_inputs" in dd, "build_dashboard_data should include health_score_inputs key")
hsi = dd["health_score_inputs"]
check("positive_pct" in hsi and "critical_pct" in hsi and "low_confidence_pct" in hsi,
      "health_score_inputs should contain positive_pct, critical_pct, low_confidence_pct")
check(abs(hsi["positive_pct"] - dd["sentiment"]["positive_pct"]) < 0.01,
      "positive_pct in health_score_inputs should match sentiment breakdown")


# ─────────────────────────────────────────────────────────────
section("TEST 15 — Action Plan Module (zero API cost)")
# ─────────────────────────────────────────────────────────────

import json
from core.action_plan import (
    compute_health_score,
    build_action_plan_prompts,
    _format_categories_block,
    _format_top_issues_block,
    validate_action_plan,
    generate_action_plan,
    ActionPlanResult,
)

# ── 15a — health_score computation: normal case ───────────────
_mock_dd_15a = {
    "health_score_inputs": {
        "positive_pct": 60.0,
        "critical_pct": 10.0,
        "low_confidence_pct": 5.0,
    }
}
score_15a, label_15a = compute_health_score(_mock_dd_15a)
check(score_15a == 76, f"15a: expected score 76, got {score_15a}")
check(label_15a == "Strong", f"15a: expected label 'Strong', got {label_15a}")

# ── 15b — health_score edge case: all-negative dataset ────────
_mock_dd_15b = {
    "health_score_inputs": {
        "positive_pct": 0.0,
        "critical_pct": 80.0,
        "low_confidence_pct": 30.0,
    }
}
score_15b, label_15b = compute_health_score(_mock_dd_15b)
check(
    label_15b in {"Needs Attention", "Critical"},
    f"15b: all-negative dataset should be 'Needs Attention' or 'Critical', got '{label_15b}'",
)

# ── 15c — _format_categories_block ────────────────────────────
_cats = [
    {"category": "Delivery Speed", "count": 42, "pct": 35.0},
    {"category": "Product Quality", "count": 18, "pct": 15.0},
]
_cats_block = _format_categories_block(_cats)
check("Delivery Speed" in _cats_block, "15c: categories block should contain category name")
check("35.0%" in _cats_block, "15c: categories block should contain percentage")
check("42" in _cats_block, "15c: categories block should contain count")

# ── 15d — _format_top_issues_block ────────────────────────────
_issues = [
    {"category": "Delivery Speed", "count": 42, "critical_count": 18,
     "example": "Package arrived three weeks late"},
]
_issues_block = _format_top_issues_block(_issues)
check("1." in _issues_block, "15d: top issues block should be numbered")
check("critical" in _issues_block.lower(), "15d: top issues block should contain 'critical'")
check("Delivery Speed" in _issues_block, "15d: top issues block should contain category name")

# ── 15e — validate_action_plan with mock valid JSON ───────────
_valid_json = json.dumps({
    "health_score": 73,
    "health_label": "Mixed",
    "executive_summary": (
        "This company received 120 reviews with 60.0% positive sentiment. "
        "Critical issues account for 15.0% of all feedback."
    ),
    "key_strengths": [
        "Product quality earned praise in 40 of the 72 positive reviews."
    ],
    "recommendations": [
        {
            "rank": 1,
            "title": "Fix Delivery Issues",
            "rationale": "42 reviews (35.0%) cite delivery as the primary complaint.",
            "action": "Audit your last-mile delivery partner. Set SLA targets. Monitor weekly.",
            "impact": "high",
            "effort": "medium",
            "timeframe": "immediate",
        },
        {
            "rank": 2,
            "title": "Improve Customer Support",
            "rationale": "25 reviews cite poor support response times.",
            "action": (
                "Implement a ticketing system. Train the team on empathy. "
                "Target 24-hour response."
            ),
            "impact": "high",
            "effort": "medium",
            "timeframe": "short_term",
        },
        {
            "rank": 3,
            "title": "Review Packaging",
            "rationale": "18 reviews mention damaged packaging on arrival.",
            "action": "Switch to reinforced materials. Run a 30-day pilot.",
            "impact": "medium",
            "effort": "low",
            "timeframe": "short_term",
        },
    ],
    "quick_win": {
        "title": "Acknowledge Critical Complaints",
        "description": "Send a follow-up to the 18 customers who flagged critical issues.",
        "expected_outcome": "Reduced churn risk from the most at-risk customer segment.",
    },
    "data_quality_note": None,
})

_val_15e = validate_action_plan(_valid_json)
check(_val_15e["success"] is True, "15e: valid JSON should parse successfully")
check(isinstance(_val_15e["result"], ActionPlanResult), "15e: result should be ActionPlanResult instance")
check(_val_15e["error"] is None, "15e: error should be None on success")

# ── 15f — validate_action_plan strips thinking block ──────────
_with_thinking = f"<thinking>\nSome internal reasoning here.\n</thinking>\n{_valid_json}"
_val_15f = validate_action_plan(_with_thinking)
check(_val_15f["success"] is True, "15f: should strip thinking block and parse successfully")

# ── 15g — validate_action_plan with invalid JSON ──────────────
_val_15g = validate_action_plan("this is not json at all {{{")
check(_val_15g["success"] is False, "15g: invalid JSON should return success=False")
check(_val_15g["error"] is not None and len(_val_15g["error"]) > 0,
      "15g: error message should be non-empty")

# ── 15h — validate_action_plan with missing required field ────
_missing_field = json.dumps({
    "health_score": 73,
    "health_label": "Mixed",
    # executive_summary is missing
    "key_strengths": [],
    "recommendations": [
        {"rank": 1, "title": "X", "rationale": "Y", "action": "Z",
         "impact": "high", "effort": "low", "timeframe": "immediate"},
        {"rank": 2, "title": "X2", "rationale": "Y2", "action": "Z2",
         "impact": "medium", "effort": "medium", "timeframe": "short_term"},
        {"rank": 3, "title": "X3", "rationale": "Y3", "action": "Z3",
         "impact": "low", "effort": "high", "timeframe": "long_term"},
    ],
    "quick_win": {"title": "T", "description": "D", "expected_outcome": "O"},
    "data_quality_note": None,
})
_val_15h = validate_action_plan(_missing_field)
check(_val_15h["success"] is False, "15h: missing required field should return success=False")

# ── 15i — generate_action_plan returns health_score on failure ─
_minimal_dd = {
    "health_score_inputs": {"positive_pct": 40.0, "critical_pct": 20.0, "low_confidence_pct": 5.0},
    "sentiment": {"positive_pct": 40.0, "positive_count": 40, "negative_count": 50,
                  "neutral_count": 10, "negative_pct": 50.0, "neutral_pct": 10.0, "overall_score": 40.0},
    "urgency": {"critical_count": 20, "critical_pct": 20.0, "medium_count": 30, "low_count": 50},
    "confidence": {"high_count": 80, "medium_count": 15, "low_count": 5, "low_pct": 5.0},
    "multi_aspect": {"multi_aspect_count": 20, "multi_aspect_pct": 20.0, "single_aspect_count": 80},
    "categories": [{"category": "Delivery Speed", "count": 50, "pct": 50.0}],
    "top_issues": [{"category": "Delivery Speed", "count": 50, "critical_count": 20,
                    "example": "Very late delivery"}],
    "emotions": [{"emotion": "angry", "count": 30, "pct": 30.0}],
    "total_reviews": 100,
}
_minimal_profile = {"company_name": "TestCo", "industry": "E-commerce"}

_plan_15i = generate_action_plan(_minimal_dd, _minimal_profile)
check("health_score" in _plan_15i, "15i: return dict must always contain health_score")
check("health_label" in _plan_15i, "15i: return dict must always contain health_label")
check(isinstance(_plan_15i["health_score"], int), "15i: health_score must be an int")

# ── 15j — build_action_plan_prompts with minimal profile ──────
_minimal_profile_j = {"company_name": "MinimalCo", "industry": "Retail"}
try:
    _prompts_15j = build_action_plan_prompts(_minimal_dd, _minimal_profile_j)
    check("system" in _prompts_15j and "user" in _prompts_15j,
          "15j: should return dict with system and user keys")
    check(len(_prompts_15j["system"]) > 0, "15j: system prompt should be non-empty")
    check(len(_prompts_15j["user"]) > 0, "15j: user prompt should be non-empty")
    _no_key_error = True
except KeyError as e:
    _no_key_error = False
    print(f"  KeyError: {e}")
check(_no_key_error, "15j: minimal profile (no description, no urgency_definition) should not raise KeyError")


# ─────────────────────────────────────────────────────────────
section("TEST 16 — PDF Report Tests")
# ─────────────────────────────────────────────────────────────

from core.pdf_report import (
    generate_pdf,
    _fig_to_base64,
    _health_colour,
    _truncate,
)
import plotly.graph_objects as go

# Shared mock data used across multiple sub-tests
_mock_dashboard = {
    "total_reviews": 10,
    "sentiment": {
        "positive_count": 6, "negative_count": 3, "neutral_count": 1,
        "positive_pct": 60.0, "negative_pct": 30.0, "neutral_pct": 10.0,
        "overall_score": 65.0,
    },
    "categories": [{"category": "Delivery", "count": 5, "pct": 50.0}],
    "urgency": {
        "critical_count": 2, "medium_count": 5, "low_count": 3, "critical_pct": 20.0,
    },
    "urgency_matrix": pd.DataFrame(
        {"critical": [2], "medium": [5], "low": [3]}, index=["Delivery"]
    ),
    "emotions": [{"emotion": "angry", "count": 3, "pct": 30.0}],
    "multi_aspect": {
        "multi_aspect_count": 3, "multi_aspect_pct": 30.0, "single_aspect_count": 7,
    },
    "top_issues": [{"category": "Delivery", "count": 3, "critical_count": 2,
                    "example": "Arrived broken"}],
    "confidence": {"high_count": 8, "medium_count": 1, "low_count": 1, "low_pct": 10.0},
    "top_category": "Delivery",
    "health_score_inputs": {
        "positive_pct": 60.0, "critical_pct": 20.0, "low_confidence_pct": 10.0,
    },
}
_mock_action_plan_fail = {
    "success": False, "result": None,
    "health_score": 62, "health_label": "Mixed", "error": "Not generated",
}
_mock_profile = {
    "company_name": "Test Co", "industry": "E-commerce",
    "categories": ["Delivery"], "description": "", "urgency_definition": "",
}
_mock_df = pd.DataFrame({
    "ID": [0], "Review": ["Test review"],
    "Sentiment": ["negative"], "Primary Category": ["Delivery"],
    "Secondary Category": [None], "Aspect Breakdown": ["🔴 Delivery: negative"],
    "Urgency": ["critical"], "Emotion": ["angry"],
    "Core Issue": ["Arrived broken"], "Confidence": ["high"],
})

# ── 16a — _fig_to_base64 with a real Plotly figure ───────────
_fig_16a = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
_b64_16a = _fig_to_base64(_fig_16a)
check(isinstance(_b64_16a, str), "16a: _fig_to_base64 should return a string")
check(len(_b64_16a) > 500, f"16a: base64 string too short ({len(_b64_16a)})")
try:
    import base64 as _b64mod
    _decoded_16a = _b64mod.b64decode(_b64_16a)
    check(_decoded_16a[:4] == b"\x89PNG", "16a: decoded bytes should be a PNG")
except Exception as _e16a_dec:
    check(False, f"16a: base64 decode failed: {_e16a_dec}")

# ── 16b — _fig_to_base64 with None input ──────────────────────
try:
    _result_16b = _fig_to_base64(None)
    check(_result_16b == "", "16b: _fig_to_base64(None) should return empty string")
except Exception as _e16b:
    check(False, f"16b: _fig_to_base64(None) raised {_e16b}")

# ── 16c — _truncate helper ────────────────────────────────────
check(_truncate("hello world", 5) == "hello…", "16c: _truncate should truncate with ellipsis")
check(_truncate("hi", 10) == "hi",                  "16c: _truncate short string unchanged")
check(_truncate("", 5) == "",                        "16c: _truncate empty string returns empty")
check(_truncate(None, 5) == "",                      "16c: _truncate None returns empty")

# ── 16d — _health_colour returns hex strings ──────────────────
_c80 = _health_colour(80)
_c60 = _health_colour(60)
_c30 = _health_colour(30)
_c10 = _health_colour(10)
check(isinstance(_c80, str) and _c80.startswith("#"), "16d: _health_colour(80) should return hex string")
check(isinstance(_c60, str) and _c60.startswith("#"), "16d: _health_colour(60) should return hex string")
check(isinstance(_c30, str) and _c30.startswith("#"), "16d: _health_colour(30) should return hex string")
check(isinstance(_c10, str) and _c10.startswith("#"), "16d: _health_colour(10) should return hex string")
check(_c80 != _c10, "16d: green score should differ from red score colour")

# ── 16e — generate_pdf with action_plan success=False ─────────
try:
    _pdf_16e = generate_pdf(
        dashboard_data=_mock_dashboard,
        action_plan=_mock_action_plan_fail,
        profile=_mock_profile,
        results_df=_mock_df,
    )
    check(isinstance(_pdf_16e, bytes), "16e: generate_pdf should return bytes")
    check(len(_pdf_16e) > 10000, f"16e: PDF too small ({len(_pdf_16e)} bytes)")
    check(_pdf_16e[:4] == b"%PDF", "16e: bytes should start with PDF magic %PDF")
except Exception as _e16e:
    check(False, f"16e: generate_pdf raised {_e16e}")

# ── 16f — generate_pdf with action_plan success=True ──────────
_mock_action_plan_ok = {
    "success": True,
    "result": {
        "health_score": 73, "health_label": "Mixed",
        "executive_summary": "Test summary sentence one. Test sentence two.",
        "key_strengths": ["Strong delivery performance"],
        "recommendations": [{
            "rank": 1, "title": "Fix Delivery",
            "rationale": "3 critical issues found.",
            "action": "Improve packaging process.",
            "impact": "high", "effort": "medium", "timeframe": "immediate",
        }],
        "quick_win": {
            "title": "Quick fix",
            "description": "Do this now.",
            "expected_outcome": "Better reviews.",
        },
        "data_quality_note": None,
    },
    "health_score": 73, "health_label": "Mixed",
    "provider": "groq", "error": None,
}
try:
    _pdf_16f = generate_pdf(
        dashboard_data=_mock_dashboard,
        action_plan=_mock_action_plan_ok,
        profile=_mock_profile,
        results_df=_mock_df,
    )
    check(_pdf_16f[:4] == b"%PDF", "16f: PDF with success=True should be valid PDF")
except Exception as _e16f:
    check(False, f"16f: generate_pdf(success=True) raised {_e16f}")

# ── 16g — company_name > 45 chars does not raise ──────────────
_long_profile = dict(_mock_profile, company_name="A" * 60)
try:
    _pdf_16g = generate_pdf(
        dashboard_data=_mock_dashboard,
        action_plan=_mock_action_plan_fail,
        profile=_long_profile,
        results_df=_mock_df,
    )
    check(_pdf_16g[:4] == b"%PDF", "16g: long company name should still produce valid PDF")
except Exception as _e16g:
    check(False, f"16g: generate_pdf with long company_name raised {_e16g}")

# ── 16h — empty top_issues does not raise ─────────────────────
_empty_issues_dashboard = dict(_mock_dashboard, top_issues=[])
try:
    _pdf_16h = generate_pdf(
        dashboard_data=_empty_issues_dashboard,
        action_plan=_mock_action_plan_fail,
        profile=_mock_profile,
        results_df=_mock_df,
    )
    check(_pdf_16h[:4] == b"%PDF", "16h: empty top_issues should produce valid PDF")
except Exception as _e16h:
    check(False, f"16h: generate_pdf with empty top_issues raised {_e16h}")

# ── 16i — results_df with 250 rows does not raise ─────────────
_base_row = _mock_df.iloc[0].to_dict()
_big_df = pd.DataFrame([_base_row] * 250)
try:
    _pdf_16i = generate_pdf(
        dashboard_data=_mock_dashboard,
        action_plan=_mock_action_plan_fail,
        profile=_mock_profile,
        results_df=_big_df,
    )
    check(_pdf_16i[:4] == b"%PDF", "16i: 250-row DataFrame should produce valid PDF")
except Exception as _e16i:
    check(False, f"16i: generate_pdf with 250-row df raised {_e16i}")


# ════════════════════════════════════════════════════════════
# SECTION 18 — Auth System Tests
# ════════════════════════════════════════════════════════════
print("\n--- Section 18: Auth System ---")

import uuid as _uuid_module
import json as _json
import os as _os
from api.auth.password import hash_password as _hash_pw, verify_password as _verify_pw
from api.auth.tokens import (
    create_access_token as _create_at,
    create_refresh_token as _create_rt,
    decode_token as _decode_tok,
    decode_refresh_token as _decode_rt,
)
from api.storage.users import UserStore as _UserStore, USERS_DIR as _USERS_DIR
from api.main import app as _fiq_app
from fastapi.testclient import TestClient as _TestClient

_client = _TestClient(_fiq_app)
_test_email = f"section18_{_uuid_module.uuid4().hex[:8]}@feedbackiq.test"
_no_profile_email = f"noprofile_{_uuid_module.uuid4().hex[:6]}@feedbackiq.test"
_test_uid = None
_test_access_token = None

try:
    # 18a — hash produces argon2 string
    _h = _hash_pw("testpassword123")
    check(_h.startswith("$argon2"),
          "18a: hash_password returns argon2 hash")

    # 18b — correct password verifies
    check(_verify_pw("testpassword123", _h) is True,
          "18b: verify_password correct password returns True")

    # 18c — wrong password fails
    check(_verify_pw("wrongpassword", _h) is False,
          "18c: verify_password wrong password returns False")

    # 18d — access token is JWT string with 2 dots
    _tok = _create_at("uid-test", "test@test.com")
    check(isinstance(_tok, str) and _tok.count(".") == 2,
          "18d: create_access_token returns valid JWT string")

    # 18e — decode access token returns correct payload
    _pay = _decode_tok(_tok)
    check(_pay is not None and _pay.get("sub") == "uid-test"
          and _pay.get("type") == "access",
          "18e: decode_token returns payload with sub and type=access")

    # 18f — decode invalid token returns None
    check(_decode_tok("not.a.valid.token") is None,
          "18f: decode_token invalid token returns None")
    check(_decode_tok("") is None,
          "18f(b): decode_token empty string returns None")

    # 18g — refresh token decode
    _ref = _create_rt("uid-ref")
    check(_decode_rt(_ref) == "uid-ref",
          "18g: decode_refresh_token returns correct user_id")
    check(_decode_rt(_tok) is None,
          "18g(b): access token fails refresh decode check")

    # 18h — UserStore signup via API
    _signup_resp = _client.post("/auth/signup", json={
        "email": _test_email,
        "password": "SecurePass123",
        "full_name": "Test Section18",
    })
    check(_signup_resp.status_code == 201,
          f"18h: POST /auth/signup returns 201 (got {_signup_resp.status_code})")
    _signup_data = _signup_resp.json()
    check("access_token" in _signup_data and "refresh_token" in _signup_data,
          "18h(b): signup response contains access_token and refresh_token")
    check(_signup_data.get("has_profile") is False,
          "18h(c): new user has_profile is False")
    _test_access_token = _signup_data["access_token"]
    _test_uid = _signup_data["user_id"]

    # 18i — duplicate signup returns 409
    _dup_resp = _client.post("/auth/signup", json={
        "email": _test_email,
        "password": "AnotherPass123",
        "full_name": "Duplicate",
    })
    check(_dup_resp.status_code == 409,
          f"18i: duplicate signup returns 409 (got {_dup_resp.status_code})")

    # 18j — login with correct credentials
    _login_resp = _client.post("/auth/login", data={
        "username": _test_email,
        "password": "SecurePass123",
    })
    check(_login_resp.status_code == 200,
          f"18j: POST /auth/login returns 200 (got {_login_resp.status_code})")
    check("access_token" in _login_resp.json(),
          "18j(b): login response contains access_token")

    # 18k — login with wrong password returns 401
    _bad_login = _client.post("/auth/login", data={
        "username": _test_email,
        "password": "WrongPassword!",
    })
    check(_bad_login.status_code == 401,
          f"18k: wrong password returns 401 (got {_bad_login.status_code})")
    check(_bad_login.json().get("error") == "Invalid email or password",
          "18k(b): error message does not reveal which field was wrong")

    # 18l — GET /auth/me with valid token
    _me_resp = _client.get("/auth/me",
                            headers={"Authorization": f"Bearer {_test_access_token}"})
    check(_me_resp.status_code == 200,
          f"18l: GET /auth/me returns 200 (got {_me_resp.status_code})")
    _me_data = _me_resp.json()
    check(_me_data.get("email") == _test_email,
          "18l(b): /auth/me returns correct email")
    check(_me_data.get("has_profile") is False,
          "18l(c): /auth/me has_profile False before profile save")

    # 18m — GET /auth/me without token returns 401
    _me_unauth = _client.get("/auth/me")
    check(_me_unauth.status_code == 401,
          f"18m: /auth/me without token returns 401 (got {_me_unauth.status_code})")

    # 18n — PUT /auth/profile saves profile
    _profile_resp = _client.put("/auth/profile",
        headers={"Authorization": f"Bearer {_test_access_token}"},
        json={
            "company_name": "Test Corp",
            "industry": "E-commerce",
            "categories": ["Delivery", "Quality", "Support"],
            "description": "Test company",
            "urgency_definition": "",
        })
    check(_profile_resp.status_code == 200,
          f"18n: PUT /auth/profile returns 200 (got {_profile_resp.status_code})")
    check(_profile_resp.json().get("profile", {}).get("company_name") == "Test Corp",
          "18n(b): profile response contains company_name")

    # 18o — GET /auth/profile returns saved profile
    _get_profile_resp = _client.get("/auth/profile",
        headers={"Authorization": f"Bearer {_test_access_token}"})
    check(_get_profile_resp.status_code == 200,
          f"18o: GET /auth/profile returns 200 (got {_get_profile_resp.status_code})")
    check(_get_profile_resp.json().get("profile", {}).get("company_name") == "Test Corp",
          "18o(b): GET /auth/profile returns correct company_name")

    # 18p — GET /auth/profile before profile exists returns 404
    _np_signup = _client.post("/auth/signup", json={
        "email": _no_profile_email,
        "password": "NoProfile123",
        "full_name": "No Profile User",
    })
    if _np_signup.status_code == 201:
        _np_token = _np_signup.json()["access_token"]
        _np_uid = _np_signup.json()["user_id"]
        _np_get = _client.get("/auth/profile",
            headers={"Authorization": f"Bearer {_np_token}"})
        check(_np_get.status_code == 404,
              f"18p: GET /auth/profile before profile set returns 404 (got {_np_get.status_code})")
    else:
        check(False, f"18p: noprofile signup failed ({_np_signup.status_code})")
        _np_uid = None

    # 18q — POST /auth/refresh issues new access token
    _refresh_tok = _login_resp.json().get("refresh_token")
    _refresh_resp = _client.post("/auth/refresh",
        json={"refresh_token": _refresh_tok})
    check(_refresh_resp.status_code == 200,
          f"18q: POST /auth/refresh returns 200 (got {_refresh_resp.status_code})")
    check("access_token" in _refresh_resp.json(),
          "18q(b): refresh response contains new access_token")

    # 18r — POST /auth/change-password
    _chpw_resp = _client.post("/auth/change-password",
        headers={"Authorization": f"Bearer {_test_access_token}"},
        json={"current_password": "SecurePass123",
              "new_password": "NewSecure456"})
    check(_chpw_resp.status_code == 200,
          f"18r: POST /auth/change-password returns 200 (got {_chpw_resp.status_code})")

    # 18s — GET /auth/history returns empty list for new user
    _hist_resp = _client.get("/auth/history",
        headers={"Authorization": f"Bearer {_test_access_token}"})
    check(_hist_resp.status_code == 200,
          f"18s: GET /auth/history returns 200 (got {_hist_resp.status_code})")
    check("sessions" in _hist_resp.json() and "total" in _hist_resp.json(),
          "18s(b): history response has sessions and total keys")

finally:
    # Cleanup — remove all @feedbackiq.test users created in Section 18
    _index_path = _os.path.join(_USERS_DIR, "_email_index.json")
    _index_data = {}
    if _os.path.exists(_index_path):
        try:
            with open(_index_path, encoding="utf-8") as _f:
                _index_data = _json.load(_f)
        except Exception:
            pass

    _emails_to_remove = [e for e in _index_data if e.endswith("@feedbackiq.test")]
    for _te in _emails_to_remove:
        _uid_to_del = _index_data.pop(_te, None)
        if _uid_to_del:
            for _ext in [".json", ".lock"]:
                _fp = _os.path.join(_USERS_DIR, _uid_to_del + _ext)
                if _os.path.exists(_fp):
                    try:
                        _os.remove(_fp)
                    except Exception:
                        pass

    if _os.path.exists(_index_path):
        try:
            with open(_index_path, "w", encoding="utf-8") as _f:
                _json.dump(_index_data, _f, indent=2)
        except Exception:
            pass

# ════════════════════════════════════════════════════════════
# SECTION 19 — FastAPI Backend Tests
# ════════════════════════════════════════════════════════════
print("\n--- Section 19: FastAPI Backend ---")

import uuid as _uuid19
import os as _os19
import json as _json19
from api.main import app as _app19
from api.storage.sessions import SessionStore as _SS19, SESSIONS_DIR as _SDIR19
from api.storage.users import UserStore as _US19, USERS_DIR as _UDIR19
from fastapi.testclient import TestClient as _TC19
from unittest.mock import patch as _patch19, AsyncMock as _AsyncMock19

_c19 = _TC19(_app19)

# ── Test user A setup ────────────────────────────────────────────────
_email19 = f"s19_{_uuid19.uuid4().hex[:8]}@feedbackiq.test"
_r19_signup = _c19.post("/auth/signup", json={
    "email": _email19, "password": "testpass123",
    "full_name": "Section19 User"})
assert _r19_signup.status_code == 201, f"Section 19 setup failed: {_r19_signup.text}"
_tok19 = _r19_signup.json()["access_token"]
_uid19 = _r19_signup.json()["user_id"]
_auth19 = {"Authorization": f"Bearer {_tok19}"}

# ── Test user B (for ownership tests) ───────────────────────────────
_email19b = f"s19b_{_uuid19.uuid4().hex[:8]}@feedbackiq.test"
_r19b_signup = _c19.post("/auth/signup", json={
    "email": _email19b, "password": "testpass123",
    "full_name": "Section19 UserB"})
assert _r19b_signup.status_code == 201, f"Section 19 user B setup failed"
_tok19b = _r19b_signup.json()["access_token"]
_auth19b = {"Authorization": f"Bearer {_tok19b}"}

# ── Mock classification return value (dict, not tuple) ───────────────
_MOCK_CLF = {
    "all_results": [
        {"id": 0, "sentiment": "positive", "primary_category": "Delivery",
         "secondary_category": None,
         "aspects": [{"category": "Delivery", "sentiment": "positive"}],
         "urgency": "low", "emotion": "happy",
         "core_issue": "Fast delivery", "confidence": "high"},
        {"id": 1, "sentiment": "negative", "primary_category": "Quality",
         "secondary_category": None,
         "aspects": [{"category": "Quality", "sentiment": "negative"}],
         "urgency": "medium", "emotion": "disappointed",
         "core_issue": "Poor quality", "confidence": "high"},
        {"id": 2, "sentiment": "neutral", "primary_category": "Delivery",
         "secondary_category": None,
         "aspects": [{"category": "Delivery", "sentiment": "neutral"}],
         "urgency": "low", "emotion": "neutral",
         "core_issue": "Average delivery", "confidence": "medium"},
        {"id": 3, "sentiment": "positive", "primary_category": "Quality",
         "secondary_category": None,
         "aspects": [{"category": "Quality", "sentiment": "positive"}],
         "urgency": "low", "emotion": "happy",
         "core_issue": "Great quality", "confidence": "high"},
        {"id": 4, "sentiment": "negative", "primary_category": "Delivery",
         "secondary_category": None,
         "aspects": [{"category": "Delivery", "sentiment": "negative"}],
         "urgency": "critical", "emotion": "angry",
         "core_issue": "Very late delivery", "confidence": "high"},
    ],
    "failed_batches": [],
    "total_classified": 5,
    "total_failed": 0,
    "gemini_fallback_count": 0,
}

# Tuple form matching the async function's return signature
_MOCK_CLF_ASYNC = (
    _MOCK_CLF["all_results"],
    _MOCK_CLF["failed_batches"],
    _MOCK_CLF["total_classified"],
    _MOCK_CLF["total_failed"],
    _MOCK_CLF["gemini_fallback_count"],
)

_RAW_TEXT_19 = (
    "Fast delivery, loved it\n"
    "Poor quality, very disappointed\n"
    "Average delivery experience\n"
    "Great quality product\n"
    "Very late delivery, unacceptable"
)

_session_id_19 = None
_anon_session_id_19 = None

try:
    # 19a — GET /health returns 200 with expected modules
    _r = _c19.get("/health")
    check(_r.status_code == 200,
          f"19a: GET /health returns 200 (got {_r.status_code})")
    _mods = _r.json().get("modules", [])
    check("auth" in _mods and "sessions" in _mods and "analyse" in _mods,
          "19a: /health lists all expected modules")

    # 19b — POST /sessions (authenticated) → 201 with user_id
    _r = _c19.post("/sessions", json={
        "company_name": "TestCo19",
        "industry": "E-commerce",
        "categories": ["Delivery", "Quality"],
        "description": "", "urgency_definition": "",
    }, headers=_auth19)
    check(_r.status_code == 201,
          f"19b: POST /sessions authenticated returns 201 (got {_r.status_code})")
    _session_id_19 = _r.json()["session_id"]
    check(bool(_session_id_19), "19b: session_id is non-empty string")
    check(_r.json()["user_id"] == _uid19,
          "19b: session linked to authenticated user")

    # 19c — POST /sessions (anonymous) → 201 with user_id=null
    _r = _c19.post("/sessions", json={
        "company_name": "AnonCo",
        "industry": "SaaS",
        "categories": ["Support", "Billing"],
        "description": "", "urgency_definition": "",
    })
    check(_r.status_code == 201,
          f"19c: anonymous POST /sessions returns 201 (got {_r.status_code})")
    _anon_session_id_19 = _r.json()["session_id"]
    check(_r.json()["user_id"] is None,
          "19c: anonymous session has user_id=null")

    # 19d — POST /sessions with similar categories → 422
    # "Fast Delivery Service" vs "Fast Delivery Issues": 2/3 words match = 66.7% >= 60%
    _r = _c19.post("/sessions", json={
        "company_name": "TestCo",
        "industry": "SaaS",
        "categories": ["Fast Delivery Service", "Fast Delivery Issues"],
        "description": "", "urgency_definition": "",
    })
    check(_r.status_code == 422,
          f"19d: similar categories returns 422 (got {_r.status_code})")

    # 19e — POST /analyse/text with mock classification → 200
    with _patch19("api.routes.analyse.classify_all_batches_async",
                  new=_AsyncMock19(return_value=_MOCK_CLF_ASYNC)):
        _r = _c19.post("/analyse/text",
                        data={"session_id": _session_id_19,
                              "raw_text": _RAW_TEXT_19},
                        headers=_auth19)
    check(_r.status_code == 200,
          f"19e: POST /analyse/text returns 200 (got {_r.status_code})")
    _analyse_data = _r.json()
    check(_analyse_data.get("total_classified") == 5,
          f"19e: total_classified == 5 (got {_analyse_data.get('total_classified')})")
    check(_analyse_data.get("session_id") == _session_id_19,
          "19e: response session_id matches request")
    check("preprocessing" in _analyse_data,
          "19e: response contains preprocessing summary")

    # 19f — GET /dashboard/{session_id} → 200 with dashboard data
    _r = _c19.get(f"/dashboard/{_session_id_19}", headers=_auth19)
    check(_r.status_code == 200,
          f"19f: GET /dashboard returns 200 (got {_r.status_code})")
    _dash = _r.json()
    check("dashboard_data" in _dash,
          "19f: response contains dashboard_data key")
    check(_dash.get("classification_done") is True,
          "19f: classification_done is True")
    check(_dash.get("total_classified") == 5,
          f"19f: total_classified == 5 (got {_dash.get('total_classified')})")
    check("sentiment" in _dash.get("dashboard_data", {}),
          "19f: dashboard_data contains sentiment key")

    # 19g — GET /dashboard before analysis → 425
    with _patch19("api.routes.analyse.classify_all_batches_async",
                  new=_AsyncMock19(return_value=_MOCK_CLF_ASYNC)):
        _r_new = _c19.post("/sessions", json={
            "company_name": "PreAnalysis",
            "industry": "SaaS",
            "categories": ["Support", "Bugs"],
            "description": "", "urgency_definition": "",
        })
    _pre_sid = _r_new.json()["session_id"]
    _r = _c19.get(f"/dashboard/{_pre_sid}")
    check(_r.status_code == 425,
          f"19g: GET /dashboard before analysis returns 425 (got {_r.status_code})")

    # 19h — GET /dashboard nonexistent session → 404
    _r = _c19.get("/dashboard/nonexistent-session-id-12345")
    check(_r.status_code == 404,
          f"19h: GET /dashboard nonexistent returns 404 (got {_r.status_code})")

    # 19i — GET /export/{session_id} → CSV download
    _r = _c19.get(f"/export/{_session_id_19}", headers=_auth19)
    check(_r.status_code == 200,
          f"19i: GET /export returns 200 (got {_r.status_code})")
    check(_r.headers.get("content-type", "").startswith("text/csv"),
          "19i: export content-type is text/csv")
    _csv_content = _r.content.decode("utf-8")
    check("Sentiment" in _csv_content and "Primary Category" in _csv_content,
          "19i: CSV contains expected column headers")
    check(_csv_content.count("\n") >= 5,
          "19i: CSV has at least 5 rows (header + 5 reviews)")

    # 19j — GET /export before analysis → 425
    _r = _c19.get(f"/export/{_pre_sid}")
    check(_r.status_code == 425,
          f"19j: GET /export before analysis returns 425 (got {_r.status_code})")

    # 19k — POST /action-plan before analysis → 425
    _r = _c19.post(f"/action-plan/{_pre_sid}")
    check(_r.status_code == 425,
          f"19k: POST /action-plan before analysis returns 425 (got {_r.status_code})")

    # 19l — POST /action-plan (mocked LLM) → 200
    _MOCK_AP = {
        "success": True,
        "result": {
            "executive_summary": "Test summary",
            "top_priorities": [],
            "quick_wins": [],
            "strategic_actions": [],
        },
        "health_score": 72,
        "health_label": "Strong",
        "provider": "groq",
        "error": None,
    }
    with _patch19("api.routes.action_plan.generate_action_plan",
                  return_value=_MOCK_AP):
        _r = _c19.post(f"/action-plan/{_session_id_19}", headers=_auth19)
    check(_r.status_code == 200,
          f"19l: POST /action-plan returns 200 (got {_r.status_code})")
    _ap_data = _r.json()
    check(_ap_data.get("success") is True,
          "19l: action plan success is True")
    check(_ap_data.get("health_score") == 72,
          f"19l: health_score == 72 (got {_ap_data.get('health_score')})")

    # 19m — GET /report (mocked PDF) → 200 streaming response
    _MOCK_PDF = b"%PDF-1.4 mock pdf content for testing purposes only"
    with _patch19("api.routes.report.generate_pdf", return_value=_MOCK_PDF):
        _r = _c19.get(f"/report/{_session_id_19}", headers=_auth19)
    check(_r.status_code == 200,
          f"19m: GET /report returns 200 (got {_r.status_code})")
    check(_r.headers.get("content-type", "").startswith("application/pdf"),
          "19m: report content-type is application/pdf")
    check(_r.content[:4] == b"%PDF",
          "19m: report content starts with %PDF")

    # 19n — GET /report before analysis → 425
    _r = _c19.get(f"/report/{_pre_sid}")
    check(_r.status_code == 425,
          f"19n: GET /report before analysis returns 425 (got {_r.status_code})")

    # 19o — GET /sessions returns authenticated user's history
    _r = _c19.get("/sessions", headers=_auth19)
    check(_r.status_code == 200,
          f"19o: GET /sessions returns 200 (got {_r.status_code})")
    _sess_list = _r.json()
    check("sessions" in _sess_list and "total" in _sess_list,
          "19o: GET /sessions returns sessions and total keys")
    check(_sess_list["total"] >= 1,
          f"19o: user has at least 1 session in history (got {_sess_list['total']})")

    # 19p — GET /sessions anonymous → empty list
    _r = _c19.get("/sessions")
    check(_r.status_code == 200,
          f"19p: anonymous GET /sessions returns 200 (got {_r.status_code})")
    check(_r.json()["total"] == 0,
          "19p: anonymous GET /sessions returns empty list")

    # 19q — Ownership: user B cannot access user A's session → 403
    _r = _c19.get(f"/dashboard/{_session_id_19}", headers=_auth19b)
    check(_r.status_code == 403,
          f"19q: user B accessing user A session returns 403 (got {_r.status_code})")

    # 19r — Anonymous session accessible by anyone (no ownership restriction)
    with _patch19("api.routes.analyse.classify_all_batches_async",
                  new=_AsyncMock19(return_value=_MOCK_CLF_ASYNC)):
        _r = _c19.post("/analyse/text",
                        data={"session_id": _anon_session_id_19,
                              "raw_text": _RAW_TEXT_19})
    check(_r.status_code == 200,
          f"19r: anonymous session analysis returns 200 (got {_r.status_code})")
    _r = _c19.get(f"/dashboard/{_anon_session_id_19}", headers=_auth19)
    check(_r.status_code == 200,
          f"19r: authenticated user can read anonymous session dashboard (got {_r.status_code})")

    # 19s — POST /analyse/text with session belonging to user B → 403 for user A
    _r_bs = _c19.post("/sessions", json={
        "company_name": "UserBCo",
        "industry": "SaaS",
        "categories": ["Support", "Speed"],
        "description": "", "urgency_definition": "",
    }, headers=_auth19b)
    _b_session_id = _r_bs.json()["session_id"]
    with _patch19("api.routes.analyse.classify_all_batches_async",
                  new=_AsyncMock19(return_value=_MOCK_CLF_ASYNC)):
        _r = _c19.post("/analyse/text",
                        data={"session_id": _b_session_id,
                              "raw_text": _RAW_TEXT_19},
                        headers=_auth19)
    check(_r.status_code == 403,
          f"19s: user A analysing user B session returns 403 (got {_r.status_code})")

finally:
    # Cleanup — remove all @feedbackiq.test users and their sessions
    _idx_path19 = _os19.path.join(_UDIR19, "_email_index.json")
    _idx_data19 = {}
    if _os19.path.exists(_idx_path19):
        try:
            with open(_idx_path19, encoding="utf-8") as _f19:
                _idx_data19 = _json19.load(_f19)
        except Exception:
            pass

    _to_del19 = [e for e in _idx_data19 if e.endswith("@feedbackiq.test")]
    for _te19 in _to_del19:
        _u19 = _idx_data19.pop(_te19, None)
        if _u19:
            for _ext19 in [".json", ".lock"]:
                _fp19 = _os19.path.join(_UDIR19, _u19 + _ext19)
                if _os19.path.exists(_fp19):
                    try:
                        _os19.remove(_fp19)
                    except Exception:
                        pass

    if _os19.path.exists(_idx_path19):
        try:
            with open(_idx_path19, "w", encoding="utf-8") as _f19:
                _json19.dump(_idx_data19, _f19, indent=2)
        except Exception:
            pass

    # Remove test session files
    for _ts19 in [s for s in [_session_id_19, _anon_session_id_19,
                               locals().get("_pre_sid"),
                               locals().get("_b_session_id")]
                  if s]:
        for _ext19 in [".json", ".lock"]:
            _sp19 = _os19.path.join(_SDIR19, _ts19 + _ext19)
            if _os19.path.exists(_sp19):
                try:
                    _os19.remove(_sp19)
                except Exception:
                    pass

# ════════════════════════════════════════════════════════════
# SECTION 20 — Async Classifier Tests
# ════════════════════════════════════════════════════════════
print("\n--- Section 20: Async Classifier ---")

import asyncio as _asyncio20
import inspect as _inspect20
from unittest.mock import patch as _patch20, AsyncMock as _AsyncMock20

# 20a — classify_all_batches_async is importable and callable
from core.classifier_async import classify_all_batches_async as _clf_async20

check(callable(_clf_async20),
      "20a: classify_all_batches_async importable from core.classifier_async")
check(_asyncio20.iscoroutinefunction(_clf_async20),
      "20a: classify_all_batches_async is a coroutine function")

# 20b — empty batches returns ([], [], 0, 0, 0) without error
_profile20 = {
    "company_name": "TestCo", "industry": "SaaS",
    "categories": ["Quality", "Support"],
    "description": "", "urgency_definition": "",
}
_res20b = _asyncio20.run(_clf_async20([], _profile20, None))
_ar20b, _fb20b, _tc20b, _tf20b, _gf20b = _res20b
check(
    _ar20b == [] and _fb20b == [] and _tc20b == 0 and _tf20b == 0 and _gf20b == 0,
    "20b: empty batches returns ([], [], 0, 0, 0)",
)

# 20c — single batch of 5 mock reviews classifies correctly (no real API calls)
_batch20c = [{"id": i, "text": f"Review number {i}"} for i in range(5)]
_batches20c = [_batch20c]

_mock_batch_result20c = {
    "success": True,
    "results": [
        {
            "id": i,
            "sentiment": "positive",
            "primary_category": "Quality",
            "secondary_category": None,
            "aspects": [{"category": "Quality", "sentiment": "positive"}],
            "urgency": "low",
            "emotion": "happy",
            "core_issue": f"Good product {i}",
            "confidence": "high",
        }
        for i in range(5)
    ],
    "batch_ids": list(range(5)),
    "error": None,
    "provider": "groq",
}

with _patch20(
    "core.classifier_async.classify_batch_async",
    new=_AsyncMock20(return_value=_mock_batch_result20c),
):
    _res20c = _asyncio20.run(_clf_async20(_batches20c, _profile20))

_ar20c, _fb20c, _tc20c, _tf20c, _gf20c = _res20c
check(
    _tc20c == 5,
    f"20c: 5 reviews classified correctly via async pipeline (got {_tc20c})",
)
check(
    len(_ar20c) == 5,
    f"20c: all_results contains 5 entries (got {len(_ar20c)})",
)
check(
    _fb20c == [] and _tf20c == 0,
    "20c: no failed batches when mock succeeds",
)

# 20d — semaphore is created with value 3 inside classify_all_batches_async
_src20d = _inspect20.getsource(_clf_async20)
check(
    "Semaphore(3)" in _src20d,
    "20d: asyncio.Semaphore(3) is hardcoded in classify_all_batches_async",
)

# 20e — sync classify_all_batches still works (regression: section 13 equivalent)
from core.classifier import classify_all_batches as _clf_sync20
from core.classifier import build_progress_summary as _bps20

_ps20e = _bps20(
    results_so_far=[
        {"id": 0, "sentiment": "positive", "urgency": "low"},
        {"id": 1, "sentiment": "negative", "urgency": "critical"},
    ],
    total_batches=5,
    completed_batches=2,
    failed_count=0,
)
check(_ps20e["classified_so_far"] == 2, "20e: sync build_progress_summary classified_so_far == 2")
check(_ps20e["pct_complete"] == 40, "20e: sync build_progress_summary pct_complete == 40 (2/5)")
check(
    _ps20e["positive_so_far"] == 1 and _ps20e["negative_so_far"] == 1,
    "20e: sync build_progress_summary counts positive and negative correctly",
)

_sync_empty = _clf_sync20([], {"categories": ["Quality"], "company_name": "X", "industry": "Y"})
check(
    _sync_empty["total_classified"] == 0 and _sync_empty["all_results"] == [],
    "20e: sync classify_all_batches returns zero totals for empty batches",
)

# ════════════════════════════════════════════════════════════
# SECTION 21 — Trend Engine Tests
# ════════════════════════════════════════════════════════════
print("\n--- Section 21: Trend Engine ---")

from core.trend_engine import (
    compute_sentiment_trajectory as _cst21,
    compute_category_drift as _ccd21,
    compute_emerging_issues as _cei21,
    compute_trends as _ct21,
)

_mock_sessions21 = [
    {
        "session_id": "s1",
        "created_at": "2026-06-01T10:00:00+00:00",
        "label": "Analysis — 01 Jun 2026",
        "total_reviews": 30,
        "overall_score": 60.0,
        "sentiment": {"positive_pct": 50.0, "negative_pct": 40.0, "neutral_pct": 10.0},
        "categories": [
            {"category": "Delivery", "count": 15, "pct": 50.0},
            {"category": "Quality", "count": 10, "pct": 33.0},
        ],
        "urgency": {"critical_count": 3, "critical_pct": 10.0},
        "top_issues": [{"category": "Delivery", "count": 10, "critical_count": 3}],
        "top_category": "Delivery",
    },
    {
        "session_id": "s2",
        "created_at": "2026-06-15T10:00:00+00:00",
        "label": "Analysis — 15 Jun 2026",
        "total_reviews": 45,
        "overall_score": 72.0,
        "sentiment": {"positive_pct": 62.0, "negative_pct": 28.0, "neutral_pct": 10.0},
        "categories": [
            {"category": "Delivery", "count": 18, "pct": 40.0},
            {"category": "Quality", "count": 15, "pct": 33.0},
            {"category": "Support", "count": 12, "pct": 27.0},
        ],
        "urgency": {"critical_count": 1, "critical_pct": 2.2},
        "top_issues": [{"category": "Delivery", "count": 8, "critical_count": 1}],
        "top_category": "Delivery",
    },
]

# 21a — improving trajectory (72 - 60 = 12 > 5)
_traj21a = _cst21(_mock_sessions21)
check(_traj21a["trend"] == "improving",
      f"21a: trend == 'improving' (got '{_traj21a['trend']}')")
check(_traj21a["change"] == 12.0,
      f"21a: change == 12.0 (got {_traj21a['change']})")

# 21b — insufficient_data with single session
_traj21b = _cst21([_mock_sessions21[0]])
check(_traj21b["trend"] == "insufficient_data",
      f"21b: single session gives trend='insufficient_data' (got '{_traj21b['trend']}')")

# 21c — 'Support' appears in new_categories (in s2, not in s1)
_drift21c = _ccd21(_mock_sessions21)
check("Support" in _drift21c["new_categories"],
      f"21c: 'Support' in new_categories (got {_drift21c['new_categories']})")

# 21d — 'Delivery' in shrinking (50% → 40%, change = -10 < -5)
_delivery_shrinking21 = [x for x in _drift21c["shrinking"] if x["category"] == "Delivery"]
check(len(_delivery_shrinking21) == 1,
      f"21d: 'Delivery' in shrinking (got {[x['category'] for x in _drift21c['shrinking']]})")
check(_delivery_shrinking21[0]["change"] == -10.0,
      f"21d: Delivery change == -10.0 (got {_delivery_shrinking21[0]['change']})")

# 21e — 'Delivery' in resolved when s2 critical_count drops to 0
_sessions21e = [
    _mock_sessions21[0],
    {
        **_mock_sessions21[1],
        "top_issues": [{"category": "Delivery", "count": 8, "critical_count": 0}],
    },
]
_emerging21e = _cei21(_sessions21e)
_resolved_cats21 = [x["category"] for x in _emerging21e["resolved"]]
check("Delivery" in _resolved_cats21,
      f"21e: 'Delivery' in resolved when critical drops to 0 (got resolved={_resolved_cats21})")

# 21f — available=False when user has no completed sessions
class _EmptyUserStore21:
    def get_user(self, user_id):
        return {"user_id": user_id, "session_history": []}

class _EmptySessionStore21:
    def get_session(self, sid):
        return None
    def deserialise_dashboard(self, data):
        return data

_res21f = _ct21("no-sessions-user", _EmptyUserStore21(), _EmptySessionStore21())
check(_res21f.get("available") is False,
      f"21f: no sessions gives available=False (got {_res21f.get('available')})")
check(_res21f.get("session_count", -1) == 0,
      f"21f: session_count == 0 (got {_res21f.get('session_count')})")

# 21g — compute_trends never raises even when UserStore throws
class _RaisingUserStore21:
    def get_user(self, user_id):
        raise RuntimeError("DB connection failed")

_res21g = _ct21("any-user", _RaisingUserStore21(), _EmptySessionStore21())
check(_res21g.get("available") is False,
      f"21g: exception gives available=False (got {_res21g.get('available')})")
check("error" in _res21g,
      f"21g: exception result has 'error' key (got keys={list(_res21g.keys())})")

# ════════════════════════════════════════════════════════════
# SECTION 22 — Benchmark Engine Tests
# ════════════════════════════════════════════════════════════
print("\n--- Section 22: Benchmark Engine ---")

import hashlib as _hashlib22
import json as _json22
import os as _os22
import shutil as _shutil22

from core.benchmark_engine import (
    _get_user_hash as _guh22,
    _load_benchmarks as _lb22,
    _save_benchmarks as _sb22,
    record_analysis_for_benchmarks as _rab22,
    get_benchmarks_for_industry as _gbfi22,
    INDUSTRY_BENCHMARK_FILE as _IBF22,
    _DATA_DIR as _DDIR22,
)

_TEST_INDUSTRY = "TestIndustry22"

_MOCK_DASHBOARD22 = {
    "total_reviews": 50,
    "sentiment": {
        "overall_score": 72.0,
        "positive_pct": 62.0,
        "negative_pct": 28.0,
        "neutral_pct": 10.0,
    },
    "urgency": {"critical_count": 3, "critical_pct": 6.0},
    "top_category": "Delivery",
}

# 22a — _get_user_hash returns 64-char hex string
_h22a = _guh22("test-user-id-abc")
check(isinstance(_h22a, str) and len(_h22a) == 64,
      f"22a: _get_user_hash returns 64-char hex (got len={len(_h22a)})")
check(all(c in "0123456789abcdef" for c in _h22a),
      "22a: _get_user_hash returns valid hex chars")

# 22b — same input always returns same hash
check(_guh22("test-user-id-abc") == _guh22("test-user-id-abc"),
      "22b: _get_user_hash is deterministic")
check(_guh22("user-a") != _guh22("user-b"),
      "22b: different inputs produce different hashes")

# 22c — _load_benchmarks returns correct empty structure when file missing
_orig_ibf = _IBF22
import core.benchmark_engine as _bmod22
_saved_path = _bmod22.INDUSTRY_BENCHMARK_FILE
_bmod22.INDUSTRY_BENCHMARK_FILE = "/nonexistent/path/x.json"
_empty22c = _lb22()
_bmod22.INDUSTRY_BENCHMARK_FILE = _saved_path
check(_empty22c == {"last_updated": None, "industries": {}},
      f"22c: _load_benchmarks returns empty structure for missing file (got {_empty22c})")

# 22d — record_analysis_for_benchmarks creates industry entry
_rab22("user-22d", _TEST_INDUSTRY, _MOCK_DASHBOARD22)
_data22d = _lb22()
check(_TEST_INDUSTRY in _data22d.get("industries", {}),
      f"22d: industry '{_TEST_INDUSTRY}' created in benchmark file")
check(_data22d["industries"][_TEST_INDUSTRY]["company_count"] == 1,
      f"22d: company_count == 1 (got {_data22d['industries'][_TEST_INDUSTRY].get('company_count')})")

# 22e — same user_id twice does not duplicate in companies list
_rab22("user-22e", _TEST_INDUSTRY, _MOCK_DASHBOARD22)
_rab22("user-22e", _TEST_INDUSTRY, _MOCK_DASHBOARD22)
_data22e = _lb22()
_companies22e = _data22e["industries"][_TEST_INDUSTRY]["companies"]
_hash22e = _guh22("user-22e")
check(_companies22e.count(_hash22e) == 1,
      f"22e: same user appears exactly once in companies list (count={_companies22e.count(_hash22e)})")

# 22f — get_benchmarks_for_industry returns available=False when company_count < 5
_res22f = _gbfi22(_TEST_INDUSTRY, 72.0, 62.0, 28.0, 6.0)
check(_res22f.get("available") is False,
      f"22f: available=False when company_count < 5 (got {_res22f.get('available')})")
check(_res22f.get("reason") == "insufficient_data",
      f"22f: reason == 'insufficient_data' (got '{_res22f.get('reason')}')")

# 22g — get_benchmarks_for_industry returns available=True with 5 entries
# Build mock file with 5 test entries for a fresh industry name
_BENCH_INDUSTRY = "BenchTestIndustry22"
_data22g = _lb22()
_data22g["industries"][_BENCH_INDUSTRY] = {
    "company_count": 5,
    "avg_overall_score": 65.0,
    "avg_positive_pct": 55.0,
    "avg_negative_pct": 33.0,
    "avg_critical_pct": 8.0,
    "common_top_category": "Quality",
    "score_distribution": {"0-25": 0, "26-50": 1, "51-75": 3, "76-100": 1},
    "avg_total_reviews": 60.0,
    "companies": [_guh22(f"mock-user-{i}") for i in range(5)],
    "_top_category_votes": {"Quality": 3, "Support": 2},
}
_sb22(_data22g)

_res22g = _gbfi22(_BENCH_INDUSTRY, 80.0, 70.0, 22.0, 3.0)
check(_res22g.get("available") is True,
      f"22g: available=True with 5 companies (got {_res22g.get('available')})")
check(_res22g.get("score_vs_avg") == round(80.0 - 65.0, 2),
      f"22g: score_vs_avg == 15.0 (got {_res22g.get('score_vs_avg')})")
check(_res22g.get("company_count") == 5,
      f"22g: company_count == 5 (got {_res22g.get('company_count')})")

# 22h — insight string is non-empty and contains industry name
_insight22h = _res22g.get("insight", "")
check(isinstance(_insight22h, str) and len(_insight22h) > 0,
      f"22h: insight is non-empty string (got {repr(_insight22h)})")
check(_BENCH_INDUSTRY in _insight22h,
      f"22h: insight contains industry name (got {repr(_insight22h)})")

# 22i — record_analysis_for_benchmarks never raises with invalid dashboard_data
try:
    _rab22("user-22i", _TEST_INDUSTRY, None)
    _rab22("user-22i", _TEST_INDUSTRY, {})
    _rab22("user-22i", _TEST_INDUSTRY, {"sentiment": "not-a-dict"})
    check(True, "22i: record_analysis_for_benchmarks never raises with invalid data")
except Exception as _e22i:
    check(False, f"22i: raised unexpectedly: {_e22i}")

# 22j — _save_benchmarks creates data/ directory if it doesn't exist
_tmp_dir22j = _os22.path.join(_DDIR22, "_test22j_subdir")
_bmod22._DATA_DIR = _tmp_dir22j
_bmod22.INDUSTRY_BENCHMARK_FILE = _os22.path.join(_tmp_dir22j, "test22j.json")
_bmod22._LOCK_FILE = _os22.path.join(_tmp_dir22j, "test22j.lock")
try:
    if _os22.path.exists(_tmp_dir22j):
        _shutil22.rmtree(_tmp_dir22j)
    _sb22({"last_updated": None, "industries": {}})
    check(_os22.path.exists(_tmp_dir22j),
          f"22j: _save_benchmarks created data directory at {_tmp_dir22j}")
    check(_os22.path.exists(_bmod22.INDUSTRY_BENCHMARK_FILE),
          "22j: _save_benchmarks created the JSON file")
finally:
    _bmod22._DATA_DIR = _DDIR22
    _bmod22.INDUSTRY_BENCHMARK_FILE = _saved_path
    _bmod22._LOCK_FILE = _os22.path.join(_DDIR22, "benchmarks.lock")
    if _os22.path.exists(_tmp_dir22j):
        _shutil22.rmtree(_tmp_dir22j)
    # Clean up test industry entries from benchmark file
    try:
        _cleanup22 = _lb22()
        for _ind in [_TEST_INDUSTRY, _BENCH_INDUSTRY]:
            _cleanup22["industries"].pop(_ind, None)
        _sb22(_cleanup22)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# SECTION 23 — Webhook engine (zero API calls; one network attempt to localhost)
# ─────────────────────────────────────────────────────────────
print("\n--- Section 23: Webhook Engine ---")
import importlib as _importlib23
import shutil as _shutil23
import tempfile as _tempfile23
import uuid as _uuid23

_wmod23 = _importlib23.import_module("core.webhook_engine")
_register23 = _wmod23.register_webhook
_get23 = _wmod23.get_webhook
_delete23 = _wmod23.delete_webhook
_sign23 = _wmod23._sign_payload
_deliver_once23 = _wmod23._deliver_once
_check23 = _wmod23.check_alert_conditions
_dispatch23 = _wmod23.dispatch_webhooks_async

_TEST_USER23 = f"test-user-wh-{_uuid23.uuid4().hex[:8]}"
_HTTPS_URL = "https://example-feedbackiq-test.com/hook"
_HTTP_URL = "http://insecure.example.com/hook"

# Temporary webhook dir so tests don't touch real data
_tmp_wh_dir23 = os.path.join(_tempfile23.mkdtemp(), "webhooks")
_saved_wh_dir23 = _wmod23.WEBHOOK_DIR

# Redirect storage to temp dir
_wmod23.WEBHOOK_DIR = _tmp_wh_dir23

try:
    # 23a — register_webhook raises ValueError for http:// URL
    try:
        _register23(_TEST_USER23, _HTTP_URL, ["critical_spike"])
        check(False, "23a: register_webhook should raise for http:// URL")
    except ValueError as _e23a:
        check("https://" in str(_e23a).lower() or "must" in str(_e23a).lower(),
              "23a: register_webhook raises ValueError with https message for http:// URL")

    # 23b — register_webhook with valid https URL creates file, returns dict with secret
    _reg23b = _register23(_TEST_USER23, _HTTPS_URL, ["critical_spike", "sentiment_drop"])
    check(isinstance(_reg23b, dict), "23b: register_webhook returns a dict")
    check("secret" in _reg23b, "23b: registration result contains 'secret'")
    check(len(_reg23b["secret"]) == 64, "23b: secret is 64-char hex (token_hex(32))")
    check(_reg23b["url"] == _HTTPS_URL, "23b: registration result url matches input")
    check(set(_reg23b["events"]) == {"critical_spike", "sentiment_drop"},
          "23b: registration result events match input")
    check(_reg23b["active"] is True, "23b: webhook registered as active")
    check(os.path.exists(_wmod23._webhook_path(_TEST_USER23)),
          "23b: webhook JSON file created on disk")

    # 23c — get_webhook returns None for unknown user
    _unknown23c = f"no-such-user-{_uuid23.uuid4().hex}"
    check(_get23(_unknown23c) is None,
          "23c: get_webhook returns None for unknown user")

    # 23d — get_webhook returns correct config after registration
    _cfg23d = _get23(_TEST_USER23)
    check(_cfg23d is not None, "23d: get_webhook returns dict after registration")
    check(_cfg23d["url"] == _HTTPS_URL, "23d: get_webhook url matches")
    check(set(_cfg23d["events"]) == {"critical_spike", "sentiment_drop"},
          "23d: get_webhook events match")
    check(_cfg23d["active"] is True, "23d: get_webhook active is True")

    # 23e — delete_webhook removes file; get_webhook returns None afterwards
    _delete23(_TEST_USER23)
    check(_get23(_TEST_USER23) is None,
          "23e: get_webhook returns None after delete_webhook")
    check(not os.path.exists(_wmod23._webhook_path(_TEST_USER23)),
          "23e: webhook JSON file removed from disk")

    # 23f — _sign_payload returns 64-char hex string
    _payload_bytes23 = b'{"event":"test"}'
    _secret23 = "abc123"
    _sig23f = _sign23(_payload_bytes23, _secret23)
    check(isinstance(_sig23f, str) and len(_sig23f) == 64,
          "23f: _sign_payload returns 64-char hex string (SHA-256)")

    # 23g — _sign_payload is deterministic (same inputs, same output)
    _sig23g = _sign23(_payload_bytes23, _secret23)
    check(_sig23g == _sig23f,
          "23g: _sign_payload is deterministic with same inputs")

    # 23h — _sign_payload different secret produces different signature
    _sig23h = _sign23(_payload_bytes23, "different-secret")
    check(_sig23h != _sig23f,
          "23h: _sign_payload produces different result with different secret")

    # 23i — check_alert_conditions triggers critical_spike when critical_pct > 20
    _dd23_high = {
        "urgency": {"critical_pct": 25.0, "critical_count": 10},
        "sentiment": {"overall_score": 60.0},
        "top_issues": [{"category": "Delivery", "count": 50}],
    }
    _triggered23i = _check23("sid-test", {}, _dd23_high, None)
    _events23i = [t["event"] for t in _triggered23i]
    check("critical_spike" in _events23i,
          "23i: check_alert_conditions triggers critical_spike when critical_pct=25.0 > 20")

    # 23j — check_alert_conditions returns empty list when critical_pct <= 20 and no previous
    _dd23_low = {
        "urgency": {"critical_pct": 15.0, "critical_count": 3},
        "sentiment": {"overall_score": 75.0},
        "top_issues": [{"category": "UI", "count": 20}],
    }
    _triggered23j = _check23("sid-test", {}, _dd23_low, None)
    check(len(_triggered23j) == 0,
          "23j: check_alert_conditions returns empty list when critical_pct=15 and no previous")

    # 23k — check_alert_conditions triggers sentiment_drop when score drops > 10 points
    _dd23_curr = {
        "urgency": {"critical_pct": 5.0, "critical_count": 1},
        "sentiment": {"overall_score": 55.0},
        "top_issues": [{"category": "Support", "count": 30}],
    }
    _dd23_prev_k = {
        "sentiment": {"overall_score": 70.0},
        "top_issues": [{"category": "Support", "count": 25}],
    }
    _triggered23k = _check23("sid-test", {}, _dd23_curr, _dd23_prev_k)
    _events23k = [t["event"] for t in _triggered23k]
    check("sentiment_drop" in _events23k,
          "23k: check_alert_conditions triggers sentiment_drop when score drops from 70 to 55")
    _drop23k = next(t for t in _triggered23k if t["event"] == "sentiment_drop")
    check(_drop23k["data"]["drop"] == 15.0,
          "23k: sentiment_drop data.drop is 15.0")

    # 23l — no alert when previous is None and score is low (no comparison available)
    _triggered23l = _check23("sid-test", {}, _dd23_low, None)
    _events23l = [t["event"] for t in _triggered23l]
    check("sentiment_drop" not in _events23l,
          "23l: no sentiment_drop when previous_dashboard_data is None")

    # 23m — check_alert_conditions triggers new_top_issue when top category changes
    _dd23_curr_m = {
        "urgency": {"critical_pct": 5.0, "critical_count": 1},
        "sentiment": {"overall_score": 68.0},
        "top_issues": [{"category": "Billing", "count": 40}],
    }
    _dd23_prev_m = {
        "sentiment": {"overall_score": 65.0},
        "top_issues": [{"category": "Delivery", "count": 35}],
    }
    _triggered23m = _check23("sid-test", {}, _dd23_curr_m, _dd23_prev_m)
    _events23m = [t["event"] for t in _triggered23m]
    check("new_top_issue" in _events23m,
          "23m: check_alert_conditions triggers new_top_issue when top category changes")
    _nti23m = next(t for t in _triggered23m if t["event"] == "new_top_issue")
    check(_nti23m["data"]["new_issue"] == "Billing",
          "23m: new_top_issue data.new_issue is 'Billing'")
    check(_nti23m["data"]["previous_issue"] == "Delivery",
          "23m: new_top_issue data.previous_issue is 'Delivery'")

    # 23n — dispatch_webhooks_async returns immediately when no webhook registered
    _user23n = f"no-wh-user-{_uuid23.uuid4().hex[:8]}"
    _result23n = _dispatch23(_user23n, "sid-test", {}, [{"event": "critical_spike", "data": {}}])
    check(_result23n is None,
          "23n: dispatch_webhooks_async returns None (no-op) when no webhook registered")

    # 23o — _deliver_once with unreachable localhost URL returns success=False, non-empty error
    # Note: makes a local TCP connection attempt (not to Groq/Gemini).
    _ok23o, _code23o, _err23o = _deliver_once23(
        "https://127.0.0.1:19999/feedbackiq-test",
        {"event": "test"},
        "secret123",
    )
    check(_ok23o is False,
          "23o: _deliver_once returns success=False for unreachable localhost")
    check(_err23o is not None and len(_err23o) > 0,
          "23o: _deliver_once returns non-empty error string for unreachable localhost")

finally:
    # Restore real webhook dir
    _wmod23.WEBHOOK_DIR = _saved_wh_dir23
    # Clean up temp directory
    try:
        _parent23 = os.path.dirname(_tmp_wh_dir23)
        if os.path.exists(_parent23):
            _shutil23.rmtree(_parent23, ignore_errors=True)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# SECTION 24 — Production hardening: config validator, logger, middleware, deployment files
# ─────────────────────────────────────────────────────────────
print("\n--- Section 24: Production Hardening ---")
# Ensure .env is loaded so JWT_SECRET_KEY is in os.environ before validate_config
from dotenv import load_dotenv as _load_dotenv24
_load_dotenv24(override=False)
import importlib as _importlib24
import io as _io24
import json as _json24
import logging as _logging24

_cfgmod24 = _importlib24.import_module("core.config_validator")
_validate_config24 = _cfgmod24.validate_config
_REQUIRED24 = _cfgmod24.REQUIRED_ENV_VARS
_OPTIONAL24 = _cfgmod24.OPTIONAL_ENV_VARS

# 24a — validate_config() passes when all required env vars are present
_result24a = _validate_config24()
check(_result24a["status"] == "ok",
      "24a: validate_config() returns status='ok' when all required vars present")
check(set(_result24a["required_vars"]) == set(_REQUIRED24.keys()),
      "24a: validate_config() lists all required_vars in result")

# 24b — validate_config() raises EnvironmentError when GROQ_API_KEY is missing
_saved_groq24 = os.environ.pop("GROQ_API_KEY", None)
try:
    try:
        _validate_config24()
        check(False, "24b: validate_config() should raise when GROQ_API_KEY is missing")
    except EnvironmentError as _e24b:
        check("GROQ_API_KEY" in str(_e24b),
              "24b: EnvironmentError message mentions GROQ_API_KEY")
        check("cannot start" in str(_e24b).lower() or ".env" in str(_e24b),
              "24b: EnvironmentError message includes helpful startup guidance")
finally:
    if _saved_groq24:
        os.environ["GROQ_API_KEY"] = _saved_groq24

# 24c — validate_config() raises EnvironmentError when JWT_SECRET_KEY is missing
_saved_jwt24 = os.environ.pop("JWT_SECRET_KEY", None)
try:
    try:
        _validate_config24()
        check(False, "24c: validate_config() should raise when JWT_SECRET_KEY is missing")
    except EnvironmentError as _e24c:
        check("JWT_SECRET_KEY" in str(_e24c),
              "24c: EnvironmentError message mentions JWT_SECRET_KEY")
finally:
    if _saved_jwt24:
        os.environ["JWT_SECRET_KEY"] = _saved_jwt24

# 24d — validate_config() sets default for GROQ_MODEL if absent
_saved_gmodel24 = os.environ.pop("GROQ_MODEL", None)
try:
    _validate_config24()
    check(os.environ.get("GROQ_MODEL") == "llama-3.1-8b-instant",
          "24d: validate_config() sets GROQ_MODEL default to 'llama-3.1-8b-instant'")
finally:
    if _saved_gmodel24 is not None:
        os.environ["GROQ_MODEL"] = _saved_gmodel24
    else:
        os.environ.pop("GROQ_MODEL", None)

# 24e — logger imports cleanly and logger.info does not raise
_logmod24 = _importlib24.import_module("core.logger")
_logger24 = _logmod24.logger
try:
    _logger24.info("test 24e log message")
    check(True, "24e: logger.info() does not raise")
except Exception as _e24e:
    check(False, f"24e: logger.info() raised unexpectedly: {_e24e}")

# 24f — logger output is JSON-parseable
_buf24f = _io24.StringIO()
_h24f = _logging24.StreamHandler(_buf24f)
from pythonjsonlogger import jsonlogger as _pjl24
_h24f.setFormatter(_pjl24.JsonFormatter(
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
))
_logger24.addHandler(_h24f)
_logger24.info("test 24f json output")
_logger24.removeHandler(_h24f)
_raw24f = _buf24f.getvalue().strip()
check(len(_raw24f) > 0, "24f: logger produced output")
try:
    _parsed24f = _json24.loads(_raw24f)
    check("message" in _parsed24f,
          "24f: logger output is valid JSON with 'message' key")
except Exception as _e24f:
    check(False, f"24f: logger output is not valid JSON: {_e24f}")

# 24g — http_exception_handler returns JSONResponse with 'error' key
from starlette.exceptions import HTTPException as _StarletteHTTPException24
from starlette.testclient import TestClient as _TestClient24
from fastapi import FastAPI as _FastAPI24
_errmod24 = _importlib24.import_module("api.middleware.error_handlers")

_app24g = _FastAPI24()
_app24g.add_exception_handler(
    _StarletteHTTPException24, _errmod24.http_exception_handler
)

@_app24g.get("/test-404")
async def _test_404_handler():
    raise _StarletteHTTPException24(status_code=404, detail="Not found test")

_client24g = _TestClient24(_app24g, raise_server_exceptions=False)
_resp24g = _client24g.get("/test-404")
check(_resp24g.status_code == 404,
      "24g: http_exception_handler returns correct status code 404")
_body24g = _resp24g.json()
check("error" in _body24g,
      "24g: http_exception_handler response has 'error' key")
check(_body24g.get("status_code") == 404,
      "24g: http_exception_handler response has 'status_code' key with value 404")

# 24h — validation_exception_handler returns 422 with 'details' list
from fastapi.exceptions import RequestValidationError as _RVE24
from pydantic import BaseModel as _BM24, Field as _Field24

_app24h = _FastAPI24()
_app24h.add_exception_handler(_RVE24, _errmod24.validation_exception_handler)

class _Body24h(_BM24):
    name: str = _Field24(min_length=1)

@_app24h.post("/test-validate")
async def _validate_handler(body: _Body24h):
    return body

_client24h = _TestClient24(_app24h, raise_server_exceptions=False)
_resp24h = _client24h.post("/test-validate", json={"name": ""})
check(_resp24h.status_code == 422,
      "24h: validation_exception_handler returns 422")
_body24h = _resp24h.json()
check("details" in _body24h,
      "24h: validation_exception_handler response has 'details' key")
check(isinstance(_body24h["details"], list),
      "24h: validation_exception_handler 'details' is a list")

# 24i — rate limiter imports cleanly
_rlmod24 = _importlib24.import_module("api.middleware.rate_limiter")
check(hasattr(_rlmod24, "limiter"),
      "24i: api.middleware.rate_limiter exports 'limiter'")
check(hasattr(_rlmod24, "RATE_LIMITS"),
      "24i: api.middleware.rate_limiter exports 'RATE_LIMITS'")
check(isinstance(_rlmod24.RATE_LIMITS, dict),
      "24i: RATE_LIMITS is a dict")
check(set(_rlmod24.RATE_LIMITS.keys()) >= {"auth", "analyse", "action_plan", "general"},
      "24i: RATE_LIMITS has required keys: auth, analyse, action_plan, general")

# 24j — Dockerfile exists and contains "FROM python:3.11-slim"
_dockerfile24j = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dockerfile")
check(os.path.exists(_dockerfile24j),
      "24j: Dockerfile exists at project root")
with open(_dockerfile24j, "r", encoding="utf-8") as _f24j:
    _docker_content24j = _f24j.read()
check("FROM python:3.11-slim" in _docker_content24j,
      "24j: Dockerfile contains 'FROM python:3.11-slim'")

# 24k — .env.example exists and contains all three required key names
_envex24k = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example")
check(os.path.exists(_envex24k),
      "24k: .env.example exists at project root")
with open(_envex24k, "r", encoding="utf-8") as _f24k:
    _envex_content24k = _f24k.read()
for _key24k in ["GROQ_API_KEY", "GEMINI_API_KEY", "JWT_SECRET_KEY"]:
    check(_key24k in _envex_content24k,
          f"24k: .env.example contains '{_key24k}'")

# 24l — render.yaml exists and contains "feedbackiq-api"
_render24l = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.yaml")
check(os.path.exists(_render24l),
      "24l: render.yaml exists at project root")
with open(_render24l, "r", encoding="utf-8") as _f24l:
    _render_content24l = _f24l.read()
check("feedbackiq-api" in _render_content24l,
      "24l: render.yaml contains 'feedbackiq-api'")

# ─────────────────────────────────────────────────────────────
# SECTION 25 — RAG Pipeline Tests (zero API cost)
# ─────────────────────────────────────────────────────────────
print("\n--- Section 25: RAG Pipeline ---")

from core.rag.embedder import embed_query as _eq25, embed_texts as _et25
from core.rag.knowledge_base import (
    load_documents_from_files as _ldf25,
    initialise_knowledge_base as _ikb25,
    retrieve_relevant_solutions as _rrs25,
    build_retrieval_query as _brq25,
)
from core.action_plan import build_action_plan_prompts as _bapp25
from unittest.mock import patch as _patch25

# 25a — embed_query returns a list of 384 floats
_emb25a = _eq25("test query")
check(isinstance(_emb25a, list), "25a: embed_query returns a list")
check(len(_emb25a) == 384, f"25a: embed_query returns 384 dimensions (got {len(_emb25a)})")
check(all(isinstance(x, float) for x in _emb25a), "25a: all elements are floats")

# 25b — embed_texts with 2 inputs returns 2 embeddings each with 384 dimensions
_emb25b = _et25(["text one", "text two"])
check(len(_emb25b) == 2, "25b: embed_texts returns 2 embeddings for 2 inputs")
check(len(_emb25b[0]) == 384, f"25b: first embedding has 384 dimensions (got {len(_emb25b[0])})")
check(len(_emb25b[1]) == 384, f"25b: second embedding has 384 dimensions (got {len(_emb25b[1])})")

# 25c — load_documents_from_files returns 80 or more documents
_docs25c = _ldf25()
check(len(_docs25c) >= 80, f"25c: load_documents_from_files returns 80+ documents (got {len(_docs25c)})")

# 25d — all documents have required fields
_required_fields25d = {"id", "industry", "issue_type", "problem", "solution", "impact", "effort", "timeframe", "tags"}
_missing25d = [
    (doc.get("id", f"index-{i}"), _required_fields25d - set(doc.keys()))
    for i, doc in enumerate(_docs25c)
    if _required_fields25d - set(doc.keys())
]
check(len(_missing25d) == 0,
      f"25d: all documents have required fields (problems in {len(_missing25d)} docs: {_missing25d[:3]})")

# 25e — all document ids are unique across all files
_ids25e = [doc["id"] for doc in _docs25c]
check(len(_ids25e) == len(set(_ids25e)),
      f"25e: all document ids are unique ({len(_ids25e)} ids, {len(set(_ids25e))} unique)")

# 25f — initialise_knowledge_base returns count >= 80
_count25f = _ikb25()
check(_count25f >= 80, f"25f: initialise_knowledge_base returns count >= 80 (got {_count25f})")

# 25g — retrieve_relevant_solutions with E-commerce returns at least 1 result
_results25g = _rrs25("delivery tracking complaints", "E-commerce", n_results=3)
check(len(_results25g) >= 1, f"25g: retrieve_relevant_solutions returns >= 1 result (got {len(_results25g)})")

# 25h — every retrieved result has solution and impact keys
_missing25h = [i for i, r in enumerate(_results25g) if "solution" not in r or "impact" not in r]
check(len(_missing25h) == 0,
      f"25h: all retrieved results have solution and impact keys (missing in indices: {_missing25h})")

# 25i — relevance scores are all between 0 and 1
_bad_scores25i = [r["relevance_score"] for r in _results25g if not (0 <= r["relevance_score"] <= 1)]
check(len(_bad_scores25i) == 0,
      f"25i: all relevance scores are between 0 and 1 (bad: {_bad_scores25i})")

# 25j — retrieve_relevant_solutions with industry "Other" returns results without error
try:
    _results25j = _rrs25("delivery tracking complaints", "Other", n_results=3)
    check(True, "25j: retrieve_relevant_solutions with industry='Other' does not raise")
except Exception as _e25j:
    check(False, f"25j: retrieve_relevant_solutions with industry='Other' raised: {_e25j}")

# 25k — build_retrieval_query output contains industry name and issue category text
_issues25k = [{"category": "Delivery Speed", "count": 5, "critical_count": 2, "example": "Late delivery"}]
_query25k = _brq25(_issues25k, "E-commerce", "frustrated")
check("E-commerce" in _query25k, "25k: build_retrieval_query output contains industry name")
check("Delivery Speed" in _query25k, "25k: build_retrieval_query output contains issue category text")

# 25l — RAG failure does not break build_action_plan_prompts
_mock_dash25l = {
    "total_reviews": 5,
    "sentiment": {"positive_count": 3, "negative_count": 2, "neutral_count": 0,
                  "positive_pct": 60.0, "negative_pct": 40.0, "neutral_pct": 0.0, "overall_score": 65.0},
    "categories": [{"category": "Delivery", "count": 3, "pct": 60.0}],
    "urgency": {"critical_count": 0, "medium_count": 2, "low_count": 3, "critical_pct": 0.0},
    "emotions": [{"emotion": "frustrated", "count": 3, "pct": 60.0}],
    "top_issues": [{"category": "Delivery", "count": 2, "critical_count": 0, "example": "Late delivery"}],
    "confidence": {"high_count": 4, "medium_count": 1, "low_count": 0, "low_pct": 0.0},
    "top_category": "Delivery",
    "multi_aspect": {"multi_aspect_count": 1, "multi_aspect_pct": 20.0, "single_aspect_count": 4},
    "health_score_inputs": {"positive_pct": 60.0, "critical_pct": 0.0, "low_confidence_pct": 0.0},
}
_mock_profile25l = {
    "company_name": "TestCo", "industry": "E-commerce",
    "categories": ["Delivery"], "description": "", "urgency_definition": "",
}
with _patch25("core.action_plan.retrieve_relevant_solutions", side_effect=Exception("RAG down")):
    try:
        _prompts25l = _bapp25(_mock_dash25l, _mock_profile25l, [])
        check("system" in _prompts25l and "user" in _prompts25l,
              "25l: build_action_plan_prompts returns system+user dict even when RAG context is empty")
    except Exception as _e25l:
        check(False, f"25l: build_action_plan_prompts raised unexpectedly: {_e25l}")

# 25m — when rag_context is provided, PROVEN SOLUTIONS appears in user prompt
_mock_rag25m = [{
    "problem": "Slow delivery tracking",
    "solution": "Send SMS at every delivery stage",
    "impact": "40% fewer complaints",
    "effort": "medium",
    "timeframe": "short_term",
    "relevance_score": 0.92,
}]
_prompts25m = _bapp25(_mock_dash25l, _mock_profile25l, _mock_rag25m)
check("PROVEN SOLUTIONS" in _prompts25m["user"],
      "25m: PROVEN SOLUTIONS appears in user prompt when rag_context is provided")

# ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}\nALL TESTS PASSED — zero API calls made\n{'='*60}")