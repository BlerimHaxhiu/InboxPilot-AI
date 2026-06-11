import os
import pytest
from src.draft_generator import generate_draft
from src.models import DraftReplyResult


def _draft(category: str, subject: str = "Test", body: str = "Test body.", sender: str = "client@co.com"):
    return generate_draft(category, subject, body, sender)


# ── Basic generation ──────────────────────────────────────────────────────────

def test_draft_is_generated():
    result = _draft("invoice", "Invoice #001", "Please process Invoice #001.")
    assert isinstance(result, DraftReplyResult)
    assert len(result.draft_text) > 30


def test_draft_returns_correct_category():
    result = _draft("tax_question")
    assert result.category == "tax_question"


def test_ai_generated_false_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = _draft("invoice")
    assert result.ai_generated is False


# ── Professional language ─────────────────────────────────────────────────────

def test_draft_contains_professional_greeting():
    result = _draft("invoice", sender="sarah.chen@westbrook.com")
    text = result.draft_text.lower()
    assert "dear" in text or "hello" in text or "hi" in text


def test_draft_uses_professional_sign_off():
    result = _draft("invoice")
    text = result.draft_text.lower()
    assert "regards" in text or "sincerely" in text or "yours" in text


# ── Safety — no final tax/legal advice ───────────────────────────────────────

def test_tax_question_draft_does_not_claim_final_advice():
    result = _draft(
        "tax_question",
        "Capital gains tax question",
        "I sold my property. What do I owe?",
    )
    text = result.draft_text.lower()
    # Must NOT make definitive claims
    assert "you owe" not in text
    assert "you must pay" not in text
    # Must contain a disclaimer or TODO
    has_disclaimer = (
        "formal" in text
        or "sign-off" in text
        or "advice" in text
        or "todo" in text
        or "informational" in text
    )
    assert has_disclaimer, "Tax draft must include appropriate disclaimer or TODO"


def test_draft_does_not_claim_email_has_been_sent():
    result = _draft("general_inquiry")
    text = result.draft_text.lower()
    assert "has been sent" not in text
    assert "email sent" not in text


# ── Category-specific behaviour ───────────────────────────────────────────────

def test_complaint_draft_references_complaint():
    result = _draft(
        "client_complaint",
        "Formal complaint",
        "I am formally complaining about errors in our accounts.",
    )
    text = result.draft_text.lower()
    assert "complaint" in text or "concerns" in text or "sorry" in text


def test_invoice_draft_references_accounts():
    result = _draft("invoice", "Invoice #INV-001", "Please process Invoice #INV-001.")
    text = result.draft_text.lower()
    assert "invoice" in text or "accounts" in text or "payment" in text


def test_spam_draft_indicates_no_action():
    result = _draft("spam", "50% off - today only!", "Click here!")
    assert "no action" in result.draft_text.lower() or "spam" in result.draft_text.lower()


def test_vat_draft_mentions_review():
    result = _draft(
        "vat",
        "VAT return Q1",
        "We need help with our VAT return. Input VAT: £10,000.",
    )
    text = result.draft_text.lower()
    assert "vat" in text or "review" in text or "return" in text


def test_bank_statement_draft_confirms_receipt():
    result = _draft(
        "bank_statement",
        "Bank statements Q1",
        "Please find attached bank statements for all accounts.",
    )
    text = result.draft_text.lower()
    assert "receipt" in text or "received" in text or "confirm" in text


# ── Phase 3 new category drafts ───────────────────────────────────────────────

def test_audit_notice_draft_warns_against_direct_hmrc_contact():
    result = _draft(
        "audit_notice",
        "HMRC Compliance Check ENQ-2026-44821",
        "HMRC has opened a formal compliance check into your company.",
        sender="client@business.com",
    )
    text = result.draft_text.lower()
    assert "hmrc" in text
    assert (
        "do not respond" in text
        or "without consulting" in text
        or "before sending" in text
        or "senior partner" in text
    )


def test_new_client_onboarding_draft_mentions_aml_or_engagement():
    result = _draft(
        "new_client_onboarding",
        "Interested in your services",
        "We are a new business and would like to engage your firm for bookkeeping.",
        sender="emily.hayes@newbiz.co.uk",
    )
    text = result.draft_text.lower()
    assert "engagement" in text or "aml" in text or "onboarding" in text


def test_payment_confirmation_draft_confirms_receipt():
    result = _draft(
        "payment_confirmation",
        "Payment of £6,200 sent",
        "I confirm that payment of £6,200 has been sent for Invoice INV-2026-0089.",
        sender="client@co.com",
    )
    text = result.draft_text.lower()
    assert "payment" in text
    assert "receipt" in text or "received" in text or "confirm" in text


def test_contract_service_question_draft_mentions_engagement_letter():
    result = _draft(
        "contract_service_question",
        "Query about your fee structure",
        "We have questions about your retainer model and terms of engagement.",
        sender="client@co.com",
    )
    text = result.draft_text.lower()
    assert "engagement" in text or "fee" in text or "services" in text


# ── _REVIEW_WARNING present in non-spam drafts ───────────────────────────────

NON_SPAM_CATEGORIES = [
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
]


@pytest.mark.parametrize("category", NON_SPAM_CATEGORIES)
def test_review_warning_present_in_non_spam(category, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = _draft(category)
    assert "DRAFT FOR REVIEW" in result.draft_text, (
        f"Category '{category}' draft is missing the _REVIEW_WARNING"
    )


def test_review_warning_absent_in_spam(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = _draft("spam")
    assert "DRAFT FOR REVIEW" not in result.draft_text
