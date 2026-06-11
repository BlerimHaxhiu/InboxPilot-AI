"""
Loads demo_emails.json and seeds the database.
Seeds only if the emails table is empty to prevent duplicate inserts.
"""
from __future__ import annotations
import json
import os
from src.config import DEMO_EMAILS_PATH
from src import database as db


def _load_json() -> list[dict]:
    path = DEMO_EMAILS_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Demo emails file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_demo_data(force: bool = False) -> int:
    """
    Insert demo emails into the database.
    Returns the number of rows inserted.
    Set force=True to insert even if rows already exist.
    """
    db.init_db()

    emails = _load_json()
    inserted = 0

    for e in emails:
        sender = e["sender"]
        subject = e["subject"]
        # Use sender|subject as a uniqueness key
        if not force and db.count_emails_with_external_id(f"{sender}|{subject}") > 0:
            continue
        db.insert_email(
            sender=sender,
            subject=subject,
            body=e["body"],
            received_at=e["received_at"],
        )
        inserted += 1

    return inserted


def is_seeded() -> bool:
    """Return True if there is at least one email in the database."""
    try:
        return len(db.get_all_emails()) > 0
    except Exception:
        return False
