import os
import pytest
import src.database as db_module
from src import database as db
from src.processor import process_email, process_all_unprocessed_emails, process_all_emails
from src.models import ProcessedEmail, ExtractedTask, DraftReplyResult, ProcessingReport


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    db.init_db()
    yield


def _make_email(subject: str, body: str, sender: str = "client@firm.com") -> dict:
    eid = db.insert_email(
        sender=sender,
        subject=subject,
        body=body,
        received_at="2026-06-10 10:00:00",
    )
    return db.get_email(eid)


# ── process_email return structure ────────────────────────────────────────────

def test_process_email_returns_processed_email():
    email = _make_email(
        "Invoice #001 for services",
        "Please find attached Invoice #001. Amount: $500. Payment terms: Net 30.",
    )
    result = process_email(email)
    assert isinstance(result, ProcessedEmail)


def test_process_email_returns_category():
    email = _make_email(
        "Invoice #001",
        "Please process Invoice #001. Amount due: $500.",
    )
    result = process_email(email)
    assert result.category is not None
    assert isinstance(result.category, str)


def test_process_email_returns_priority():
    email = _make_email(
        "URGENT: Tax deadline tomorrow",
        "Your corporation tax is overdue. Penalties will apply immediately. Do not ignore.",
    )
    result = process_email(email)
    assert result.priority in ("urgent", "high", "medium", "low")
    assert result.priority == "urgent"


def test_process_email_returns_summary():
    email = _make_email(
        "Question about capital gains",
        "I sold my property. Need to understand capital gains tax liability.",
    )
    result = process_email(email)
    assert result.summary is not None
    assert len(result.summary) > 10


def test_process_email_returns_recommended_action():
    email = _make_email(
        "Formal complaint about errors",
        "I am formally complaining about errors in our accounts and overcharging.",
    )
    result = process_email(email)
    assert result.recommended_action is not None
    assert len(result.recommended_action) > 5


def test_process_email_returns_tasks():
    email = _make_email(
        "Please review and confirm",
        "Could you please review our VAT figures and confirm the submission before Friday?",
    )
    result = process_email(email)
    assert isinstance(result.tasks, list)
    assert len(result.tasks) >= 1
    assert all(isinstance(t, ExtractedTask) for t in result.tasks)


def test_process_email_returns_draft_reply():
    email = _make_email(
        "Invoice #INV-001 for April",
        "Please find attached Invoice #INV-001. Amount: $1,000. Net 30 terms.",
    )
    result = process_email(email)
    assert isinstance(result.draft_reply, DraftReplyResult)
    assert len(result.draft_reply.draft_text) > 20


def test_process_email_persists_category_in_db():
    email = _make_email(
        "VAT return Q1 2026",
        "We need help with our VAT return. Input VAT: £10,000. Output VAT: £25,000.",
    )
    result = process_email(email)
    persisted = db.get_email(email["id"])
    assert persisted["category"] == result.category


def test_spam_gets_no_draft_in_db():
    email = _make_email(
        "SPECIAL OFFER: 70% off - Today only!!!",
        "Incredible deal! Click here to claim before it expires in 24 hours! Unsubscribe.",
    )
    result = process_email(email)
    assert result.category == "spam"
    draft = db.get_draft_for_email(email["id"])
    assert draft is None


def test_process_all_unprocessed_emails():
    _make_email("Invoice #001", "Please process Invoice #001. Amount due: $500.")
    _make_email("Appointment request", "I would like to schedule a meeting.")
    report = process_all_unprocessed_emails()
    assert isinstance(report, ProcessingReport)
    assert report.processed == 2
    assert report.tasks_created >= 2
    assert len(report.errors) == 0


def test_detected_deadline_stored():
    email = _make_email(
        "URGENT: Corporation tax due June 20th",
        "Your corporation tax payment of $18,750 is due on June 20, 2026. "
        "Penalties will apply if not paid immediately.",
    )
    result = process_email(email)
    persisted = db.get_email(email["id"])
    # Deadline may be detected in subject or body
    assert persisted["detected_deadline"] is not None or result.detected_deadline is not None


# ── Phase 3 additions ─────────────────────────────────────────────────────────

def test_summary_contains_meaningful_content():
    email = _make_email(
        "R&D tax credit refund - still outstanding",
        "We submitted our R&D tax credit claim of £23,450 four months ago. "
        "We have not yet received the refund. When will payment be made?",
    )
    result = process_email(email)
    assert result.summary is not None
    assert len(result.summary) > 20
    # Summary should contain business-relevant language, not generic placeholder
    assert result.summary.lower() != "client email requires review and response."


def test_task_owner_is_office_team():
    email = _make_email(
        "Invoice #INV-2026-0145 for services",
        "Please find attached our invoice INV-2026-0145 for £4,850. "
        "Please confirm receipt and advise on your payment timeline.",
    )
    result = process_email(email)
    assert len(result.tasks) >= 1
    for task in result.tasks:
        assert task.owner == "Office Team", (
            f"Expected owner='Office Team', got '{task.owner}' for task: {task.task_text}"
        )


def test_task_count_capped_at_five():
    email = _make_email(
        "Multiple action items",
        "Please send the documents. Please confirm receipt. "
        "Please review the figures. Please advise on the tax position. "
        "Please prepare the draft return. Please schedule a call. "
        "Please forward the accounts to your partner. Please respond asap.",
    )
    result = process_email(email)
    assert len(result.tasks) <= 5


def test_category_default_task_always_present():
    # An email with no obvious action verbs should still get the default task
    email = _make_email(
        "Bank statements Q1 2026",
        "Attached are the Q1 2026 bank statements for all three accounts.",
    )
    result = process_email(email)
    assert len(result.tasks) >= 1
    # Category default task should mention "bank" or "bookkeeping" or "reconciliation"
    task_texts = " ".join(t.task_text.lower() for t in result.tasks)
    assert "bank" in task_texts or "reconcil" in task_texts or "bookkeep" in task_texts


def test_audit_notice_processed_correctly():
    email = _make_email(
        "HMRC Compliance Check — Enquiry ENQ-2026-44821",
        "HMRC has opened a formal compliance check into your corporation tax return. "
        "Please provide all records within 30 days. This is urgent.",
        sender="hmrc-notification@gov.uk",
    )
    result = process_email(email)
    assert result.category == "audit_notice"
    assert result.priority in ("urgent", "high")
    assert result.draft_reply is not None
    assert "DRAFT FOR REVIEW" in result.draft_reply.draft_text


# ── Phase 4 — processing metadata ────────────────────────────────────────────

def test_processor_works_without_openai_key(monkeypatch):
    import src.processor as proc_module
    monkeypatch.setattr(proc_module, "HAS_OPENAI", False)
    email = _make_email(
        "Invoice #001",
        "Please find attached Invoice #001. Amount due: $500. Payment terms: Net 30.",
    )
    result = process_email(email)
    assert isinstance(result, ProcessedEmail)
    assert result.category is not None


def test_fallback_used_true_when_no_openai_key(monkeypatch):
    import src.processor as proc_module
    monkeypatch.setattr(proc_module, "HAS_OPENAI", False)
    email = _make_email(
        "Invoice #001",
        "Please find attached Invoice #001. Amount due: $500.",
    )
    result = process_email(email)
    assert result.fallback_used is True
    assert result.ai_used is False


def test_processing_mode_is_rule_based_without_key(monkeypatch):
    import src.processor as proc_module
    monkeypatch.setattr(proc_module, "HAS_OPENAI", False)
    email = _make_email(
        "Tax question",
        "I need advice on my capital gains tax liability.",
    )
    result = process_email(email)
    assert "rule" in result.processing_mode.lower() or "rule-based" in result.processing_mode.lower()


def test_confidence_zero_in_rule_based_mode(monkeypatch):
    import src.processor as proc_module
    monkeypatch.setattr(proc_module, "HAS_OPENAI", False)
    email = _make_email("Invoice", "Please process Invoice #001.")
    result = process_email(email)
    assert result.confidence == 0.0


def test_safety_note_present_in_result(monkeypatch):
    import src.processor as proc_module
    monkeypatch.setattr(proc_module, "HAS_OPENAI", False)
    email = _make_email("General query", "Just a quick question about your office hours.")
    result = process_email(email)
    assert isinstance(result.safety_note, str)
    assert len(result.safety_note) > 0


def test_processing_mode_stored_in_db(monkeypatch):
    import src.processor as proc_module
    monkeypatch.setattr(proc_module, "HAS_OPENAI", False)
    email = _make_email("Invoice #001", "Please process Invoice #001. Amount: $500.")
    process_email(email)
    persisted = db.get_email(email["id"])
    # processing_mode column should exist and be a string after Phase 4 migration
    assert "processing_mode" in persisted
    assert persisted["processing_mode"] is not None


def test_ai_used_false_stored_in_db_without_key(monkeypatch):
    import src.processor as proc_module
    monkeypatch.setattr(proc_module, "HAS_OPENAI", False)
    email = _make_email("Invoice #001", "Please process Invoice #001. Amount: $500.")
    process_email(email)
    persisted = db.get_email(email["id"])
    assert "ai_used" in persisted
    assert not bool(persisted["ai_used"])


def test_ai_enhanced_mode_when_openai_available(monkeypatch):
    """When a mocked AI call succeeds, result should reflect AI-enhanced mode."""
    import src.processor as proc_module
    import src.openai_client as oc_module
    import json

    monkeypatch.setattr(proc_module, "HAS_OPENAI", True)

    ai_response = {
        "category": "tax_question",
        "priority": "high",
        "summary": "Client has a capital gains tax query.",
        "detected_deadline": None,
        "recommended_action": "Prepare response with senior partner review.",
        "tasks": [{"task_text": "Prepare CGT response", "owner": "Office Team", "due_date": None, "priority": "high"}],
        "draft_reply": "Dear Client,\n\nThank you for your tax query. [TODO: Insert response]\n\nKind regards,\n[Your Name]",
        "confidence": 0.92,
        "requires_human_review": True,
        "safety_note": "Reviewed automatically — verify before sending.",
    }

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class _Msg:
                        content = json.dumps(ai_response)
                    class _Choice:
                        message = _Msg()
                    class _Resp:
                        choices = [_Choice()]
                    return _Resp()

    monkeypatch.setattr(oc_module, "_client", lambda: _FakeClient())

    email = _make_email(
        "Capital gains tax question",
        "I sold my property. Need to understand CGT liability.",
    )
    result = process_email(email)

    assert result.ai_used is True
    assert result.fallback_used is False
    assert result.processing_mode == "OpenAI-enhanced mode"
    assert abs(result.confidence - 0.92) < 0.01


# ── Phase 5 — idempotency ─────────────────────────────────────────────────────

def test_reprocess_does_not_duplicate_tasks():
    email = _make_email(
        "Invoice #001",
        "Please process Invoice #001. Amount due: $500. Payment terms: Net 30.",
    )
    process_email(email)
    count_after_first = len(db.get_tasks(email_id=email["id"]))
    process_email(email)
    count_after_second = len(db.get_tasks(email_id=email["id"]))
    assert count_after_second == count_after_first, (
        f"Reprocessing created duplicate tasks: {count_after_first} → {count_after_second}"
    )


def test_reprocess_does_not_duplicate_draft():
    email = _make_email(
        "Invoice #001",
        "Please process Invoice #001. Amount due: $500. Payment terms: Net 30.",
    )
    process_email(email)
    process_email(email)
    all_drafts = db.get_all_drafts()
    email_drafts = [d for d in all_drafts if d["email_id"] == email["id"]]
    assert len(email_drafts) == 1, (
        f"Expected 1 draft after reprocess, found {len(email_drafts)}"
    )


# ── Phase 5 — ProcessingReport ────────────────────────────────────────────────

def test_process_all_unprocessed_returns_report():
    _make_email("Invoice", "Please process Invoice #001. Amount: $500.")
    report = process_all_unprocessed_emails()
    assert isinstance(report, ProcessingReport)


def test_processing_report_counts_processed():
    _make_email("Invoice #001", "Amount: $500.")
    _make_email("Appointment", "I would like to schedule a meeting next week.")
    report = process_all_unprocessed_emails()
    assert report.processed == 2


def test_processing_report_tasks_created():
    _make_email("Invoice #001", "Please process Invoice #001. Amount: $500.")
    report = process_all_unprocessed_emails()
    assert report.tasks_created >= 1


def test_processing_report_drafts_generated():
    _make_email("Invoice #001", "Please process Invoice #001. Amount: $500.")
    report = process_all_unprocessed_emails()
    assert report.drafts_generated >= 1


def test_processing_report_spam_not_counted_as_draft():
    _make_email(
        "SPECIAL OFFER: 70% off!!!",
        "Incredible deal! Click here today! Unsubscribe link below.",
    )
    report = process_all_unprocessed_emails()
    assert report.drafts_generated == 0


def test_process_all_emails_returns_report():
    _make_email("Invoice", "Please process Invoice #001. Amount: $500.")
    # Pre-process so it has a category
    process_all_unprocessed_emails()
    report = process_all_emails()
    assert isinstance(report, ProcessingReport)
    assert report.processed >= 1
