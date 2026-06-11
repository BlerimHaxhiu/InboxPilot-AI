import os
import pytest
import src.database as db_module
from src import database as db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    db.init_db()
    yield
    if os.path.exists(test_db):
        os.remove(test_db)


def _make_email():
    return db.insert_email(
        sender="client@firm.com",
        subject="Test Email",
        body="Test body.",
        received_at="2026-06-10 10:00:00",
    )


# ── get_all_tasks / get_open_tasks / get_completed_tasks ──────────────────────

def test_get_all_tasks_returns_all():
    eid = _make_email()
    db.insert_task(eid, "Task A")
    db.insert_task(eid, "Task B")
    tasks = db.get_all_tasks()
    assert len(tasks) == 2


def test_get_open_tasks_returns_open_only():
    eid = _make_email()
    db.insert_task(eid, "Open task")
    done_tid = db.insert_task(eid, "Completed task")
    db.update_task_status(done_tid, "completed")
    open_tasks = db.get_open_tasks()
    assert len(open_tasks) == 1
    assert open_tasks[0]["task_text"] == "Open task"


def test_get_completed_tasks_returns_completed_only():
    eid = _make_email()
    db.insert_task(eid, "Open task")
    done_tid = db.insert_task(eid, "Completed task")
    db.update_task_status(done_tid, "completed")
    completed = db.get_completed_tasks()
    assert len(completed) == 1
    assert completed[0]["status"] == "completed"


def test_get_open_tasks_empty_when_none():
    tasks = db.get_open_tasks()
    assert tasks == []


# ── update_task_owner ─────────────────────────────────────────────────────────

def test_update_task_owner():
    eid = _make_email()
    tid = db.insert_task(eid, "Review invoice")
    db.update_task_owner(tid, "Senior Partner")
    tasks = db.get_tasks(email_id=eid)
    assert tasks[0]["owner"] == "Senior Partner"


def test_update_task_owner_allows_reassignment():
    eid = _make_email()
    tid = db.insert_task(eid, "Review filing", owner="Office Team")
    db.update_task_owner(tid, "Tax Manager")
    tasks = db.get_tasks(email_id=eid)
    assert tasks[0]["owner"] == "Tax Manager"


# ── update_task_priority ──────────────────────────────────────────────────────

def test_update_task_priority():
    eid = _make_email()
    tid = db.insert_task(eid, "Process payment", priority="medium")
    db.update_task_priority(tid, "urgent")
    tasks = db.get_tasks(email_id=eid)
    assert tasks[0]["priority"] == "urgent"


def test_update_task_priority_to_low():
    eid = _make_email()
    tid = db.insert_task(eid, "Archive documents", priority="high")
    db.update_task_priority(tid, "low")
    tasks = db.get_tasks(email_id=eid)
    assert tasks[0]["priority"] == "low"


# ── delete_tasks_for_email ────────────────────────────────────────────────────

def test_delete_tasks_for_email_removes_all():
    eid = _make_email()
    db.insert_task(eid, "Task A")
    db.insert_task(eid, "Task B")
    db.delete_tasks_for_email(eid)
    tasks = db.get_tasks(email_id=eid)
    assert tasks == []


def test_delete_tasks_for_email_only_removes_target():
    eid1 = _make_email()
    eid2 = _make_email()
    db.insert_task(eid1, "Task for email 1")
    db.insert_task(eid2, "Task for email 2")
    db.delete_tasks_for_email(eid1)
    assert db.get_tasks(email_id=eid1) == []
    assert len(db.get_tasks(email_id=eid2)) == 1


# ── upsert_draft_reply ────────────────────────────────────────────────────────

def test_upsert_draft_reply_inserts_when_none():
    eid = _make_email()
    did = db.upsert_draft_reply(eid, "Draft text A")
    assert did > 0
    draft = db.get_draft_for_email(eid)
    assert draft["draft_text"] == "Draft text A"


def test_upsert_draft_reply_updates_existing_pending():
    eid = _make_email()
    db.upsert_draft_reply(eid, "First draft")
    db.upsert_draft_reply(eid, "Second draft")
    all_drafts = db.get_all_drafts()
    email_drafts = [d for d in all_drafts if d["email_id"] == eid]
    assert len(email_drafts) == 1
    assert email_drafts[0]["draft_text"] == "Second draft"


def test_upsert_draft_reply_inserts_new_after_approved():
    eid = _make_email()
    did = db.insert_draft_reply(eid, "Approved draft")
    db.update_draft_status(did, "approved")
    db.upsert_draft_reply(eid, "New pending draft after reprocess")
    all_drafts = db.get_all_drafts()
    email_drafts = [d for d in all_drafts if d["email_id"] == eid]
    assert len(email_drafts) == 2
    pending = [d for d in email_drafts if d["status"] == "pending_review"]
    assert len(pending) == 1
    assert pending[0]["draft_text"] == "New pending draft after reprocess"


# ── get_review_log_all ────────────────────────────────────────────────────────

def test_get_review_log_all_returns_all_entries():
    eid1 = _make_email()
    eid2 = _make_email()
    db.insert_review_log(eid1, "draft_approved", "OK")
    db.insert_review_log(eid2, "draft_rejected", "Too vague")
    log = db.get_review_log_all()
    assert len(log) == 2


def test_get_review_log_all_includes_email_metadata():
    eid = _make_email()
    db.insert_review_log(eid, "draft_approved")
    log = db.get_review_log_all()
    assert len(log) == 1
    assert "email_subject" in log[0]
    assert "sender" in log[0]
