import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import google.generativeai as genai
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL
from .prompt_builder import build_prompt_pair
from .validator import validate_batch_response


groq_client = Groq(api_key=GROQ_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MAX_RETRIES = 2
# Delays (seconds) between successive Groq or Gemini rate-limit retries.
# Three retries → 2 s, 4 s, 8 s before declaring a provider exhausted.
_BACKOFFS = [2, 4, 8]
# How long to wait before the single last-resort attempt when both providers
# are rate-limited on the same batch.
_LAST_RESORT_WAIT = 10


def build_progress_summary(
    results_so_far: list, total_batches: int, completed_batches: int, failed_count: int
) -> dict:
    classified = len(results_so_far)
    pct = round((completed_batches / total_batches) * 100) if total_batches else 0

    positive = sum(1 for r in results_so_far if r.get("sentiment") == "positive")
    negative = sum(1 for r in results_so_far if r.get("sentiment") == "negative")
    critical = sum(1 for r in results_so_far if r.get("urgency") == "critical")

    return {
        "completed_batches": completed_batches,
        "total_batches": total_batches,
        "classified_so_far": classified,
        "failed_count": failed_count,
        "pct_complete": pct,
        "positive_so_far": positive,
        "negative_so_far": negative,
        "critical_so_far": critical,
    }


def is_rate_limit_error(error_str: str) -> bool:
    error_lower = error_str.lower()
    return (
        "rate_limit_exceeded" in error_lower
        or "429" in error_str
        or "tokens per day" in error_lower
    )


def call_groq(system_prompt: str, user_prompt: str) -> str:
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def call_gemini(system_prompt: str, user_prompt: str) -> str:
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config={
            "temperature": 0.0,
            "response_mime_type": "application/json",
        },
    )
    response = model.generate_content(user_prompt)
    return response.text


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _attempt(
    system_prompt: str,
    user_prompt: str,
    use_gemini: bool,
    batch_ids: list,
    allowed_categories: list,
) -> tuple:
    """
    Single LLM call → validate → remap local ids to original batch ids.
    Returns: (ok: bool, data: list|str, rate_limited: bool, provider: str)
    """
    provider = "gemini" if use_gemini else "groq"
    try:
        raw = (
            call_gemini(system_prompt, user_prompt)
            if use_gemini
            else call_groq(system_prompt, user_prompt)
        )

        validation = validate_batch_response(
            raw_response=raw,
            expected_count=len(batch_ids),
            allowed_categories=allowed_categories,
        )
        if not validation["success"]:
            return False, validation["error"], False, provider

        results = validation["results"]
        for r in results:
            lid = r["id"]
            if lid < 1 or lid > len(batch_ids):
                return (
                    False,
                    f"Model returned out-of-range id {lid} "
                    f"for a batch of {len(batch_ids)} reviews.",
                    False,
                    provider,
                )
            r["id"] = batch_ids[lid - 1]

        return True, results, False, provider

    except Exception as e:
        err = str(e)
        return False, err, is_rate_limit_error(err), provider


def _run_with_backoff(
    system_prompt: str,
    base_user_prompt: str,
    use_gemini: bool,
    batch_ids: list,
    allowed_categories: list,
) -> tuple:
    """
    Try one provider with exponential backoff on rate-limit errors and
    correction-prefix retries on validation failures.

    Rate-limit retries: up to len(_BACKOFFS) retries with delays _BACKOFFS[i].
    Validation retries: up to MAX_RETRIES with a 1 s delay (Groq only; Gemini
    already enforces JSON via response_mime_type so correction adds no value).

    Returns: (ok: bool, data: list|str, all_rate_limited: bool, provider: str)
    """
    last_err = None
    last_was_rate_limit = False
    backoff_idx = 0
    correction_tries = 0

    while True:
        user_prompt = base_user_prompt
        if (
            not use_gemini
            and last_err
            and not last_was_rate_limit
            and correction_tries > 0
        ):
            user_prompt = (
                f"CORRECTION REQUIRED: Your previous response was rejected.\n"
                f"Reason: {last_err}\n"
                f"Return ONLY valid JSON. Use ONLY the allowed values "
                f"from the system prompt. No explanation, no extra text.\n\n"
                f"{base_user_prompt}"
            )

        ok, data, rate_limited, provider = _attempt(
            system_prompt, user_prompt, use_gemini, batch_ids, allowed_categories
        )

        if ok:
            return True, data, False, provider

        last_err = data
        last_was_rate_limit = rate_limited

        if rate_limited:
            if backoff_idx < len(_BACKOFFS):
                time.sleep(_BACKOFFS[backoff_idx])
                backoff_idx += 1
            else:
                return False, last_err, True, provider
        else:
            correction_tries += 1
            if correction_tries <= MAX_RETRIES:
                time.sleep(1)
            else:
                return False, last_err, False, provider


# ─── Public API ───────────────────────────────────────────────────────────────

def classify_batch(batch: list, profile: dict) -> dict:
    batch_ids = [r["id"] for r in batch]
    allowed_categories = profile["categories"]
    prompt_pair = build_prompt_pair(profile, batch)
    system_prompt = prompt_pair["system"]
    base_user_prompt = prompt_pair["user"]

    # Phase 1 — Groq with exponential backoff on rate limits.
    ok, data, groq_rate_limited, provider = _run_with_backoff(
        system_prompt, base_user_prompt, False, batch_ids, allowed_categories
    )
    if ok:
        return {
            "success": True,
            "results": data,
            "batch_ids": batch_ids,
            "error": None,
            "provider": provider,
        }
    if not groq_rate_limited:
        return {
            "success": False,
            "results": [],
            "batch_ids": batch_ids,
            "error": data,
        }

    # Phase 2 — Groq exhausted due to rate limits → try Gemini.
    if not GEMINI_API_KEY:
        return {
            "success": False,
            "results": [],
            "batch_ids": batch_ids,
            "error": "Groq rate limit hit and no Gemini API key configured for fallback.",
        }

    ok, data, gemini_rate_limited, provider = _run_with_backoff(
        system_prompt, base_user_prompt, True, batch_ids, allowed_categories
    )
    if ok:
        return {
            "success": True,
            "results": data,
            "batch_ids": batch_ids,
            "error": None,
            "provider": provider,
        }
    if not gemini_rate_limited:
        return {
            "success": False,
            "results": [],
            "batch_ids": batch_ids,
            "error": data,
        }

    # Phase 3 — Both providers rate-limited. Wait 10 s then one final attempt.
    time.sleep(_LAST_RESORT_WAIT)
    ok, data, _, provider = _attempt(
        system_prompt, base_user_prompt, False, batch_ids, allowed_categories
    )
    if ok:
        return {
            "success": True,
            "results": data,
            "batch_ids": batch_ids,
            "error": None,
            "provider": provider,
        }

    return {
        "success": False,
        "results": [],
        "batch_ids": batch_ids,
        "error": f"Both Groq and Gemini hit rate limits after backoff. Last error: {data}",
    }


def classify_all_batches(batches: list, profile: dict, progress_callback=None) -> dict:
    all_results = []
    failed_batches = []
    gemini_fallback_count = 0
    total_batches = len(batches)

    for i, batch in enumerate(batches):
        result = classify_batch(batch, profile)

        if result["success"]:
            all_results.extend(result["results"])
            if result.get("provider") == "gemini":
                gemini_fallback_count += 1
        else:
            failed_batches.append(
                {
                    "batch_number": i + 1,
                    "batch_ids": result["batch_ids"],
                    "error": result["error"],
                }
            )

        completed = i + 1
        failed_count = sum(len(b["batch_ids"]) for b in failed_batches)

        if progress_callback:
            summary = build_progress_summary(
                results_so_far=all_results,
                total_batches=total_batches,
                completed_batches=completed,
                failed_count=failed_count,
            )
            progress_callback(summary)

    return {
        "all_results": all_results,
        "failed_batches": failed_batches,
        "total_classified": len(all_results),
        "total_failed": sum(len(b["batch_ids"]) for b in failed_batches),
        "gemini_fallback_count": gemini_fallback_count,
    }
