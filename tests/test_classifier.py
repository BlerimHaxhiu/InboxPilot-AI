import pytest
from src.classifier import classify_email, score_priority, detect_deadline, recommend_action


# ── classify_email ────────────────────────────────────────────────────────────

def test_invoice_classification():
    cat = classify_email(
        "Invoice #INV-2026-0145 for April Services",
        "Please find attached Invoice #INV-2026-0145. Amount due: $4,850. Payment terms: Net 30.",
    )
    assert cat == "invoice"


def test_tax_question_classification():
    cat = classify_email(
        "Question about capital gains tax",
        "I sold my property and need to understand my capital gains tax liability.",
    )
    assert cat == "tax_question"


def test_vat_classification():
    cat = classify_email(
        "VAT return Q1 2026 - need assistance",
        "We need help preparing our VAT return. Input VAT: £18,200 Output VAT: £71,340.",
    )
    assert cat == "vat"


def test_payroll_classification():
    cat = classify_email(
        "Payroll query - new employee tax code",
        "New starter joining Monday. No P45. Should we use emergency tax code 1257L W1/M1?",
    )
    assert cat == "payroll"


def test_bank_statement_classification():
    cat = classify_email(
        "Bank statements attached - Q1 2026",
        "Please find attached bank statements for all three accounts (xxxx-1234, xxxx-5678).",
    )
    assert cat == "bank_statement"


def test_complaint_classification():
    cat = classify_email(
        "Formal complaint - errors in our accounts",
        "I am writing to formally raise a complaint. We discovered errors and were overcharged.",
    )
    assert cat == "client_complaint"


def test_spam_classification():
    cat = classify_email(
        "SPECIAL OFFER: 70% OFF accounting software - Today only!!!",
        "INCREDIBLE DEAL! Click here now before this offer expires in 24 hours! Unsubscribe here.",
    )
    assert cat == "spam"


def test_appointment_classification():
    cat = classify_email(
        "Appointment request - annual accounts review",
        "I would like to schedule a meeting to review our accounts. I am available Monday.",
    )
    assert cat == "appointment_request"


def test_refund_classification():
    cat = classify_email(
        "R&D tax credit refund - still outstanding",
        "It has been four months since we submitted our R&D tax credit claim. When will we receive the refund?",
    )
    assert cat == "refund_question"


def test_general_inquiry_fallback():
    cat = classify_email("Quick question", "Just a general question about your services.")
    assert cat == "general_inquiry"


# ── score_priority ────────────────────────────────────────────────────────────

def test_urgent_priority():
    pri = score_priority(
        "URGENT: Corporation tax deadline June 20th",
        "Your tax payment is overdue. Penalties will accrue immediately. Do not ignore this notice.",
    )
    assert pri == "urgent"


def test_high_priority_complaint():
    pri = score_priority(
        "Formal complaint - errors in accounts",
        "I am formally complaining about incorrect entries and overcharging.",
    )
    assert pri == "high"


def test_medium_priority_invoice():
    pri = score_priority(
        "Invoice for April services",
        "Please process Invoice #INV-001 under standard payment terms.",
    )
    assert pri == "medium"


def test_low_priority_general():
    pri = score_priority("General question", "Just wondering about your office hours.")
    assert pri == "low"


# ── detect_deadline ───────────────────────────────────────────────────────────

def test_deadline_detected_from_subject():
    deadline = detect_deadline(
        "Corporation tax due June 20th",
        "Please pay before the deadline.",
    )
    assert deadline is not None
    assert "june" in deadline.lower() or "20" in deadline


def test_deadline_detected_from_body():
    deadline = detect_deadline(
        "Tax return reminder",
        "We need the documents by June 15th to avoid penalties.",
    )
    assert deadline is not None


def test_no_deadline_returns_none():
    deadline = detect_deadline("General inquiry", "Just a general question with no dates.")
    assert deadline is None


# ── recommend_action ──────────────────────────────────────────────────────────

def test_recommend_action_spam():
    action = recommend_action("spam", "low", "Click here for deals!")
    assert "no action" in action.lower() or "spam" in action.lower()


def test_recommend_action_urgent_prefix():
    action = recommend_action("urgent_client_issue", "urgent", "Critical issue!")
    assert action.upper().startswith("URGENT")


def test_recommend_action_complaint():
    action = recommend_action("client_complaint", "high", "I am complaining.")
    assert "complaint" in action.lower() or "senior" in action.lower() or "escalate" in action.lower()


# ── Phase 3 new category classification ──────────────────────────────────────

def test_audit_notice_classification():
    cat = classify_email(
        "HMRC Compliance Check — Enquiry Reference ENQ-2026-44821",
        "HMRC has opened a formal compliance check into your corporation tax return "
        "for the year ended 31 December 2024. Please provide the requested records.",
    )
    assert cat == "audit_notice"


def test_new_client_onboarding_classification():
    cat = classify_email(
        "Interested in your accounting services",
        "My name is Emily Hayes and I am looking to engage an accountant for my limited company. "
        "I would like to discuss onboarding and your service packages.",
    )
    assert cat == "new_client_onboarding"


def test_payment_confirmation_classification():
    cat = classify_email(
        "Payment Confirmation — Invoice INV-2026-0089",
        "I am pleased to confirm that payment of £6,200 has been sent today by bank transfer "
        "for invoice INV-2026-0089. Please acknowledge receipt.",
    )
    assert cat == "payment_confirmation"


def test_contract_service_question_classification():
    cat = classify_email(
        "Query regarding your service agreement and fee structure",
        "We are considering signing an engagement letter but have some questions about "
        "the scope of services, retainer terms, and your billing policy.",
    )
    assert cat == "contract_service_question"


# ── Phase 3 improved deadline detection ──────────────────────────────────────

def test_deadline_today():
    deadline = detect_deadline(
        "Action required",
        "Please send the signed documents today as we have a submission deadline.",
    )
    assert deadline is not None
    assert "today" in deadline.lower()


def test_deadline_tomorrow():
    deadline = detect_deadline(
        "Action required",
        "We need the VAT figures by tomorrow at the latest or we will miss the filing window.",
    )
    assert deadline is not None
    assert "tomorrow" in deadline.lower()


def test_deadline_by_month_day():
    deadline = detect_deadline(
        "Year-end accounts",
        "Please ensure all receipts are submitted by March 15 to allow time for review.",
    )
    assert deadline is not None
    assert "march" in deadline.lower() or "15" in deadline


def test_deadline_iso_format():
    deadline = detect_deadline(
        "Corporation tax reminder",
        "Please note the deadline is 2026-03-15. Payment must be received before this date.",
    )
    assert deadline is not None
    assert "2026-03-15" in deadline


def test_deadline_next_monday():
    deadline = detect_deadline(
        "Outstanding documents",
        "We require all outstanding documents by next Monday without fail.",
    )
    assert deadline is not None
    assert "monday" in deadline.lower()


# ── Phase 3 priority tests for new categories ─────────────────────────────────

def test_audit_notice_priority_urgent():
    pri = score_priority(
        "HMRC Compliance Check — Enquiry Reference ENQ-2026-44821",
        "HMRC has opened a formal compliance check. Penalty notice may follow. "
        "Please respond urgently within the required deadline.",
    )
    assert pri in ("urgent", "high")


def test_spam_priority_low():
    pri = score_priority(
        "SPECIAL OFFER: 70% OFF accounting software today only!!!",
        "Incredible deal! Click here now before this offer expires! Unsubscribe here.",
    )
    assert pri == "low"
