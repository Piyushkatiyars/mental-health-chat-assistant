"""
Rule-based crisis-detection layer.

Design principle: keep this DETERMINISTIC and AUDITABLE, not ML-based.
For a mental health app, you want to be able to point at exactly why
a message was flagged — a black-box classifier is the wrong tool here,
and it's also a great talking point in interviews ("why rule-based
over ML for this specific layer?").

This is intentionally NOT exhaustive or clinical-grade. In a real
product this list would be built with input from mental health
professionals and reviewed regularly.
"""

import re

# Keep categories separate so you can log/route them differently if needed.
CRISIS_PATTERNS = {
    "self_harm": [
        r"\bkill myself\b",
        r"\bsuicid(e|al)\b",
        r"\bend my life\b",
        r"\bwant to die\b",
        r"\bhurt myself\b",
        r"\bself[- ]harm\b",
        r"\bno reason to live\b",
    ],
    "harm_to_others": [
        r"\bkill (him|her|them)\b",
        r"\bhurt (him|her|them)\b",
    ],
}

# India-focused as a default since this is a college project; swap/add
# numbers as appropriate for your deployment context.
CRISIS_RESPONSE = (
    "I hear that you're going through something really painful right now, "
    "and I want to make sure you get support from people who are trained to help.\n\n"
    "If you're in India, you can reach:\n"
    "• iCall (TISS): +91 9152987821\n"
    "• AASRA: +91 9820466726\n"
    "• Or call 112 for immediate emergency help\n\n"
    "If you're outside India, please look up your local crisis helpline or go to "
    "your nearest emergency room. You don't have to go through this alone."
)


def check_for_crisis(message: str):
    """
    Returns (is_crisis: bool, category: str | None).
    Checks against known patterns using word-boundary regex to reduce
    false positives (e.g. avoids matching inside unrelated words).
    """
    lowered = message.lower()
    for category, patterns in CRISIS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                return True, category
    return False, None
