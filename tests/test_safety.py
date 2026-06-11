import pytest
from src.safety import (
    contains_risky_claims,
    enforce_draft_safety,
    append_review_notice_if_needed,
)

_REVIEW_MARKER = "DRAFT FOR REVIEW"


# ── contains_risky_claims ─────────────────────────────────────────────────────

def test_clean_draft_has_no_risky_claims():
    safe_draft = (
        "Dear Client,\n\nThank you for your email. "
        "I will review your situation and respond shortly.\n\nKind regards,\n[Your Name]"
    )
    assert contains_risky_claims(safe_draft) is False


def test_guarantee_triggers_risky():
    assert contains_risky_claims("We guarantee you will receive a full refund.") is True


def test_i_guarantee_triggers_risky():
    assert contains_risky_claims("I guarantee this will be resolved by Friday.") is True


def test_email_sent_claim_triggers_risky():
    assert contains_risky_claims("This email has been sent to HMRC on your behalf.") is True


def test_final_tax_advice_triggers_risky():
    assert contains_risky_claims(
        "This constitutes final tax advice for your situation."
    ) is True


def test_licensed_advisor_claim_triggers_risky():
    assert contains_risky_claims(
        "As your licensed tax advisor, I confirm you owe nothing."
    ) is True


def test_api_key_exposure_triggers_risky():
    assert contains_risky_claims("The OPENAI_API_KEY is sk-abc123def456ghi789jkl.") is True


def test_empty_string_is_safe():
    assert contains_risky_claims("") is False


# ── enforce_draft_safety ──────────────────────────────────────────────────────

def test_guarantee_replaced_safely():
    draft = "We guarantee your refund will arrive within 5 days."
    result = enforce_draft_safety(draft)
    assert "guarantee" not in result.lower() or "aim to ensure" in result.lower()


def test_email_sent_claim_replaced():
    draft = "This email has been sent to HMRC."
    result = enforce_draft_safety(draft)
    assert "has been sent" not in result.lower()


def test_final_advice_claim_replaced():
    draft = "This constitutes definitive tax advice for your case."
    result = enforce_draft_safety(draft)
    assert "definitive tax advice" not in result.lower()


def test_api_key_redacted():
    draft = "Please set OPENAI_API_KEY in your environment."
    result = enforce_draft_safety(draft)
    assert "OPENAI_API_KEY" not in result
    assert "[REDACTED]" in result


def test_safe_draft_unchanged():
    safe = "Dear Client,\n\nThank you. Kind regards,\n[Your Name]"
    result = enforce_draft_safety(safe)
    assert result == safe


def test_empty_string_unchanged():
    assert enforce_draft_safety("") == ""


def test_none_like_empty_unchanged():
    # enforce_draft_safety with empty input should return input as-is
    assert enforce_draft_safety("") == ""


# ── append_review_notice_if_needed ────────────────────────────────────────────

def test_review_notice_appended_when_missing():
    draft = "Dear Client,\n\nThank you for your email.\n\nKind regards,\n[Your Name]"
    result = append_review_notice_if_needed(draft)
    assert _REVIEW_MARKER in result


def test_review_notice_not_duplicated_when_already_present():
    draft = f"Dear Client,\n\nThank you.\n\n---\n{_REVIEW_MARKER}: This draft requires review."
    result = append_review_notice_if_needed(draft)
    assert result.count(_REVIEW_MARKER) == 1


def test_empty_string_unchanged_by_notice():
    assert append_review_notice_if_needed("") == ""


def test_review_notice_contains_correct_wording():
    draft = "Draft reply text."
    result = append_review_notice_if_needed(draft)
    assert "qualified team member" in result or "human review" in result.lower()


def test_combined_safety_pipeline():
    """enforce_draft_safety then append_review_notice_if_needed produces safe, reviewed draft."""
    risky_draft = (
        "Dear Client,\n\n"
        "We guarantee your refund will arrive in 5 days. "
        "This constitutes final tax advice.\n\n"
        "Kind regards,\n[Your Name]"
    )
    cleaned = enforce_draft_safety(risky_draft)
    final = append_review_notice_if_needed(cleaned)
    assert "guarantee" not in final.lower() or "aim to ensure" in final.lower()
    assert _REVIEW_MARKER in final
    assert contains_risky_claims(final) is False
