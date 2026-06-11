"""
Validation and normalisation for AI-generated email analysis results.
Ensures model output is safe, complete, and within expected bounds before use.
"""
from __future__ import annotations

VALID_CATEGORIES = {
    "invoice",
    "tax_question",
    "missing_document",
    "appointment_request",
    "payroll",
    "vat",
    "bank_statement",
    "client_complaint",
    "refund_question",
    "urgent_client_issue",
    "audit_notice",
    "new_client_onboarding",
    "payment_confirmation",
    "contract_service_question",
    "general_inquiry",
    "spam",
}

VALID_PRIORITIES = {"low", "medium", "high", "urgent"}

# Common alias variations the model might use
_CATEGORY_ALIASES: dict[str, str] = {
    "tax question": "tax_question",
    "tax query": "tax_question",
    "missing document": "missing_document",
    "missing documents": "missing_document",
    "appointment request": "appointment_request",
    "meeting request": "appointment_request",
    "payroll query": "payroll",
    "payroll question": "payroll",
    "vat return": "vat",
    "value added tax": "vat",
    "bank statement": "bank_statement",
    "bank statements": "bank_statement",
    "client complaint": "client_complaint",
    "complaint": "client_complaint",
    "refund question": "refund_question",
    "refund query": "refund_question",
    "urgent client issue": "urgent_client_issue",
    "urgent issue": "urgent_client_issue",
    "audit notice": "audit_notice",
    "compliance notice": "audit_notice",
    "hmrc notice": "audit_notice",
    "new client onboarding": "new_client_onboarding",
    "new client": "new_client_onboarding",
    "onboarding": "new_client_onboarding",
    "payment confirmation": "payment_confirmation",
    "payment received": "payment_confirmation",
    "contract service question": "contract_service_question",
    "contract/service question": "contract_service_question",
    "service question": "contract_service_question",
    "fee enquiry": "contract_service_question",
    "general inquiry": "general_inquiry",
    "general enquiry": "general_inquiry",
    "general": "general_inquiry",
    "spam/irrelevant": "spam",
    "spam / irrelevant": "spam",
    "irrelevant": "spam",
    "promotional": "spam",
    "marketing": "spam",
}

_DEFAULT_SAFETY_NOTE = (
    "This analysis was generated automatically. All outputs require human review "
    "before use. Do not send any draft without sign-off by a qualified team member."
)


def normalize_category(value: str) -> str:
    """Map raw model output to a valid category slug. Defaults to 'general_inquiry'."""
    if not isinstance(value, str) or not value.strip():
        return "general_inquiry"
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in VALID_CATEGORIES:
        return normalized
    alias_key = value.strip().lower()
    if alias_key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[alias_key]
    # Substring match as last resort
    for cat in VALID_CATEGORIES:
        if cat.replace("_", " ") in alias_key or alias_key in cat.replace("_", " "):
            return cat
    return "general_inquiry"


def normalize_priority(value: str) -> str:
    """Map raw model output to a valid priority level. Defaults to 'medium'."""
    if not isinstance(value, str) or not value.strip():
        return "medium"
    normalized = value.strip().lower()
    if normalized in VALID_PRIORITIES:
        return normalized
    if normalized in ("critical", "emergency", "immediate", "asap", "highest"):
        return "urgent"
    if normalized in ("important", "elevated", "high priority", "elevated priority"):
        return "high"
    if normalized in ("normal", "standard", "routine", "moderate"):
        return "medium"
    if normalized in ("informational", "fyi", "low priority", "minimal"):
        return "low"
    return "medium"


def ensure_required_fields(result: dict) -> dict:
    """Fill missing or invalid fields with safe defaults. Returns a new dict."""
    out = dict(result)

    out["category"] = normalize_category(out.get("category", ""))
    out["priority"] = normalize_priority(out.get("priority", ""))

    # Summary
    if not isinstance(out.get("summary"), str) or not out["summary"].strip():
        out["summary"] = "Email received — requires review."
    out["summary"] = out["summary"].strip()[:250]

    # Recommended action
    if not isinstance(out.get("recommended_action"), str) or not out["recommended_action"].strip():
        out["recommended_action"] = "Review and respond to the client email."
    out["recommended_action"] = out["recommended_action"].strip()[:400]

    # Detected deadline
    dl = out.get("detected_deadline")
    if dl in (None, "null", "none", "", "N/A", "n/a"):
        out["detected_deadline"] = None
    else:
        out["detected_deadline"] = str(dl).strip()[:100]

    # Tasks
    if not isinstance(out.get("tasks"), list):
        out["tasks"] = []
    clean_tasks = []
    for t in out["tasks"][:5]:
        if not isinstance(t, dict):
            continue
        task_text = str(t.get("task_text", "")).strip()
        if not task_text:
            continue
        clean_tasks.append({
            "task_text": task_text[:200],
            "owner": str(t.get("owner", "Office Team")).strip() or "Office Team",
            "due_date": t.get("due_date") or None,
            "priority": normalize_priority(str(t.get("priority", out["priority"]))),
            "status": "open",
        })
    out["tasks"] = clean_tasks

    # Draft reply
    if not isinstance(out.get("draft_reply"), str):
        out["draft_reply"] = ""
    out["draft_reply"] = out["draft_reply"].strip()

    # Confidence — clamped to [0.0, 1.0]
    try:
        conf = float(out.get("confidence", 0.0))
        out["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        out["confidence"] = 0.0

    # requires_human_review — always True, non-negotiable
    out["requires_human_review"] = True

    # safety_note
    if not isinstance(out.get("safety_note"), str) or not out["safety_note"].strip():
        out["safety_note"] = _DEFAULT_SAFETY_NOTE
    out["safety_note"] = out["safety_note"].strip()[:500]

    return out


def validate_ai_result(result: dict) -> dict:
    """
    Validate and normalise a raw AI output dict.
    Guarantees all required fields are present, typed correctly, and within bounds.
    Never raises — always returns a safe dict.
    """
    if not isinstance(result, dict):
        return ensure_required_fields({})
    return ensure_required_fields(result)
