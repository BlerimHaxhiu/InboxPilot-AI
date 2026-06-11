"""
Human-in-the-loop review workflow.
All actions update the database and create an audit trail in review_log.
No email is ever sent automatically.
"""
from __future__ import annotations
from src import database as db


def approve_draft(email_id: int, note: str = None):
    """Mark the draft reply as approved and set email status to 'approved'."""
    draft = db.get_draft_for_email(email_id)
    if draft:
        db.update_draft_status(draft["id"], "approved")
    db.update_email_status(email_id, "approved")
    db.insert_review_log(email_id, "draft_approved", note)


def reject_draft(email_id: int, note: str = None):
    """Reject the draft reply and set email status to 'rejected'."""
    draft = db.get_draft_for_email(email_id)
    if draft:
        db.update_draft_status(draft["id"], "rejected")
    db.update_email_status(email_id, "rejected")
    db.insert_review_log(email_id, "draft_rejected", note)


def edit_draft(email_id: int, edited_text: str, note: str = None):
    """Save an edited version of the draft and mark email status as 'edited'."""
    draft = db.get_draft_for_email(email_id)
    if draft:
        db.update_draft_status(draft["id"], "edited", edited_text)
    db.update_email_status(email_id, "edited")
    db.insert_review_log(email_id, "draft_edited", note)


def mark_email_reviewed(email_id: int, action: str, note: str = None):
    """Mark an email as reviewed with a custom action label (e.g. 'no_reply_needed')."""
    db.update_email_status(email_id, "reviewed")
    db.insert_review_log(email_id, action, note)


# ── Review queue queries ───────────────────────────────────────────────────────

def get_pending_reviews() -> list[dict]:
    """Processed emails awaiting review (status='pending_review')."""
    return db.get_pending_review_emails()


def get_approved_reviews() -> list[dict]:
    """Emails whose draft has been approved, edited, or marked reviewed."""
    return db.get_completed_review_emails()


def get_rejected_reviews() -> list[dict]:
    """Emails whose draft was rejected."""
    return db.get_rejected_review_emails()


def get_review_history(email_id: int) -> list[dict]:
    """Full audit log for a single email."""
    return db.get_review_log(email_id)
