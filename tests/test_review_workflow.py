import os
import pytest
import src.database as db_module
from src import database as db
from src.processor import process_email
from src.review_workflow import (
    approve_draft,
    reject_draft,
    edit_draft,
    mark_email_reviewed,
    get_pending_reviews,
    get_approved_reviews,
    get_rejected_reviews,
    get_review_history,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    db.init_db()
    yield
    if os.path.exists(test_db):
        os.remove(test_db)


def _processed_email(subject="Invoice #001", body="Please process Invoice #001. Amount: $500."):
    eid = db.insert_email(
        sender="client@firm.com",
        subject=subject,
        body=body,
        received_at="2026-06-10 10:00:00",
    )
    email = db.get_email(eid)
    process_email(email)
    return db.get_email(eid)


# ── approve_draft ─────────────────────────────────────────────────────────────

def test_approve_draft_sets_email_status_approved():
    email = _processed_email()
    approve_draft(email["id"], note="Looks good")
    updated = db.get_email(email["id"])
    assert updated["status"] == "approved"


def test_approve_draft_sets_draft_status_approved():
    email = _processed_email()
    approve_draft(email["id"])
    draft = db.get_draft_for_email(email["id"])
    assert draft["status"] == "approved"


def test_approve_draft_logs_action():
    email = _processed_email()
    approve_draft(email["id"], note="Checked OK")
    log = db.get_review_log(email["id"])
    assert any(entry["action"] == "draft_approved" for entry in log)
    assert any(entry["note"] == "Checked OK" for entry in log)


# ── reject_draft ─────────────────────────────────────────────────────────────

def test_reject_draft_sets_email_status_rejected():
    email = _processed_email()
    reject_draft(email["id"], note="Needs revision")
    updated = db.get_email(email["id"])
    assert updated["status"] == "rejected"


def test_reject_draft_sets_draft_status_rejected():
    email = _processed_email()
    reject_draft(email["id"])
    draft = db.get_draft_for_email(email["id"])
    assert draft["status"] == "rejected"


def test_reject_draft_logs_action():
    email = _processed_email()
    reject_draft(email["id"], note="Too vague")
    log = db.get_review_log(email["id"])
    assert any(entry["action"] == "draft_rejected" for entry in log)


# ── edit_draft ────────────────────────────────────────────────────────────────

def test_edit_draft_sets_email_status_edited():
    email = _processed_email()
    edit_draft(email["id"], edited_text="Updated draft text.", note="Fixed tone")
    updated = db.get_email(email["id"])
    assert updated["status"] == "edited"


def test_edit_draft_saves_edited_text():
    email = _processed_email()
    edit_draft(email["id"], edited_text="Completely revised draft.")
    draft = db.get_draft_for_email(email["id"])
    assert draft["edited_text"] == "Completely revised draft."


def test_edit_draft_logs_action():
    email = _processed_email()
    edit_draft(email["id"], edited_text="Fixed text.", note="Minor edits")
    log = db.get_review_log(email["id"])
    assert any(entry["action"] == "draft_edited" for entry in log)


# ── mark_email_reviewed ───────────────────────────────────────────────────────

def test_mark_email_reviewed_sets_status():
    email = _processed_email()
    mark_email_reviewed(email["id"], "no_reply_needed")
    updated = db.get_email(email["id"])
    assert updated["status"] == "reviewed"


def test_mark_email_reviewed_logs_custom_action():
    email = _processed_email()
    mark_email_reviewed(email["id"], "no_reply_needed", note="Spam-like")
    log = db.get_review_log(email["id"])
    assert any(entry["action"] == "no_reply_needed" for entry in log)


# ── review queue queries ──────────────────────────────────────────────────────

def test_get_pending_reviews_returns_unreviewed_emails():
    email = _processed_email()
    pending = get_pending_reviews()
    ids = [e["id"] for e in pending]
    assert email["id"] in ids


def test_get_pending_reviews_excludes_approved():
    email = _processed_email()
    approve_draft(email["id"])
    pending = get_pending_reviews()
    ids = [e["id"] for e in pending]
    assert email["id"] not in ids


def test_get_approved_reviews_includes_approved():
    email = _processed_email()
    approve_draft(email["id"])
    approved = get_approved_reviews()
    ids = [e["id"] for e in approved]
    assert email["id"] in ids


def test_get_rejected_reviews_includes_rejected():
    email = _processed_email()
    reject_draft(email["id"])
    rejected = get_rejected_reviews()
    ids = [e["id"] for e in rejected]
    assert email["id"] in ids


def test_get_review_history_returns_log_for_email():
    email = _processed_email()
    approve_draft(email["id"], note="OK")
    history = get_review_history(email["id"])
    assert len(history) >= 1
    assert history[0]["action"] == "draft_approved"


def test_get_review_history_empty_before_action():
    email = _processed_email()
    history = get_review_history(email["id"])
    assert history == []
