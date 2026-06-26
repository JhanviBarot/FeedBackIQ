import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import google.generativeai as genai
from groq import AsyncGroq

from config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL
from .prompt_builder import build_prompt_pair
from .validator import validate_batch_response
from .classifier import (
    call_gemini,
    build_progress_summary,
    is_rate_limit_error,
    MAX_RETRIES,
    _BACKOFFS,
    _LAST_RESORT_WAIT,
)

_async_groq_client = AsyncGroq(api_key=GROQ_API_KEY)


async def call_groq_async(system_prompt: str, user_prompt: str) -> str:
    response = await _async_groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=2048,
    )
    return response.choices[0].message.content


async def call_gemini_async(system_prompt: str, user_prompt: str) -> str:
    # Gemini SDK has no native async client — wrap the sync call in a thread.
    def _sync():
        return call_gemini(system_prompt, user_prompt)
    return await asyncio.to_thread(_sync)


# ─── Internal async helpers ───────────────────────────────────────────────────

async def _attempt_async(
    system_prompt: str,
    user_prompt: str,
    use_gemini: bool,
    batch_ids: list,
    allowed_categories: list,
) -> tuple:
    provider = "gemini" if use_gemini else "groq"
    try:
        raw = (
            await call_gemini_async(system_prompt, user_prompt)
            if use_gemini
            else await call_groq_async(system_prompt, user_prompt)
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


async def _run_with_backoff_async(
    system_prompt: str,
    base_user_prompt: str,
    use_gemini: bool,
    batch_ids: list,
    allowed_categories: list,
) -> tuple:
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

        ok, data, rate_limited, provider = await _attempt_async(
            system_prompt, user_prompt, use_gemini, batch_ids, allowed_categories
        )

        if ok:
            return True, data, False, provider

        last_err = data
        last_was_rate_limit = rate_limited

        if rate_limited:
            if backoff_idx < len(_BACKOFFS):
                await asyncio.sleep(_BACKOFFS[backoff_idx])
                backoff_idx += 1
            else:
                return False, last_err, True, provider
        else:
            correction_tries += 1
            if correction_tries <= MAX_RETRIES:
                await asyncio.sleep(1)
            else:
                return False, last_err, False, provider


# ─── Public async API ─────────────────────────────────────────────────────────

async def classify_batch_async(
    batch: list, profile: dict, semaphore: asyncio.Semaphore, use_gemini: bool = False
) -> dict:
    batch_ids = [r["id"] for r in batch]
    allowed_categories = profile["categories"]
    prompt_pair = build_prompt_pair(profile, batch)
    system_prompt = prompt_pair["system"]
    base_user_prompt = prompt_pair["user"]

    async with semaphore:
        # Phase 1 — Groq with exponential backoff on rate limits.
        ok, data, groq_rate_limited, provider = await _run_with_backoff_async(
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

        ok, data, gemini_rate_limited, provider = await _run_with_backoff_async(
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

        # Phase 3 — Both providers rate-limited. Wait then one final attempt.
        await asyncio.sleep(_LAST_RESORT_WAIT)
        ok, data, _, provider = await _attempt_async(
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


async def classify_all_batches_async(
    batches: list, profile: dict, progress_callback=None
) -> tuple:
    """
    Run all batches concurrently with a semaphore cap of 3 concurrent API calls.
    Returns: (all_results, failed_batches, total_classified, total_failed, gemini_fallback_count)
    """
    if not batches:
        return ([], [], 0, 0, 0)

    # Semaphore value of 3 is critical — Groq's rate limit is per-minute tokens,
    # so more than 3 concurrent calls causes burst 429s.
    semaphore = asyncio.Semaphore(3)
    total_batches = len(batches)
    all_results = []
    failed_batches = []
    gemini_fallback_count = 0

    start = time.time()

    tasks = [classify_batch_async(batch, profile, semaphore) for batch in batches]
    batch_outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(batch_outcomes):
        if isinstance(result, Exception):
            failed_batches.append({
                "batch_number": i + 1,
                "batch_ids": [r["id"] for r in batches[i]],
                "error": str(result),
            })
        elif result["success"]:
            all_results.extend(result["results"])
            if result.get("provider") == "gemini":
                gemini_fallback_count += 1
        else:
            failed_batches.append({
                "batch_number": i + 1,
                "batch_ids": result["batch_ids"],
                "error": result["error"],
            })

        if progress_callback:
            failed_count = sum(len(b["batch_ids"]) for b in failed_batches)
            summary = build_progress_summary(
                results_so_far=all_results,
                total_batches=total_batches,
                completed_batches=i + 1,
                failed_count=failed_count,
            )
            progress_callback(summary)

    duration = time.time() - start
    total_classified = len(all_results)
    total_failed = sum(len(b["batch_ids"]) for b in failed_batches)

    print(
        f"Async classification complete: {total_classified} reviews in {duration:.1f}s "
        f"({len(batches)} batches, max 3 concurrent)"
    )

    return (all_results, failed_batches, total_classified, total_failed, gemini_fallback_count)
