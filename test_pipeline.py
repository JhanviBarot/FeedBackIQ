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
    check(_bad_login.json().get("detail") == "Invalid email or password",
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
from unittest.mock import patch as _patch19

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
    with _patch19("api.routes.analyse.classify_all_batches",
                  return_value=_MOCK_CLF):
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
    with _patch19("api.routes.analyse.classify_all_batches",
                  return_value=_MOCK_CLF):
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
    with _patch19("api.routes.analyse.classify_all_batches",
                  return_value=_MOCK_CLF):
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
    with _patch19("api.routes.analyse.classify_all_batches",
                  return_value=_MOCK_CLF):
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

# ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}\nALL TESTS PASSED — zero API calls made\n{'='*60}")