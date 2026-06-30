"""
Generates a structured AI business action plan from aggregated dashboard statistics.
Sends only pre-computed metrics (never raw review text) to the LLM, then validates
the structured JSON response against Pydantic models before returning it to the caller.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import json
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

import google.generativeai as genai
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL
from .classifier import is_rate_limit_error
from core.rag.knowledge_base import retrieve_relevant_solutions, build_retrieval_query, retrieve_per_issue
from core.logger import logger


_groq_client = Groq(api_key=GROQ_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MAX_RETRIES = 4


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


# ─── Generic-phrase detector (used in validation) ─────────────────────────────

GENERIC_PHRASES = [
    "optimization project",
    "streamline",
    "leverage",
    "synergies",
    "best practices",
    "going forward",
    "at the end of the day",
    "moving forward",
    "enhance overall",
    "improve overall",
    "various measures",
    "take steps to",
    "work towards",
    "focus on improving",
]

# Concrete action verbs that signal a specific, doable quick win.
_QUICK_WIN_VERBS = [
    "implement", "send", "add", "create", "set up",
    "enable", "switch", "replace",
]

# Generic words stripped from customer examples before they become
# category-relevance anchors — they would match almost any text.
_GROUNDING_STOPWORDS = {
    "with", "that", "this", "have", "were", "was", "your", "you",
    "they", "them", "from", "when", "what", "which", "would", "could",
    "should", "work", "working", "very", "just", "more", "some", "been",
    "their", "there", "about", "into", "over", "than", "then", "only",
    "also", "such", "does", "did", "not", "but", "and", "the", "for",
}


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
        priority = (
            "URGENT — act this week"
            if issue.get("critical_count", 0) > 0
            else "Important — act this month"
        )
        lines.append(
            f"  {i}. {issue['category']}\n"
            f"     Negative reviews: {issue['count']}\n"
            f"     Critical urgency: {issue['critical_count']}\n"
            f"     Example customer quote: \"{example}\"\n"
            f"     Action priority: {priority}"
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

def build_action_plan_prompts(dashboard_data: dict, profile: dict, rag_context: Dict[str, List[Dict]] = None) -> dict:
    if rag_context is None:
        rag_context = {}
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

    rag_section = ""
    if rag_context:
        category_blocks = []
        for category, docs in rag_context.items():
            if not docs:
                continue
            doc_lines = []
            for i, doc in enumerate(docs, 1):
                relevance_pct = round(doc.get("relevance_score", 0) * 100)
                timeframe = doc.get("timeframe", "short_term").replace("_", " ")
                doc_lines.append(
                    f"  Solution {i} (relevance: {relevance_pct}%):\n"
                    f"  Problem: {doc.get('problem', '')}\n"
                    f"  Proven approach: {doc.get('solution', '')}\n"
                    f"  Impact: {doc.get('impact', '')}\n"
                    f"  Effort: {doc.get('effort', '')} | Timeframe: {timeframe}"
                )
            if doc_lines:
                category_blocks.append(
                    f"For {category.upper()} complaints:\n"
                    + "\n\n".join(doc_lines)
                )
        if category_blocks:
            rag_section = (
                "\n\nPROVEN SOLUTIONS — MATCHED TO EACH ISSUE AREA\n\n"
                + "\n\n".join(category_blocks)
                + "\n\nMATCHING RULE: For each recommendation, use the proven solutions listed under "
                "that exact category above. Do not mix solutions across categories. If a category "
                "has no proven solutions listed, generate that recommendation from the customer "
                "data alone — be specific to what the customers actually said, and do not invent "
                "generic advice or borrow solutions from unrelated categories."
            )

    data_quality_warning = ""
    if low_conf_pct > 25:
        data_quality_warning = (
            f"\n⚠ WARNING: {low_conf_pct:.1f}% of classifications are low-confidence. "
            f"Treat findings from this dataset with caution."
        )

    system_prompt = f"""You are a sharp, data-driven business consultant writing an action plan for a real business. You have customer feedback statistics. Your job is to write specific, actionable recommendations that a business owner can act on THIS WEEK — not generic management consulting filler.

GROUNDING RULE: Every recommendation must cite specific numbers from the data snapshot. Every action must be concrete enough that a manager knows exactly what to do on Monday morning. Never write phrases like "implement an optimization project", "streamline processes", "leverage synergies", or any other vague corporate language. If you cannot write a specific action, write nothing.

BAD example (never write this):
"Implement a delivery speed optimization project to reduce delivery times by streamlining logistics and improving warehouse management."

GOOD example (write like this):
"Delivery Speed has 5 negative reviews — 2 explicitly mention inconsistent tracking updates leaving customers in the dark. Fix: send automated SMS/email updates at each shipping stage. This costs nothing if you use your existing courier's API. Target: zero 'where is my order' complaints within 30 days."

TONE: Direct, practical, respectful. Write like a trusted advisor not a consultant billing by the hour.

OUTPUT FORMAT:
First write a <thinking> block where you analyse the data — what is the single biggest problem, what is driving it, what is the easiest win, what is being ignored that matters. Be specific about the numbers.
Then output ONE valid JSON object matching the schema exactly. No markdown fences. No text after the JSON.

JSON SCHEMA:
{{
  "health_score": <integer 0-100, pre-computed — copy from DATA SNAPSHOT exactly>,
  "health_label": <"Strong" | "Mixed" | "Needs Attention" | "Critical", pre-computed — copy from DATA SNAPSHOT exactly>,
  "executive_summary": <string, exactly 2 sentences, must cite at least 2 numbers from the data. When citing issue numbers in the executive summary, always distinguish between total negative reviews and critical-urgency reviews. Use the format 'X negative reviews, Y of them critical' rather than conflating the two numbers. For example: '5 negative delivery reviews, 3 of them critical' — never just '3 reviews citing delivery' when the negative count is actually higher. Always lead with the total negative count for an issue, then note how many are critical if any.>,
  "key_strengths": [<string, one sentence each citing a specific number> ...],
  "recommendations": [
    {{
      "rank": <integer starting at 1>,
      "title": <string, short action-oriented title>,
      "rationale": <string, one sentence citing a specific number from the data AND the example customer quote>,
      "action": <string, 2-3 concrete sentences on EXACTLY what to do — no vague language>,
      "impact": <"high" | "medium" | "low">,
      "effort": <"low" | "medium" | "high">,
      "timeframe": <"immediate" | "short_term" | "long_term">
    }}
  ],
  "quick_win": {{
    "title": <string, short title>,
    "description": <string, 1-2 sentences referencing a specific issue from the data>,
    "expected_outcome": <string, one sentence with a measurable target>
  }},
  "data_quality_note": <string or null — null if low_confidence_pct <= 25>
}}

Rules: recommendations must have 3 to 5 items. impact/effort/timeframe must use exact enum values. health_score and health_label must use the exact pre-computed values provided — do not recompute them.

Company context: {company_name} is a {industry} business."""

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

TOP NEGATIVE ISSUE AREAS (with example customer quotes — use these in your recommendations)
{top_issues_block}{rag_section}

WHAT CUSTOMERS ARE FEELING:
{emotions_block}

The dominant emotion tells you the severity. Angry customers need immediate acknowledgment. Disappointed customers need process fixes. Frustrated customers need better communication.

MULTI-ASPECT COMPLEXITY
- Reviews addressing multiple issues: {multi_aspect_count} ({multi_aspect_pct:.1f}%)
- Reviews addressing single issue: {single_aspect_count}

DATA CONFIDENCE
- High confidence classifications: {high_conf}
- Low confidence classifications: {low_conf} ({low_conf_pct:.1f}%){data_quality_warning}

COMPANY CONTEXT
{company_context_block}

SPECIFICITY REQUIREMENT: Your recommendations must reference the actual example feedback quoted above. If a customer said "tracking updates were inconsistent" your recommendation must address tracking specifically — not "delivery processes" generically. A business owner reading this should think "yes, this was written about MY customers" not "this could be about anyone."

Generate the action plan JSON now. Be specific. Be direct. Be useful."""

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
        max_tokens=3000,
    )
    return response.choices[0].message.content


def call_gemini_action_plan(system_prompt: str, user_prompt: str) -> str:
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config={
            "temperature": 0.0,
            "max_output_tokens": 3000,
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

    # Reject boilerplate responses — force the LLM to be specific
    result_dict = result.model_dump()
    all_action_text = " ".join(
        r["action"] + " " + r["rationale"]
        for r in result_dict["recommendations"]
    ).lower()

    generic_count = sum(1 for phrase in GENERIC_PHRASES if phrase in all_action_text)
    if generic_count >= 3:
        return {
            "success": False,
            "result": None,
            "error": (
                f"Response contained {generic_count} generic phrases — retrying for specificity"
            ),
        }

    return {"success": True, "result": result, "error": None}


# ─── Grounding verification (pure Python, zero LLM calls) ─────────────────────

def _verify_grounding(result_dict: dict, dashboard_data: dict) -> tuple:
    """
    Quality gate run after Pydantic validation. Verifies a generated action plan
    is actually grounded in the data rather than generic filler. Pure string and
    number checking — zero LLM calls, microsecond cost.

    Returns (passed: bool, reason: str). On the first failing check it returns
    (False, <specific reason>); if every check passes it returns (True, "passed").
    """
    recommendations = result_dict.get("recommendations", []) or []
    quick_win = result_dict.get("quick_win", {}) or {}

    # 1. Number grounding — grounded rationales cite counts or percentages.
    rationales_with_numbers = sum(
        1 for r in recommendations
        if re.search(r"\d", r.get("rationale", ""))
    )
    if rationales_with_numbers < 3:
        return (
            False,
            f"Only {rationales_with_numbers} recommendation rationale(s) cite a "
            f"number; at least 3 must reference specific counts or percentages "
            f"from the data.",
        )

    # 2. Generic phrase check across all rationale + action text combined.
    combined_text = " ".join(
        (r.get("rationale", "") + " " + r.get("action", ""))
        for r in recommendations
    ).lower()
    generic_count = sum(
        1 for phrase in GENERIC_PHRASES if phrase in combined_text
    )
    if generic_count >= 3:
        return (
            False,
            f"Found {generic_count} generic phrases across the recommendations; "
            f"rewrite with specific, concrete language instead of business filler.",
        )

    # 3. Category relevance — recommendations must stay anchored to the real
    #    issues instead of drifting into generic advice. Anchor terms come from
    #    the actual top-issue category names and customer examples.
    top_issues = dashboard_data.get("top_issues", []) or []
    relevant_terms = set()
    for issue in top_issues:
        category = str(issue.get("category", "")).lower()
        for word in re.findall(r"[a-z]+", category):
            if len(word) > 3:
                relevant_terms.add(word)
        example = str(issue.get("example", "")).lower()
        for word in re.findall(r"[a-z]+", example):
            if len(word) > 3 and word not in _GROUNDING_STOPWORDS:
                relevant_terms.add(word)

    if relevant_terms and recommendations:
        matched = 0
        for r in recommendations:
            text = (r.get("title", "") + " " + r.get("action", "")).lower()
            if any(term in text for term in relevant_terms):
                matched += 1
        if matched < len(recommendations) / 2.0:
            return (
                False,
                f"Only {matched} of {len(recommendations)} recommendations "
                f"reference the actual issue categories; they drifted away from "
                f"the real customer feedback.",
            )

    # 4. Quick win specificity — must cite a number or a concrete action verb.
    qw_desc = str(quick_win.get("description", "")).lower()
    has_number = bool(re.search(r"\d", qw_desc))
    has_verb = any(verb in qw_desc for verb in _QUICK_WIN_VERBS)
    if not (has_number or has_verb):
        return (
            False,
            "Quick win description is vague; it must cite a number or a concrete "
            "action (implement, send, add, create, set up, enable, switch, "
            "replace).",
        )

    return (True, "passed")


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
        top_issues = dashboard_data.get("top_issues", [])
        industry = profile.get("industry", "General")

        rag_context_per_issue = {}
        try:
            rag_context_per_issue = retrieve_per_issue(
                top_issues, industry, n_per_issue=2)
            total = sum(len(v) for v in
                        rag_context_per_issue.values())
            logger.info(
                f"RAG per-issue retrieval: {total} docs "
                f"across {len(rag_context_per_issue)} issues")
        except Exception as e:
            logger.warning(f"RAG per-issue failed: {e}")
            rag_context_per_issue = {}

        prompts = build_action_plan_prompts(dashboard_data, profile, rag_context_per_issue)
        system_prompt = prompts["system"]
        user_prompt = prompts["user"]

        use_gemini = False
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            current_user_prompt = user_prompt

            if attempt > 0 and last_error:
                if last_error.startswith("GROUNDING: "):
                    reason = last_error[len("GROUNDING: "):]
                    retry_prefix = (
                        f"PREVIOUS ATTEMPT REJECTED: {reason} You must cite specific "
                        f"numbers from the data in each rationale and reference the actual "
                        f"issue categories. Do not use generic business language.\n\n"
                    )
                else:
                    retry_prefix = (
                        f"RETRY ATTEMPT {attempt}. Previous attempt failed because: {last_error}\n\n"
                        f"Critical reminder: Output ONLY valid JSON after the </thinking> tag. "
                        f"No markdown. No code fences. The JSON must be complete — do not truncate it. "
                        f"If you are running long, write shorter recommendation actions but complete "
                        f"the full JSON structure.\n\n"
                    )
                current_user_prompt = f"{retry_prefix}{user_prompt}"

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
                    result_dict = validation["result"].model_dump()

                    # Grounding verification — another reason a retry can fire,
                    # within the existing retry budget. Zero extra LLM calls
                    # unless it forces a retry.
                    grounded, ground_reason = _verify_grounding(
                        result_dict, dashboard_data)

                    if grounded:
                        return {
                            "success": True,
                            "result": result_dict,
                            "health_score": health_score,
                            "health_label": health_label,
                            "provider": provider,
                            "error": None,
                        }

                    if attempt < MAX_RETRIES:
                        last_error = f"GROUNDING: {ground_reason}"
                        logger.info(
                            f"Grounding check failed on attempt {attempt + 1}, "
                            f"retrying: {ground_reason}")
                        continue

                    # No retries left — a mediocre plan beats no plan, but flag
                    # it so we can monitor quality.
                    logger.warning(
                        f"Action plan did not pass grounding verification after "
                        f"all retries: {ground_reason}")
                    return {
                        "success": True,
                        "result": result_dict,
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
