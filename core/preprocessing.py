import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import emoji
from difflib import SequenceMatcher
from config import MIN_REVIEWS, MAX_REVIEW_LENGTH, MIN_REVIEW_LENGTH, BATCH_SIZE

def convert_emojis(text: str) -> str:
    return emoji.demojize(text, delimiters=(" ", " "))

def normalize_text(text: str) -> str:
    # Remove control characters and non-printable characters
    # but preserve all normal language characters including Hindi, Arabic, Chinese etc.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Normalize curly quotes to straight quotes
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')

    # Normalize em dash and en dash to hyphen
    text = text.replace("–", "-").replace("—", "-")

    # Collapse multiple consecutive spaces into one
    text = re.sub(r" +", " ", text)

    # Strip leading and trailing whitespace
    text = text.strip()

    return text

def is_noise(text: str) -> bool:
    if not text:
        return True

    # Rule 1: More than 60% of characters are the same character
    # catches "aaaaaaa", "!!!!!!", "........."
    if len(text) > 3:
        lower_text = text.lower()
        for char in set(lower_text):
            if lower_text.count(char) / len(lower_text) > 0.6:
                return True

    # Rule 2: More than 70% of characters are digits
    # catches "123456789", "00000"
    digit_count = sum(1 for c in text if c.isdigit())
    if digit_count / len(text) > 0.7:
        return True

    # Rule 3: No alphanumeric characters at all
    # catches "...", "---", "***"
    if not any(c.isalnum() for c in text):
        return True

    return False

def exact_dedup(reviews: list) -> tuple:
    seen = set()
    unique = []
    removed_count = 0

    for review in reviews:
        if review["text"] not in seen:
            seen.add(review["text"])
            unique.append(review)
        else:
            removed_count += 1

    return unique, removed_count

def _normalize_for_comparison(text: str) -> str:
    # Lowercase everything
    text = text.lower()
    # Remove all punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def near_dedup(reviews: list, threshold: float = 0.90) -> tuple:
    # Build normalized versions for comparison only
    # The original text in reviews is never touched
    normalized = [_normalize_for_comparison(r["text"]) for r in reviews]

    to_remove = set()

    for i in range(len(normalized)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(normalized)):
            if j in to_remove:
                continue
            similarity = SequenceMatcher(None, normalized[i], normalized[j]).ratio()
            if similarity >= threshold:
                to_remove.add(j)

    unique = [r for idx, r in enumerate(reviews) if idx not in to_remove]
    return unique, len(to_remove)

def enforce_length(text: str) -> str | None:
    # Drop reviews under minimum length
    if len(text) < MIN_REVIEW_LENGTH:
        return None

    # Return unchanged if within limit
    if len(text) <= MAX_REVIEW_LENGTH:
        return text

    # Trim at sentence boundary for reviews over the limit
    truncated = text[:MAX_REVIEW_LENGTH]

    # Find the last sentence-ending punctuation
    last_boundary = max(
        truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?")
    )

    # Only use the boundary if it falls in the latter half of the truncated text
    # If we cut at position 100 of 1000, we lose too much content
    if last_boundary > MAX_REVIEW_LENGTH * 0.5:
        return truncated[: last_boundary + 1].strip()

    # No good boundary found — return the hard truncation
    return truncated.strip()

def preprocess(raw_text: str) -> dict:

    # ── Stage 1: Split, strip, remove blank lines ──────────────────────────
    lines = [line.strip() for line in raw_text.split("\n")]
    lines = [line for line in lines if line]

    blank_removed = 0  # blank lines were in raw_text but not counted separately
    # We track input as post-split count for clarity
    input_count = len(lines)

    # ── Stage 2: Minimum check ─────────────────────────────────────────────
    if input_count < MIN_REVIEWS:
        return {
            "error": f"Please enter at least {MIN_REVIEWS} reviews. You entered {input_count}.",
            "reviews": [],
            "report": {},
        }

    # ── Stage 3: Emoji conversion ──────────────────────────────────────────
    lines = [convert_emojis(line) for line in lines]

    # ── Stage 4: Normalisation ─────────────────────────────────────────────
    lines = [normalize_text(line) for line in lines]

    # ── Stage 5: Noise filter ──────────────────────────────────────────────
    before_noise = len(lines)
    lines = [line for line in lines if not is_noise(line)]
    noise_removed = before_noise - len(lines)

    # ── Stage 6: Build internal structure ─────────────────────────────────
    reviews = [{"id": i, "text": line} for i, line in enumerate(lines)]

    # ── Stage 7: Exact deduplication ──────────────────────────────────────
    reviews, exact_removed = exact_dedup(reviews)

    # ── Stage 8: Near-duplicate detection ─────────────────────────────────
    reviews, near_removed = near_dedup(reviews)

    # ── Stage 9: Length enforcement ────────────────────────────────────────
    short_removed = 0
    cleaned_reviews = []
    for review in reviews:
        result = enforce_length(review["text"])
        if result is None:
            short_removed += 1
        else:
            review["text"] = result
            cleaned_reviews.append(review)
    reviews = cleaned_reviews

    # ── Re-index IDs after all filtering ──────────────────────────────────
    for i, review in enumerate(reviews):
        review["id"] = i

    # ── Stage 10: Final minimum check ─────────────────────────────────────
    if len(reviews) < MIN_REVIEWS:
        return {
            "error": (
                f"After removing duplicates and low-quality entries, "
                f"only {len(reviews)} reviews remain. "
                f"Minimum required is {MIN_REVIEWS}. Please add more reviews."
            ),
            "reviews": [],
            "report": {},
        }

    # ── Stage 11: Build data quality report ───────────────────────────────
    report = {
        "input_count": input_count,
        "noise_removed": noise_removed,
        "exact_duplicates_removed": exact_removed,
        "near_duplicates_removed": near_removed,
        "short_removed": short_removed,
        "final_count": len(reviews),
    }

    return {"error": None, "reviews": reviews, "report": report}

def batch_reviews(reviews: list) -> list:
    batches = []
    for i in range(0, len(reviews), BATCH_SIZE):
        batches.append(reviews[i : i + BATCH_SIZE])
    return batches
