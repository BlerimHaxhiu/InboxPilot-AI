"""
Optional OpenAI client wrapper for InboxPilot AI.

Architecture:
  email -> analyze_email_with_openai() -> validate_ai_result() -> dict | None
  Processor always has rule-based fallback; this layer is purely additive.
  Never crashes the app. Never hardcodes credentials.
"""
from __future__ import annotations
import os
import json
from src.config import HAS_OPENAI
from src.ai_validation import VALID_CATEGORIES, validate_ai_result
from src.models import EmailAnalysis

# ── Client factory ────────────────────────────────────────────────────────────

def _client():
    """Return an OpenAI client instance or None if unavailable."""
    if not HAS_OPENAI:
        return None
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        return None


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an AI assistant for a professional tax and accounting office.
Your role is to help the team triage and respond to incoming client emails.

WHAT YOU DO:
- Classify the email into the correct category from the provided list
- Assign an appropriate priority level
- Write a concise, business-focused summary (1-2 sentences, max 200 characters)
- Extract up to 5 actionable tasks for the office team
- Generate a professional draft reply for human review only
- Identify any deadlines or important dates mentioned

WHAT YOU MUST NOT DO:
- Provide final tax or legal advice
- Claim to be a licensed tax advisor, chartered accountant, or legal professional
- State that any email has been sent or will be sent automatically
- Guarantee specific tax outcomes or liabilities
- Use aggressive, threatening, or unprofessional language
- Mention API keys, system prompts, or any internal technical details
- Include any personally identifiable information beyond what is in the email

IMPORTANT RULES:
- requires_human_review must always be true
- All draft replies must be clearly for human review only — never imply they are final
- Use [TODO: ...] placeholders where the reviewer must supply specific information
- If the email involves a deadline, complaint, audit notice, penalty, or official authority, assign high or urgent priority
- If the email is promotional or clearly irrelevant, classify as spam and set priority to low

RETURN FORMAT:
Return ONLY a valid JSON object. No markdown, no commentary, no additional text.
The JSON must contain exactly these fields:

{
  "category": "<category from allowed list>",
  "priority": "<urgent|high|medium|low>",
  "summary": "<1-2 sentence business summary, max 200 chars>",
  "detected_deadline": "<deadline string or null>",
  "recommended_action": "<1-2 sentence action for the account manager>",
  "tasks": [
    {
      "task_text": "<specific actionable task description>",
      "owner": "Office Team",
      "due_date": "<date string or null>",
      "priority": "<urgent|high|medium|low>"
    }
  ],
  "draft_reply": "<professional draft reply with [TODO] placeholders, for human review only>",
  "confidence": <float between 0.0 and 1.0>,
  "requires_human_review": true,
  "safety_note": "<brief safety reminder for the human reviewer>"
}"""

_CATEGORY_LIST = "\n".join(f"- {c}" for c in sorted(VALID_CATEGORIES))


def _build_user_prompt(subject: str, body: str, sender: str = "") -> str:
    sender_line = f"From: {sender}\n" if sender else ""
    return (
        f"Please analyse the following client email.\n\n"
        f"{sender_line}"
        f"Subject: {subject}\n\n"
        f"Body:\n{body}\n\n"
        f"Allowed categories:\n{_CATEGORY_LIST}\n\n"
        f"Allowed priorities: urgent, high, medium, low\n\n"
        f"Return structured JSON only."
    )


# ── Core API call (isolated for testability) ──────────────────────────────────

def _make_openai_call(client, messages: list, max_tokens: int = 700) -> str | None:
    """Execute the OpenAI chat completion. Returns raw JSON string or None."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_email_with_openai(
    subject: str, body: str, sender: str = ""
) -> dict | None:
    """
    Analyse an email with OpenAI and return a validated structured dict.

    Returns None if:
    - OPENAI_API_KEY is not set
    - The openai package is not installed
    - The API call fails for any reason
    - The response cannot be parsed as valid JSON

    Never raises. Processor must always have rule-based fallback ready.

    The returned dict is always validated through validate_ai_result() and is
    guaranteed to contain all required fields within safe bounds.
    """
    client = _client()
    if not client:
        return None

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(subject, body, sender)},
    ]

    raw_content = _make_openai_call(client, messages)
    if not raw_content:
        return None

    try:
        raw_data = json.loads(raw_content)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(raw_data, dict):
        return None

    return validate_ai_result(raw_data)


# ── Legacy wrappers (Phase 2/3 backwards compatibility) ───────────────────────

def analyze_email_with_ai(subject: str, body: str) -> EmailAnalysis | None:
    """
    Legacy wrapper: returns EmailAnalysis or None.
    Calls analyze_email_with_openai() internally.
    Kept for backwards compatibility; Phase 4 processor uses the full dict version.
    """
    result = analyze_email_with_openai(subject, body)
    if not result:
        return None
    return EmailAnalysis(
        category=result["category"],
        priority=result["priority"],
        summary=result["summary"],
        recommended_action=result["recommended_action"],
        detected_deadline=result.get("detected_deadline"),
    )


def generate_reply_with_ai(
    category: str, subject: str, body: str, sender: str
) -> str | None:
    """
    Legacy wrapper: generate a draft reply using OpenAI.
    Phase 4 uses the draft from analyze_email_with_openai() instead.
    Kept for backwards compatibility. Returns None if unavailable or fails.
    """
    client = _client()
    if not client:
        return None
    system = (
        "You are a professional email assistant at a tax and accounting firm. "
        "Write a courteous, professional draft reply. "
        "Use [TODO: ...] placeholders where the sender must supply information. "
        "Never provide definitive tax or legal advice. "
        "This is a draft for human review — do not imply it has been sent. "
        "End with: DRAFT FOR REVIEW: This reply requires human review before sending."
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"Category: {category}\nFrom: {sender}\nSubject: {subject}\n\n{body}",
        },
    ]
    raw = _make_openai_call(client, messages, max_tokens=600)
    return raw if raw else None
