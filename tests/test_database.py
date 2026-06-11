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


def _sample_email():
    return db.insert_email(
        sender="client@example.com",
        subject="Test Invoice",
        body="Please process Invoice #001. Amount: $500.",
        received_at="2026-06-10 10:00:00",
    )


# ── Email CRUD ────────────────────────────────────────────────────────────────

def test_insert_and_get_email():
    eid = _sample_email()
    assert eid > 0
    email = db.get_email(eid)
    assert email is not None
    assert email["subject"] == "Test Invoice"
    assert email["sender"] == "client@example.com"
    assert email["status"] == "pending_review"


def test_get_all_emails():
    db.insert_email("a@a.com", "Sub A", "Body A", "2026-06-10 09:00:00")
    db.insert_email("b@b.com", "Sub B", "Body B", "2026-06-10 10:00:00")
    emails = db.get_all_emails()
    assert len(emails) == 2


def test_update_email_analysis():
    eid = _sample_email()
    db.update_email_analysis(
        eid, "invoice", "medium", "Invoice received.", "Forward to AP.", "June 25"
    )
    email = db.get_email(eid)
    assert email["category"] == "invoice"
    assert email["priority"] == "medium"
    assert email["summary"] == "Invoice received."
    assert email["detected_deadline"] == "June 25"


def test_update_email_status():
    eid = _sample_email()
    db.update_email_status(eid, "reviewed")
    email = db.get_email(eid)
    assert email["status"] == "reviewed"


# ── Tasks ─────────────────────────────────────────────────────────────────────

def test_insert_and_get_task():
    eid = _sample_email()
    tid = db.insert_task(eid, "Process the invoice", due_date="June 25", priority="medium")
    assert tid > 0
    tasks = db.get_tasks(email_id=eid)
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Process the invoice"
    assert tasks[0]["due_date"] == "June 25"


def test_update_task_status():
    eid = _sample_email()
    tid = db.insert_task(eid, "Do something")
    db.update_task_status(tid, "completed")
    tasks = db.get_tasks(status="completed")
    assert any(t["id"] == tid for t in tasks)


def test_get_tasks_by_status():
    eid = _sample_email()
    db.insert_task(eid, "Open task")
    done_tid = db.insert_task(eid, "Done task")
    db.update_task_status(done_tid, "completed")
    open_tasks = db.get_tasks(status="open")
    done_tasks = db.get_tasks(status="completed")
    assert len(open_tasks) == 1
    assert len(done_tasks) == 1


# ── Draft replies ─────────────────────────────────────────────────────────────

def test_insert_and_get_draft():
    eid = _sample_email()
    did = db.insert_draft_reply(eid, "Dear Client, thank you for your email.")
    assert did > 0
    draft = db.get_draft_for_email(eid)
    assert draft is not None
    assert draft["draft_text"] == "Dear Client, thank you for your email."
    assert draft["status"] == "pending_review"


def test_update_draft_status_approved():
    eid = _sample_email()
    did = db.insert_draft_reply(eid, "Original draft text.")
    db.update_draft_status(did, "approved")
    draft = db.get_draft_for_email(eid)
    assert draft["status"] == "approved"


def test_update_draft_status_with_edited_text():
    eid = _sample_email()
    did = db.insert_draft_reply(eid, "Original text.")
    db.update_draft_status(did, "edited", "Edited and improved text.")
    draft = db.get_draft_for_email(eid)
    assert draft["status"] == "edited"
    assert draft["edited_text"] == "Edited and improved text."


def test_get_all_drafts_filter():
    eid = _sample_email()
    did = db.insert_draft_reply(eid, "Draft text.")
    db.update_draft_status(did, "approved")
    approved = db.get_all_drafts(status="approved")
    pending = db.get_all_drafts(status="pending_review")
    assert len(approved) == 1
    assert len(pending) == 0


# ── Review log ────────────────────────────────────────────────────────────────

def test_insert_and_get_review_log():
    eid = _sample_email()
    db.insert_review_log(eid, "draft_approved", "Looks good")
    log = db.get_review_log(eid)
    assert len(log) == 1
    assert log[0]["action"] == "draft_approved"
    assert log[0]["note"] == "Looks good"


def test_review_log_multiple_entries():
    eid = _sample_email()
    db.insert_review_log(eid, "draft_rejected", "Needs revision")
    db.insert_review_log(eid, "draft_edited", "Fixed")
    log = db.get_review_log(eid)
    assert len(log) == 2


# ── Dashboard metrics ─────────────────────────────────────────────────────────

def test_dashboard_metrics():
    eid = _sample_email()
    db.update_email_analysis(eid, "invoice", "urgent", "Summary", "Action")
    db.insert_task(eid, "Do task")
    metrics = db.get_dashboard_metrics()
    assert metrics["total"] == 1
    assert metrics["urgent"] == 1
    assert metrics["pending_review"] == 1
    assert metrics["tasks"] == 1


def test_dashboard_metrics_draft_breakdown():
    e1 = db.insert_email("a@a.com", "Sub A", "Body", "2026-06-10 09:00:00")
    e2 = db.insert_email("b@b.com", "Sub B", "Body", "2026-06-10 10:00:00")
    e3 = db.insert_email("c@c.com", "Sub C", "Body", "2026-06-10 11:00:00")
    d1 = db.insert_draft_reply(e1, "Draft 1")
    d2 = db.insert_draft_reply(e2, "Draft 2")
    d3 = db.insert_draft_reply(e3, "Draft 3")
    db.update_draft_status(d1, "approved")
    db.update_draft_status(d2, "edited", "Edited text")
    db.update_draft_status(d3, "rejected")
    metrics = db.get_dashboard_metrics()
    assert metrics["approved_only"] == 1
    assert metrics["edited_drafts"] == 1
    assert metrics["approved_drafts"] == 2  # approved + edited
    assert metrics["rejected_drafts"] == 1


def test_clear_all_data():
    eid = _sample_email()
    db.insert_task(eid, "Some task")
    db.insert_draft_reply(eid, "Draft")
    db.insert_review_log(eid, "test_action")
    db.clear_all_data()
    assert db.get_all_emails() == []
    assert db.get_tasks() == []
    assert db.get_all_drafts() == []
    assert db.get_review_log_all() == []


# ── Export helpers ─────────────────────────────────────────────────────────────

def test_get_processed_emails_dataframe_empty():
    import pandas as pd
    df = db.get_processed_emails_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_get_processed_emails_dataframe_with_data():
    import pandas as pd
    db.insert_email("x@x.com", "Subject X", "Body X", "2026-06-10 09:00:00")
    df = db.get_processed_emails_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "sender" in df.columns
    assert "subject" in df.columns
    assert df.iloc[0]["subject"] == "Subject X"


def test_get_tasks_dataframe_empty():
    import pandas as pd
    df = db.get_tasks_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_get_tasks_dataframe_with_data():
    import pandas as pd
    eid = _sample_email()
    db.insert_task(eid, "Invoice review", due_date="2026-06-30", priority="high")
    df = db.get_tasks_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "task_text" in df.columns
    assert df.iloc[0]["task_text"] == "Invoice review"
    assert df.iloc[0]["priority"] == "high"


def test_get_review_log_dataframe_empty():
    import pandas as pd
    df = db.get_review_log_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_get_review_log_dataframe_with_data():
    import pandas as pd
    eid = _sample_email()
    db.insert_review_log(eid, "draft_approved", "Looks good")
    df = db.get_review_log_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "action" in df.columns
    assert df.iloc[0]["action"] == "draft_approved"
    assert "email_subject" in df.columns


# ── Seeder idempotency ─────────────────────────────────────────────────────────

def test_seed_demo_data_is_idempotent(monkeypatch):
    """Calling seed_demo_data() twice must not produce duplicate rows."""
    import src.demo_data as demo_module
    import src.database as db_module2

    monkeypatch.setattr(db_module2, "DB_PATH", db_module.DB_PATH)
    monkeypatch.setattr(demo_module, "_load_json", lambda: [
        {
            "sender": "client@demo.com",
            "subject": "Demo Invoice",
            "body": "Please review invoice #999.",
            "received_at": "2026-06-10 09:00:00",
        }
    ])

    from src.demo_data import seed_demo_data
    n1 = seed_demo_data()
    n2 = seed_demo_data()
    all_emails = db.get_all_emails()
    assert n1 == 1
    assert n2 == 0  # second call skips existing
    assert len(all_emails) == 1  # no duplicates
