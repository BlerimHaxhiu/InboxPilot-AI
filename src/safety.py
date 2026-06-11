"""
Safety enforcement for AI-generated draft replies.
Prevents risky or inappropriate language from reaching outgoing drafts.
"""
from __future__ import annotations
import re

_REVIEW_MARKER = "DRAFT FOR REVIEW"

_REVIEW_NOTICE = (
    "\n\n---\n"
    "DRAFT FOR REVIEW: This reply was generated automatically. "
    "Please review, edit as needed, and obtain sign-off from a qualified team member "
    "before sending. Do not send this message in its current form without review."
)

# Patterns whose presence indicates a risky draft
_RISKY_DETECTION = [
    re.compile(r'\bwe guarantee\b', re.I),
    re.compile(r'\bI guarantee\b', re.I),
    re.compile(r'\byou (will|won\'t|wont) owe\b', re.I),
    re.compile(r'\byou (are|are not|aren\'t) liable\b', re.I),
    re.compile(r'\byou (must|should) definitely\b', re.I),
    re.compile(
        r'\bthis (is|constitutes) (final|definitive|official|formal) '
        r'(tax |legal )?(advice|opinion|ruling|determination)\b',
        re.I,
    ),
    re.compile(r'\bthis (email|message) (has been|was) sent\b', re.I),
    re.compile(r'\bI (have|\'ve|have already) sent (the|this|an) (email|message|reply)\b', re.I),
    re.compile(r'\bas (your|the) licensed (tax|legal) (advisor|adviser|professional|expert)\b', re.I),
    re.compile(r'\bas a (qualified|registered|certified) (tax|legal) (advisor|adviser)\b', re.I),
    re.compile(r'\b(OPENAI_API_KEY|sk-[A-Za-z0-9]{20,})\b'),
    re.compile(r'\b(system prompt|internal prompt|my (training|instructions))\b', re.I),
]

# Patterns to replace with safer wording
_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bwe guarantee\b', re.I), "we aim to ensure"),
    (re.compile(r'\bI guarantee\b', re.I), "I will endeavour to ensure"),
    (
        re.compile(
            r'\bthis (is|constitutes) (final|definitive|official|formal) '
            r'(tax |legal )?(advice|opinion|ruling|determination)\b',
            re.I,
        ),
        "this draft is for review only and does not constitute formal advice",
    ),
    (
        re.compile(r'\bthis (email|message) (has been|was) sent\b', re.I),
        "this draft is pending human review",
    ),
    (
        re.compile(r'\bI (have|\'ve|have already) sent (the|this|an) (email|message|reply)\b', re.I),
        "I have prepared a draft for your review",
    ),
    (
        re.compile(r'\bas (your|the) licensed (tax|legal) (advisor|adviser|professional|expert)\b', re.I),
        "as your professional service provider",
    ),
    (
        re.compile(r'\bas a (qualified|registered|certified) (tax|legal) (advisor|adviser)\b', re.I),
        "as a professional service provider",
    ),
    # Redact any accidental credential exposure
    (re.compile(r'\bsk-[A-Za-z0-9]{20,}\b'), "[REDACTED]"),
    (re.compile(r'\bOPENAI_API_KEY\b'), "[REDACTED]"),
    (re.compile(r'\b(system prompt|internal prompt|my (training|instructions))\b', re.I), "[internal]"),
]


def contains_risky_claims(draft_text: str) -> bool:
    """Return True if the draft contains any unsafe language patterns."""
    if not draft_text:
        return False
    return any(pat.search(draft_text) for pat in _RISKY_DETECTION)


def enforce_draft_safety(draft_text: str) -> str:
    """
    Remove or replace known risky phrases with safe alternatives.
    Returns a cleaned draft string. Never raises.
    """
    if not draft_text:
        return draft_text
    result = draft_text
    for pat, replacement in _REPLACEMENTS:
        result = pat.sub(replacement, result)
    return result


def append_review_notice_if_needed(draft_text: str) -> str:
    """
    Ensure the DRAFT FOR REVIEW notice is present.
    If already present, returns the text unchanged.
    """
    if not draft_text:
        return draft_text
    if _REVIEW_MARKER in draft_text:
        return draft_text
    return draft_text + _REVIEW_NOTICE
