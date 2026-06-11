import sqlite3
import os
from contextlib import contextmanager
from src.config import DB_PATH as _CONFIG_DB_PATH

# Module-level variable — tests can monkeypatch this
DB_PATH: str = _CONFIG_DB_PATH


@contextmanager
def get_conn():
    path = DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS emails (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                sender             TEXT    NOT NULL,
                subject            TEXT    NOT NULL,
                body               TEXT    NOT NULL,
                received_at        TEXT    NOT NULL,
                category           TEXT,
                priority           TEXT,
                summary            TEXT,
                recommended_action TEXT,
                detected_deadline  TEXT,
                status             TEXT    NOT NULL DEFAULT 'pending_review'
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id   INTEGER NOT NULL,
                task_text  TEXT    NOT NULL,
                owner      TEXT,
                due_date   TEXT,
                priority   TEXT,
                status     TEXT    NOT NULL DEFAULT 'open',
                FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS draft_replies (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id     INTEGER NOT NULL,
                draft_text   TEXT    NOT NULL,
                status       TEXT    NOT NULL DEFAULT 'pending_review',
                edited_text  TEXT,
                ai_generated INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS review_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id   INTEGER NOT NULL,
                action     TEXT    NOT NULL,
                note       TEXT,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
            );
        """)
    migrate_db()


def migrate_db():
    """
    Add Phase 4 columns to existing tables if they are missing.
    Safe to call on a fresh DB (columns already present) or an older DB.
    Never drops or recreates tables.
    """
    _add_columns_if_missing("emails", [
        ("processing_mode", "TEXT"),
        ("ai_used",         "INTEGER DEFAULT 0"),
        ("fallback_used",   "INTEGER DEFAULT 1"),
        ("confidence",      "REAL"),
        ("safety_note",     "TEXT"),
    ])
    _add_columns_if_missing("draft_replies", [
        ("ai_generated", "INTEGER DEFAULT 0"),
    ])


def _add_columns_if_missing(table: str, columns: list[tuple[str, str]]):
    """Add columns to a table only if they don't already exist."""
    with get_conn() as conn:
        existing = {
            row[1]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for col_name, col_type in columns:
            if col_name not in existing:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
                )


# ── Email ────────────────────────────────────────────────────────────────────

def insert_email(
    sender: str,
    subject: str,
    body: str,
    received_at: str,
    external_id: str = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO emails (sender, subject, body, received_at) VALUES (?,?,?,?)",
            (sender, subject, body, received_at),
        )
        return cur.lastrowid


def get_all_emails() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM emails ORDER BY received_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_email(email_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM emails WHERE id = ?", (email_id,)
        ).fetchone()
    return dict(row) if row else None


def update_email_analysis(
    email_id: int,
    category: str,
    priority: str,
    summary: str,
    recommended_action: str,
    detected_deadline: str = None,
    *,
    processing_mode: str = "Rule-based mode",
    ai_used: bool = False,
    fallback_used: bool = True,
    confidence: float = 0.0,
    safety_note: str = "",
):
    with get_conn() as conn:
        conn.execute(
            """UPDATE emails
               SET category=?, priority=?, summary=?,
                   recommended_action=?, detected_deadline=?,
                   processing_mode=?, ai_used=?, fallback_used=?,
                   confidence=?, safety_note=?
               WHERE id=?""",
            (
                category, priority, summary, recommended_action, detected_deadline,
                processing_mode, int(ai_used), int(fallback_used),
                confidence, safety_note,
                email_id,
            ),
        )


def update_email_status(email_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE emails SET status=? WHERE id=?", (status, email_id)
        )


def count_emails_with_external_id(external_id: str) -> int:
    """Used by demo seeder to check for duplicates by subject+sender combo."""
    parts = external_id.split("|", 1)
    if len(parts) != 2:
        return 0
    sender, subject = parts
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE sender=? AND subject=?",
            (sender, subject),
        ).fetchone()
    return row[0]


# ── Tasks ────────────────────────────────────────────────────────────────────

def insert_task(
    email_id: int,
    task_text: str,
    owner: str = None,
    due_date: str = None,
    priority: str = "medium",
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (email_id, task_text, owner, due_date, priority) VALUES (?,?,?,?,?)",
            (email_id, task_text, owner, due_date, priority),
        )
        return cur.lastrowid


def get_tasks(email_id: int = None, status: str = None) -> list[dict]:
    clauses, params = [], []
    if email_id is not None:
        clauses.append("email_id = ?")
        params.append(email_id)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM tasks {where} ORDER BY id", params
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_tasks() -> list[dict]:
    return get_tasks()


def get_open_tasks() -> list[dict]:
    return get_tasks(status="open")


def get_completed_tasks() -> list[dict]:
    return get_tasks(status="completed")


def update_task_status(task_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))


def update_task_owner(task_id: int, owner: str):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET owner=? WHERE id=?", (owner, task_id))


def update_task_priority(task_id: int, priority: str):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET priority=? WHERE id=?", (priority, task_id))


def delete_tasks_for_email(email_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE email_id=?", (email_id,))


# ── Draft replies ─────────────────────────────────────────────────────────────

def insert_draft_reply(email_id: int, draft_text: str, ai_generated: bool = False) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO draft_replies (email_id, draft_text, ai_generated) VALUES (?,?,?)",
            (email_id, draft_text, int(ai_generated)),
        )
        return cur.lastrowid


def get_draft_for_email(email_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM draft_replies WHERE email_id=? ORDER BY id DESC LIMIT 1",
            (email_id,),
        ).fetchone()
    return dict(row) if row else None


def get_all_drafts(status: str = None) -> list[dict]:
    clause = "WHERE d.status=?" if status else ""
    params = [status] if status else []
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT d.*, e.sender, e.subject as email_subject "
            f"FROM draft_replies d JOIN emails e ON d.email_id = e.id "
            f"{clause} ORDER BY d.created_at DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_draft_reply(email_id: int, draft_text: str, ai_generated: bool = False) -> int:
    """
    Update the most-recent pending_review draft for this email, or insert a new one.
    Ensures re-processing never creates duplicate pending drafts.
    """
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM draft_replies WHERE email_id=? AND status='pending_review' "
            "ORDER BY id DESC LIMIT 1",
            (email_id,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE draft_replies SET draft_text=?, ai_generated=? WHERE id=?",
                (draft_text, int(ai_generated), existing[0]),
            )
            return existing[0]
        else:
            cur = conn.execute(
                "INSERT INTO draft_replies (email_id, draft_text, ai_generated) VALUES (?,?,?)",
                (email_id, draft_text, int(ai_generated)),
            )
            return cur.lastrowid


def update_draft_status(draft_id: int, status: str, edited_text: str = None):
    with get_conn() as conn:
        if edited_text is not None:
            conn.execute(
                "UPDATE draft_replies SET status=?, edited_text=? WHERE id=?",
                (status, edited_text, draft_id),
            )
        else:
            conn.execute(
                "UPDATE draft_replies SET status=? WHERE id=?", (status, draft_id)
            )


# ── Review log ────────────────────────────────────────────────────────────────

def insert_review_log(email_id: int, action: str, note: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO review_log (email_id, action, note) VALUES (?,?,?)",
            (email_id, action, note),
        )


def get_review_log(email_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM review_log WHERE email_id=? ORDER BY created_at DESC",
            (email_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_review_log_all() -> list[dict]:
    """All review log entries across all emails, joined with email subject/sender."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT rl.*, e.subject AS email_subject, e.sender "
            "FROM review_log rl JOIN emails e ON rl.email_id = e.id "
            "ORDER BY rl.created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Dashboard metrics ─────────────────────────────────────────────────────────

def get_dashboard_metrics() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        urgent = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE priority='urgent'"
        ).fetchone()[0]
        high = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE priority='high'"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE status='pending_review'"
        ).fetchone()[0]
        tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        drafts_pending = conn.execute(
            "SELECT COUNT(*) FROM draft_replies WHERE status='pending_review'"
        ).fetchone()[0]
        approved = conn.execute(
            "SELECT COUNT(*) FROM draft_replies WHERE status='approved'"
        ).fetchone()[0]
        edited = conn.execute(
            "SELECT COUNT(*) FROM draft_replies WHERE status='edited'"
        ).fetchone()[0]
        rejected = conn.execute(
            "SELECT COUNT(*) FROM draft_replies WHERE status='rejected'"
        ).fetchone()[0]
    return {
        "total": total,
        "urgent": urgent,
        "high": high,
        "pending_review": pending,
        "tasks": tasks,
        "drafts_pending": drafts_pending,
        "approved_drafts": approved + edited,
        "approved_only": approved,
        "edited_drafts": edited,
        "rejected_drafts": rejected,
    }


def get_pending_review_emails() -> list[dict]:
    """Processed emails whose status is still 'pending_review'."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM emails WHERE status='pending_review' AND category IS NOT NULL "
            "ORDER BY received_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_completed_review_emails() -> list[dict]:
    """Emails that have been approved, edited, or reviewed."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM emails "
            "WHERE status IN ('approved', 'edited', 'reviewed') "
            "ORDER BY received_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_rejected_review_emails() -> list[dict]:
    """Emails whose draft was rejected."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM emails WHERE status='rejected' ORDER BY received_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Export helpers ─────────────────────────────────────────────────────────────

def get_processed_emails_dataframe():
    import pandas as pd
    data = get_all_emails()
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_tasks_dataframe():
    import pandas as pd
    data = get_tasks()
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_review_log_dataframe():
    import pandas as pd
    data = get_review_log_all()
    return pd.DataFrame(data) if data else pd.DataFrame()


def clear_all_data():
    """Delete all rows from all tables. Schema (tables) are preserved."""
    with get_conn() as conn:
        conn.execute("DELETE FROM review_log")
        conn.execute("DELETE FROM draft_replies")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM emails")
