import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BATCH_SIZE

GENERAL_FALLBACK = "General Experience"


def _build_urgency_definitions(custom_definition: str | None) -> str:
    if custom_definition:
        return (
            f'  - "critical": {custom_definition}\n'
            f'  - "medium": Notable issue the business should address within days\n'
            f'  - "low": Minor friction with no immediate churn risk'
        )
    return (
        '  - "critical": Customer is likely to churn, escalate publicly, or leave a 1-star review\n'
        '  - "medium": Notable issue the business should address but not immediately urgent\n'
        '  - "low": Minor friction or cosmetic complaint with no churn risk'
    )


def _build_examples(categories: list) -> str:
    cat1 = categories[0]
    cat2 = categories[1] if len(categories) > 1 else categories[0]

    return f"""Input:
Review 1: Terrible delivery, took 3 weeks and when it arrived the product had a huge scratch on it.
Review 2: Outstanding product quality! Could not be happier with this purchase.
Review 3: It is okay I guess. Nothing special but nothing terrible either.
Review 4: Total waste of money.
Review 5: बहुत खराब अनुभव था। बिल्कुल अच्छा नहीं था।

Output:
{{
  "results": [
    {{
      "id": 1,
      "sentiment": "negative",
      "primary_category": "{cat2}",
      "secondary_category": "{cat1}",
      "aspects": [
        {{"category": "{cat2}", "sentiment": "negative"}},
        {{"category": "{cat1}", "sentiment": "negative"}}
      ],
      "urgency": "critical",
      "emotion": "angry",
      "core_issue": "3-week delayed delivery, product arrived scratched and damaged",
      "confidence": "high"
    }},
    {{
      "id": 2,
      "sentiment": "positive",
      "primary_category": "{cat1}",
      "secondary_category": null,
      "aspects": [
        {{"category": "{cat1}", "sentiment": "positive"}}
      ],
      "urgency": "low",
      "emotion": "happy",
      "core_issue": "Excellent product quality, customer fully satisfied with purchase",
      "confidence": "high"
    }},
    {{
      "id": 3,
      "sentiment": "neutral",
      "primary_category": "General Experience",
      "secondary_category": null,
      "aspects": [
        {{"category": "General Experience", "sentiment": "neutral"}}
      ],
      "urgency": "low",
      "emotion": "neutral",
      "core_issue": "Average experience with no strong positive or negative aspects",
      "confidence": "medium"
    }},
    {{
      "id": 4,
      "sentiment": "negative",
      "primary_category": "{cat2}",
      "secondary_category": null,
      "aspects": [
        {{"category": "{cat2}", "sentiment": "negative"}}
      ],
      "urgency": "medium",
      "emotion": "disappointed",
      "core_issue": "Customer considers purchase poor value for money",
      "confidence": "medium"
    }},
    {{
      "id": 5,
      "sentiment": "negative",
      "primary_category": "{cat1}",
      "secondary_category": null,
      "aspects": [
        {{"category": "{cat1}", "sentiment": "negative"}}
      ],
      "urgency": "medium",
      "emotion": "frustrated",
      "core_issue": "Very bad experience reported by customer",
      "confidence": "high"
    }}
  ]
}}"""


def build_system_prompt(profile: dict) -> str:
    company_name  = profile["company_name"]
    industry      = profile["industry"]
    categories    = profile["categories"]
    description   = profile.get("description", "")
    urgency_def   = profile.get("urgency_definition", "")

    description_line = (
        f"\nBusiness context: {description}" if description else ""
    )

    all_categories       = categories + [GENERAL_FALLBACK]
    categories_formatted = ", ".join(f'"{c}"' for c in all_categories)
    urgency_defs         = _build_urgency_definitions(urgency_def or None)
    examples             = _build_examples(categories)

    return f"""You are a customer feedback classification engine for {company_name}, a {industry} business.{description_line}

You will receive a numbered list of customer reviews. For each review, classify it across all dimensions below. Return results as a single JSON object. Do not explain, comment, or add any text outside the JSON.

## OUTPUT FORMAT
Return exactly this structure:
{{
  "results": [
    {{
      "id": <integer matching the Review number shown in the input, e.g. "Review 3" means id: 3>,
      "sentiment": <string>,
      "primary_category": <string — the single most relevant category>,
      "secondary_category": <string or null — second category only if the review clearly mentions two distinct issues>,
      "aspects": [
        {{"category": <string>, "sentiment": <string>}}
      ],
      "urgency": <string>,
      "emotion": <string>,
      "core_issue": <string, maximum 15 words>,
      "confidence": <string>
    }}
  ]
}}

## ALLOWED VALUES
sentiment: "positive", "negative", "neutral"
category (for primary_category, secondary_category, and aspect category fields): {categories_formatted}
urgency:
{urgency_defs}
emotion: "happy", "angry", "frustrated", "disappointed", "confused", "satisfied", "surprised", "neutral"
confidence:
  - "high": Review clearly and explicitly addresses specific aspects. Sentiment and category are unambiguous.
  - "medium": Review addresses mixed aspects, uses indirect or sarcastic language, or the category is implied rather than explicitly stated.
  - "low": Review is too vague, too short, or too general to classify with certainty. Assigned values are best guesses.

## RULES
1. Return ONLY the JSON object. No text before it, no text after it, no markdown code fences.
2. Use ONLY the allowed values listed above for every field. Never invent a new value.
3. All field values must be in English regardless of the language of the review text.
4. The "id" in each result must exactly match the Review number shown in the input (Review 1 → id 1, Review 2 → id 2, etc). Every review must have exactly one result. Never skip, never duplicate.
5. Set secondary_category to null if the review clearly addresses only one category. Only populate it when two genuinely distinct issues are present.
6. The aspects array must always contain at least one entry matching primary_category. Add a second entry for secondary_category if it is not null, with its own sentiment which may differ from the overall sentiment.
7. Use "General Experience" as primary_category only when the review is too generic to map to any specific category.
8. If a review is genuinely ambiguous, use the closest best-fit value and set confidence to "low". Never return null for any field except secondary_category.

## EXAMPLES
{examples}"""


def build_user_prompt(batch: list) -> str:
    lines = []
    for position, review in enumerate(batch):
        lines.append(f"Review {position + 1}: {review['text']}")
    return "\n".join(lines)


def build_prompt_pair(profile: dict, batch: list) -> dict:
    return {
        "system": build_system_prompt(profile),
        "user":   build_user_prompt(batch)
    }