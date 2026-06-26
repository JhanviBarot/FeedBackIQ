"""
Generates a structured AI business action plan from aggregated dashboard statistics.
Sends only pre-computed metrics (never raw review text) to the LLM, then validates
the structured JSON response against Pydantic models before returning it to the caller.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import json
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

import google.generativeai as genai
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL
from .classifier import is_rate_limit_error


_groq_client = Groq(api_key=GROQ_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MAX_RETRIES = 2


# ─── Pydantic Models ───────────────────────────────────────────────────────────

class Recommendation(BaseModel):
    rank: int
    title: str
    rationale: str
    action: str
    impact: Literal["high", "medium", "low"]
    effort: Literal["low", "medium", "high"]
    timeframe: Literal["immediate", "short_term", "long_term"]


class QuickWin(BaseModel):
    title: str
    description: str
    expected_outcome: str


class ActionPlanResult(BaseModel):
    health_score: int = Field(ge=0, le=100)
    health_label: Literal["Strong", "Mixed", "Needs Attention", "Critical"]
    executive_summary: str
    key_strengths: List[str]
    recommendations: List[Recommendation] = Field(min_length=3, max_length=5)
    quick_win: QuickWin
    data_quality_note: Optional[str]


_SCHEMA_STRING = """{
  "health_score": <integer 0-100, pre-computed — copy from DATA SNAPSHOT exactly>,
  "health_label": <"Strong" | "Mixed" | "Needs Attention" | "Critical", pre-computed — copy from DATA SNAPSHOT exactly>,
  "executive_summary": <string, exactly 2 sentences, must cite at least 2 numbers from the data>,
  "key_strengths": [<string, one sentence each citing a specific number> ...],
  "recommendations": [
    {
      "rank": <integer starting at 1>,
      "title": <string, short action-oriented title>,
      "rationale": <string, one sentence citing a specific number from the data>,
      "action": <string, 2-3 concrete sentences on what to do>,
      "impact": <"high" | "medium" | "low">,
      "effort": <"low" | "medium" | "high">,
      "timeframe": <"immediate" | "short_term" | "long_term">
    }
  ],
  "quick_win": {
    "title": <string, short title>,
    "description": <string, 1-2 sentences, must be genuinely actionable this week>,
    "expected_outcome": <string, one sentence on expected improvement>
  },
  "data_quality_note": <string or null — null if low_confidence_pct <= 25>
}"""


# ─── Health score computation (Python only — never delegate to LLM) ───────────

def compute_health_score(dashboard_data: dict) -> tuple:
    inputs = dashboard_data.get("health_score_inputs", {})
    positive_pct = inputs.get("positive_pct", 0.0)
    critical_pct = inputs.get("critical_pct", 0.0)
    low_pct = inputs.get("low_confidence_pct", 0.0)

    score = round(
        (positive_pct * 0.5)
        + ((100 - critical_pct) * 0.3)
        + ((100 - low_pct) * 0.2)
    )
    score = max(0, min(100, score))

    if score >= 75:
        label = "Strong"
    elif score >= 50:
        label = "Mixed"
    elif score >= 25:
        label = "Needs Attention"
    else:
        label = "Critical"

    return (score, label)


# ─── Prompt block formatters ───────────────────────────────────────────────────

def _format_categories_block(categories: list) -> str:
    lines = []
    for cat in categories:
        lines.append(
            f"  - {cat['category']}: {cat['count']} reviews ({cat['pct']:.1f}%)"
        )
    return "\n".join(lines) if lines else "  (no categories)"


def _format_top_issues_block(top_issues: list) -> str:
    lines = []
    for i, issue in enumerate(top_issues, 1):
        example = issue.get("example", "")
        lines.append(
            f"  {i}. {issue['category']} — {issue['count']} negative reviews, "
            f"{issue['critical_count']} critical, example: \"{example}\""
        )
    return "\n".join(lines) if lines else "  (no significant negative issues)"


def _format_emotions_block(emotions: list) -> str:
    lines = []
    for emo in emotions:
        lines.append(
            f"  - {emo['emotion'].capitalize()}: {emo['count']} reviews ({emo['pct']:.1f}%)"
        )
    return "\n".join(lines) if lines else "  (no emotion data)"


def _format_company_context(profile: dict) -> str:
    parts = [
        f"Company: {profile.get('company_name', 'Unknown')}",
        f"Industry: {profile.get('industry', 'Unknown')}",
    ]
    desc = profile.get("description")
    if desc:
        parts.append(f"Description: {desc}")
    urgency_def = profile.get("urgency_definition")
    if urgency_def:
        parts.append(f"What 'critical' means for this business: {urgency_def}")
    return "\n".join(parts)


# ─── Prompt builder ────────────────────────────────────────────────────────────

def build_action_plan_prompts(dashboard_data: dict, profile: dict) -> dict:
    health_score, health_label = compute_health_score(dashboard_data)

    sentiment = dashboard_data["sentiment"]
    urgency = dashboard_data["urgency"]
    confidence = dashboard_data["confidence"]
    multi_aspect = dashboard_data["multi_aspect"]

    positive_pct = sentiment["positive_pct"]
    positive_count = sentiment["positive_count"]
    negative_count = sentiment["negative_count"]
    neutral_count = sentiment["neutral_count"]
    negative_pct = sentiment["negative_pct"]
    neutral_pct = sentiment["neutral_pct"]
    overall_score = sentiment["overall_score"]

    critical_count = urgency["critical_count"]
    critical_pct = urgency["critical_pct"]
    medium_count = urgency["medium_count"]
    low_urg_count = urgency["low_count"]

    high_conf = confidence["high_count"]
    low_conf = confidence["low_count"]
    low_conf_pct = confidence["low_pct"]

    multi_aspect_count = multi_aspect["multi_aspect_count"]
    multi_aspect_pct = multi_aspect["multi_aspect_pct"]
    single_aspect_count = multi_aspect["single_aspect_count"]

    company_name = profile.get("company_name", "the company")
    industry = profile.get("industry", "Unknown")

    categories_block = _format_categories_block(dashboard_data["categories"])
    top_issues_block = _format_top_issues_block(dashboard_data["top_issues"])
    emotions_block = _format_emotions_block(dashboard_data["emotions"])
    company_context_block = _format_company_context(profile)

    data_quality_warning = ""
    if low_conf_pct > 25:
        data_quality_warning = (
            f"⚠ WARNING: {low_conf_pct:.1f}% of classifications are low-confidence. "
            f"Treat findings from this dataset with caution."
        )

    system_prompt = f"""You are a senior customer experience analyst generating a structured business intelligence report.

SCOPE: You have access ONLY to the data snapshot provided below. Do not reference anything about this company that is not in the data. Do not invent benchmarks, industry averages, or competitor comparisons unless explicitly provided.

GROUNDING RULE: Every claim in executive_summary, rationale, and action fields MUST cite a specific number from the DATA SNAPSHOT. If you cannot ground a claim in the data, do not make it.

TASK: Analyse the feedback data for {company_name}, a {industry} business. Generate a structured action plan following the exact JSON schema provided.

OUTPUT FORMAT:
1. First, write a <thinking> block where you reason through the key patterns in the data — what's working, what's failing, what's urgent, what's a quick win.
2. Then output ONE valid JSON object matching the schema exactly. No markdown fences. No preamble after the JSON.

JSON SCHEMA:
{_SCHEMA_STRING}

HARD RULES:
- JSON only after the </thinking> tag. No text before or after.
- Use only these allowed values for impact: "high", "medium", "low"
- Use only these allowed values for effort: "low", "medium", "high"
- Use only these allowed values for timeframe: "immediate", "short_term", "long_term"
- Recommendations must be ranked 1 (most impactful) to N (least impactful)
- executive_summary must be exactly 2 sentences
- key_strengths must be empty list [] if positive_pct < 30
- data_quality_note must be null if low_confidence_pct <= 25"""

    user_prompt = f"""DATA SNAPSHOT for {company_name} ({industry}):

OVERVIEW
- Total reviews analysed: {dashboard_data['total_reviews']}
- Overall sentiment score: {overall_score:.1f}/100
- Positive: {positive_count} reviews ({positive_pct:.1f}%)
- Negative: {negative_count} reviews ({negative_pct:.1f}%)
- Neutral: {neutral_count} reviews ({neutral_pct:.1f}%)

PRE-COMPUTED HEALTH SCORE
- Health Score: {health_score}/100 ({health_label})
  [Do not recompute this. Use these exact values.]

URGENCY BREAKDOWN
- Critical issues: {critical_count} reviews ({critical_pct:.1f}%)
- Medium urgency: {medium_count} reviews
- Low urgency: {low_urg_count} reviews

FEEDBACK CATEGORIES (sorted by volume)
{categories_block}

TOP NEGATIVE ISSUE AREAS
{top_issues_block}

EMOTION DISTRIBUTION
{emotions_block}

MULTI-ASPECT COMPLEXITY
- Reviews addressing multiple issues: {multi_aspect_count} ({multi_aspect_pct:.1f}%)
- Reviews addressing single issue: {single_aspect_count}

DATA CONFIDENCE
- High confidence classifications: {high_conf}
- Low confidence classifications: {low_conf} ({low_conf_pct:.1f}%)
{data_quality_warning}

COMPANY CONTEXT
{company_context_block}

Generate the action plan JSON now."""

    return {"system": system_prompt, "user": user_prompt}


# ─── LLM calls ────────────────────────────────────────────────────────────────

def call_groq_action_plan(system_prompt: str, user_prompt: str) -> str:
    response = _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=1500,
    )
    return response.choices[0].message.content


def call_gemini_action_plan(system_prompt: str, user_prompt: str) -> str:
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config={
            "temperature": 0.0,
            "max_output_tokens": 1500,
            "response_mime_type": "application/json",
        },
    )
    response = model.generate_content(user_prompt)
    return response.text


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_action_plan(raw_response: str) -> dict:
    cleaned = re.sub(
        r"<thinking>.*?</thinking>", "", raw_response, flags=re.DOTALL
    ).strip()

    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "result": None,
            "error": f"JSON parsing failed: {str(e)}",
        }

    try:
        result = ActionPlanResult(**parsed)
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"Schema validation failed: {str(e)}",
        }

    return {"success": True, "result": result, "error": None}


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_action_plan(dashboard_data: dict, profile: dict) -> dict:
    health_score, health_label = compute_health_score(dashboard_data)

    base_return = {
        "success": False,
        "result": None,
        "health_score": health_score,
        "health_label": health_label,
        "provider": None,
        "error": None,
    }

    try:
        prompts = build_action_plan_prompts(dashboard_data, profile)
        system_prompt = prompts["system"]
        user_prompt = prompts["user"]

        use_gemini = False
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            current_user_prompt = user_prompt

            if attempt > 0 and last_error:
                correction = (
                    f"Your previous response failed validation. "
                    f"Reason: {last_error}. "
                    f"Retry with valid JSON only — no thinking block, "
                    f"no markdown fences, no preamble."
                )
                current_user_prompt = f"{correction}\n\n{user_prompt}"

            try:
                if use_gemini:
                    if not GEMINI_API_KEY:
                        base_return["error"] = (
                            "Groq rate limit hit and no Gemini API key configured."
                        )
                        return base_return
                    raw = call_gemini_action_plan(system_prompt, current_user_prompt)
                    provider = "gemini"
                else:
                    raw = call_groq_action_plan(system_prompt, current_user_prompt)
                    provider = "groq"

                validation = validate_action_plan(raw)

                if validation["success"]:
                    result_obj = validation["result"]
                    return {
                        "success": True,
                        "result": result_obj.model_dump(),
                        "health_score": health_score,
                        "health_label": health_label,
                        "provider": provider,
                        "error": None,
                    }
                else:
                    last_error = validation["error"]

            except Exception as e:
                error_str = str(e)
                last_error = error_str

                if is_rate_limit_error(error_str) and not use_gemini:
                    use_gemini = True
                    continue

                if is_rate_limit_error(error_str) and use_gemini:
                    base_return["error"] = (
                        "Both Groq and Gemini hit rate limits. Try again later."
                    )
                    return base_return

        base_return["error"] = (
            f"Action plan generation failed after {MAX_RETRIES + 1} attempts. "
            f"Last error: {last_error}"
        )

    except Exception as e:
        base_return["error"] = f"Unexpected error: {str(e)}"

    return base_return
