"""
InboxPilot AI — Sanity Check Script

Verifies the full pipeline end-to-end without requiring Streamlit or an OpenAI API key.

Usage:
    python scripts/sanity_check.py

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""
import sys
import os
import tempfile

# Allow running from project root or scripts/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.database as db_module
from src import database as db


def run():
    print("=" * 55)
    print("InboxPilot AI — Sanity Check")
    print("=" * 55)

    errors = []

    # ── 1. Isolated temp database ─────────────────────────────────────────────
    tmp_db = tempfile.mktemp(suffix=".db")
    db_module.DB_PATH = tmp_db

    try:
        print("\n[1] Initialising database...")
        db.init_db()
        print("    OK — schema created")

        # ── 2. Seed demo data ─────────────────────────────────────────────────
        print("\n[2] Seeding demo data...")
        from src.demo_data import seed_demo_data
        n_seeded = seed_demo_data()
        if n_seeded == 0:
            errors.append("seed_demo_data() returned 0 — check data/demo_emails.json")
        else:
            print(f"    OK — {n_seeded} demo email(s) loaded")

        # ── 3. Idempotency check ──────────────────────────────────────────────
        print("\n[3] Seeder idempotency check...")
        n_second = seed_demo_data()
        if n_second != 0:
            errors.append(f"seed_demo_data() second call returned {n_second} (expected 0)")
        else:
            print("    OK — second seed call inserted 0 rows (no duplicates)")

        # ── 4. Process emails ─────────────────────────────────────────────────
        print("\n[4] Processing emails (rule-based mode)...")
        from src.processor import process_all_unprocessed_emails
        report = process_all_unprocessed_emails()
        if report.processed == 0:
            errors.append("process_all_unprocessed_emails() processed 0 emails")
        else:
            print(f"    OK — processed {report.processed} email(s)")
            print(f"         tasks created:    {report.tasks_created}")
            print(f"         drafts generated: {report.drafts_generated}")
            print(f"         ai used:          {report.ai_used_count}")
            print(f"         fallback used:    {report.fallback_used_count}")
            if report.errors:
                print(f"         ERRORS: {report.errors}")
                errors.extend(report.errors)

        # ── 5. Processing idempotency ─────────────────────────────────────────
        print("\n[5] Processing idempotency check...")
        from src.processor import process_all_emails
        report2 = process_all_emails()
        tasks_after = db.get_all_tasks()
        if report2.processed > 0 and len(tasks_after) != report.tasks_created:
            errors.append(
                f"Re-processing changed task count: "
                f"{report.tasks_created} -> {len(tasks_after)}"
            )
        else:
            print(f"    OK — re-process did not duplicate tasks ({len(tasks_after)} tasks)")

        # ── 6. Dashboard metrics ──────────────────────────────────────────────
        print("\n[6] Dashboard metrics...")
        metrics = db.get_dashboard_metrics()
        total = metrics["total"]
        tasks = metrics["tasks"]
        pending = metrics["pending_review"]
        print(f"    total emails:    {total}")
        print(f"    urgent:          {metrics['urgent']}")
        print(f"    high:            {metrics['high']}")
        print(f"    pending review:  {pending}")
        print(f"    tasks:           {tasks}")
        print(f"    drafts pending:  {metrics['drafts_pending']}")
        print(f"    approved_only:   {metrics['approved_only']}")
        print(f"    edited_drafts:   {metrics['edited_drafts']}")
        print(f"    rejected_drafts: {metrics['rejected_drafts']}")
        if total == 0:
            errors.append("No emails found after seeding + processing")
        else:
            print("    OK")

        # ── 7. Export helpers ─────────────────────────────────────────────────
        print("\n[7] Export helpers (DataFrames)...")
        emails_df = db.get_processed_emails_dataframe()
        tasks_df = db.get_tasks_dataframe()
        log_df = db.get_review_log_dataframe()
        print(f"    emails_df rows:      {len(emails_df)}")
        print(f"    tasks_df rows:       {len(tasks_df)}")
        print(f"    review_log_df rows:  {len(log_df)}")
        if len(emails_df) == 0:
            errors.append("get_processed_emails_dataframe() returned empty DataFrame")
        else:
            print("    OK")

        # ── 8. Review workflow ────────────────────────────────────────────────
        print("\n[8] Review workflow (approve one draft)...")
        from src.review_workflow import approve_draft, get_pending_reviews, get_approved_reviews
        pending_before = get_pending_reviews()
        if pending_before:
            eid = pending_before[0]["id"]
            approve_draft(eid, note="Sanity check approval")
            approved = get_approved_reviews()
            if not any(e["id"] == eid for e in approved):
                errors.append(f"approve_draft() did not move email #{eid} to approved")
            else:
                print(f"    OK — email #{eid} approved and appears in approved queue")
        else:
            print("    SKIP — no pending reviews (all emails may be spam or unprocessed)")

        # ── 9. Task update ────────────────────────────────────────────────────
        print("\n[9] Task update...")
        all_tasks = db.get_all_tasks()
        if all_tasks:
            tid = all_tasks[0]["id"]
            db.update_task_status(tid, "in_progress")
            db.update_task_owner(tid, "Sanity Script")
            updated = db.get_tasks(email_id=all_tasks[0]["email_id"])
            match = next((t for t in updated if t["id"] == tid), None)
            if match and match["status"] == "in_progress" and match["owner"] == "Sanity Script":
                print(f"    OK — task #{tid} status=in_progress owner=Sanity Script")
            else:
                errors.append(f"Task #{tid} update did not persist correctly")
        else:
            print("    SKIP — no tasks found")

    finally:
        if os.path.exists(tmp_db):
            os.remove(tmp_db)

    # ── Result ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    if errors:
        print(f"FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        print("=" * 55)
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
        print("=" * 55)
        sys.exit(0)


if __name__ == "__main__":
    run()
