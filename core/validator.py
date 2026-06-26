import json
import re
from pydantic import BaseModel, field_validator
from typing import List, Optional


ALLOWED_SENTIMENTS = {"positive", "negative", "neutral"}
ALLOWED_URGENCIES = {"critical", "medium", "low"}
ALLOWED_EMOTIONS = {
    "happy",
    "angry",
    "frustrated",
    "disappointed",
    "confused",
    "satisfied",
    "surprised",
    "neutral",
}
ALLOWED_CONFIDENCES = {"high", "medium", "low"}
GENERAL_FALLBACK = "General Experience"


class AspectSentiment(BaseModel):
    category: str
    sentiment: str

    @field_validator("sentiment")
    @classmethod
    def validate_aspect_sentiment(cls, v):
        n = v.lower().strip()
        if n not in ALLOWED_SENTIMENTS:
            raise ValueError(
                f"Invalid aspect sentiment '{v}'. Allowed: {ALLOWED_SENTIMENTS}"
            )
        return n

    @field_validator("category")
    @classmethod
    def validate_aspect_category(cls, v):
        return v.strip()


class ReviewClassification(BaseModel):
    id: int
    sentiment: str
    primary_category: str
    secondary_category: Optional[str] = None
    aspects: List[AspectSentiment] = []
    urgency: str
    emotion: str
    core_issue: str
    confidence: str

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v):
        n = v.lower().strip()
        if n not in ALLOWED_SENTIMENTS:
            raise ValueError(f"Invalid sentiment '{v}'. Allowed: {ALLOWED_SENTIMENTS}")
        return n

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v):
        n = v.lower().strip()
        if n not in ALLOWED_URGENCIES:
            raise ValueError(f"Invalid urgency '{v}'. Allowed: {ALLOWED_URGENCIES}")
        return n

    @field_validator("emotion")
    @classmethod
    def validate_emotion(cls, v):
        n = v.lower().strip()
        if n not in ALLOWED_EMOTIONS:
            raise ValueError(f"Invalid emotion '{v}'. Allowed: {ALLOWED_EMOTIONS}")
        return n

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        n = v.lower().strip()
        if n not in ALLOWED_CONFIDENCES:
            raise ValueError(
                f"Invalid confidence '{v}'. Allowed: {ALLOWED_CONFIDENCES}"
            )
        return n

    @field_validator("primary_category")
    @classmethod
    def validate_primary_category(cls, v):
        return v.strip()

    @field_validator("secondary_category")
    @classmethod
    def validate_secondary_category(cls, v):
        if v is None:
            return None
        return v.strip()

    @field_validator("core_issue")
    @classmethod
    def validate_core_issue(cls, v):
        words = v.strip().split()
        if len(words) > 15:
            return " ".join(words[:15])
        return v.strip()


class BatchClassificationResult(BaseModel):
    results: List[ReviewClassification]


def normalize_llm_response(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _fix_category_against_allowed(
    value: str, allowed_lower_map: dict, fallback: str
) -> str:
    if value.lower() in allowed_lower_map:
        return allowed_lower_map[value.lower()]
    return fallback


def validate_batch_response(
    raw_response: str, expected_count: int, allowed_categories: list
) -> dict:

    cleaned = normalize_llm_response(raw_response)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "results": [],
            "error": f"JSON parsing failed: {str(e)}",
        }

    try:
        validated = BatchClassificationResult(**parsed)
    except Exception as e:
        return {
            "success": False,
            "results": [],
            "error": f"Schema validation failed: {str(e)}",
        }

    if len(validated.results) != expected_count:
        return {
            "success": False,
            "results": [],
            "error": (
                f"Expected {expected_count} results, "
                f"got {len(validated.results)}. "
                f"Model skipped or duplicated a review."
            ),
        }

    all_categories = allowed_categories + [GENERAL_FALLBACK]
    allowed_lower_map = {c.lower(): c for c in all_categories}
    fallback_cat = GENERAL_FALLBACK

    for item in validated.results:
        item.primary_category = _fix_category_against_allowed(
            item.primary_category, allowed_lower_map, fallback_cat
        )

        if item.secondary_category is not None:
            item.secondary_category = _fix_category_against_allowed(
                item.secondary_category, allowed_lower_map, fallback_cat
            )
            if item.secondary_category == item.primary_category:
                item.secondary_category = None

        for aspect in item.aspects:
            aspect.category = _fix_category_against_allowed(
                aspect.category, allowed_lower_map, fallback_cat
            )

        if not item.aspects:
            item.aspects = [
                AspectSentiment(
                    category=item.primary_category, sentiment=item.sentiment
                )
            ]

    return {
        "success": True,
        "results": [r.model_dump() for r in validated.results],
        "error": None,
    }
