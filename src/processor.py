"""
Email processor: orchestrates classify → summarise → task extract → draft → persist.

Processing pipeline (Phase 4):
  1. Rule-based analysis always runs first (guaranteed result)
  2. If OpenAI is available: call analyze_email_with_openai(), validate result
  3. Merge: AI result preferred for text fields; rule-based as fallback
  4. Safety enforcement applied to all drafts
  5. Persist with processing metadata (mode, ai_used, confidence, safety_note)
  6. Return ProcessedEmail with metadata attached

Rule-based mode is not an error — it is a valid, stable fallback architecture.
"""
from __future__ import annotations
import re
from src.config import HAS_OPENAI
from src.models import EmailAnalysis, ExtractedTask, DraftReplyResult, ProcessedEmail, ProcessingReport
from src.classifier import classify_email, score_priority, detect_deadline, recommend_action
from src.draft_generator import generate_draft
from src import database as db
from src import safety

# ── Summary generation ────────────────────────────────────────────────────────

def _extract_amount(text: str) -> str | None:
    m = re.search(
        r'[£$€]\s*[\d,]+(?:\.\d{2})?|\b[\d,]+(?:\.\d{2})?\s*(?:pounds?|dollars?|euros?)\b',
        text, re.I,
    )
    return m.group(0).strip() if m else None


def _extract_ref(text: str) -> str | None:
    m = re.search(r'\b(?:INV|REF|SU|PO|ACC|PROJ|ENQ)[#\-\s]?[\w\-]+\b', text, re.I)
    return m.group(0) if m else None


def _generate_summary(category: str, subject: str, body: str, sender: str) -> str:
    """Generate a 1-2 sentence business-focused summary specific to the category."""
    amount = _extract_amount(f"{subject} {body}")
    ref = _extract_ref(f"{subject} {body}")

    templates: dict[str, str] = {
        "invoice": (
            f"Client has submitted{' ' + ref if ref else ' an invoice'}"
            f"{' for ' + amount if amount else ''}"
            ". Review, confirm receipt, and process within the agreed payment terms."
        ),
        "tax_question": (
            "Client is seeking professional tax guidance"
            f"{' on a matter involving ' + amount if amount else ''}"
            ". Requires review and a carefully worded response with appropriate disclaimers."
        ),
        "missing_document": (
            "Outstanding documents are required before the client's filing can be completed. "
            "Client must be contacted immediately to chase the missing items before the deadline."
        ),
        "appointment_request": (
            "Client has requested an appointment to discuss their accounts or tax affairs. "
            "Check team availability and confirm a suitable date and time."
        ),
        "payroll": (
            "A payroll query has been received requiring specialist input. "
            "Review with the payroll team and respond before the next payroll run."
        ),
        "vat": (
            f"Client requires assistance with their VAT return"
            f"{' involving turnover of ' + amount if amount else ''}"
            ". Prepare or review the return and ensure submission is made before the filing deadline."
        ),
        "bank_statement": (
            "Bank statements have been received from the client for processing. "
            "Acknowledge receipt and assign to the bookkeeping team for reconciliation."
        ),
        "client_complaint": (
            "A formal complaint has been received from the client citing errors and potential overcharging. "
            "This requires immediate escalation to a senior manager and a formal written response."
        ),
        "refund_question": (
            f"Client is following up on a tax refund or repayment claim"
            f"{' of ' + amount if amount else ''}"
            ". Check claim status with HMRC and provide the client with an updated timeline."
        ),
        "urgent_client_issue": (
            "An urgent client matter requiring immediate attention has been flagged. "
            "Escalate to the responsible partner without delay and acknowledge receipt within one hour."
        ),
        "audit_notice": (
            "An official HMRC audit or compliance enquiry notice has been received"
            f"{' — ref ' + ref if ref else ''}"
            ". This requires urgent senior partner review before any response is made."
        ),
        "new_client_onboarding": (
            "A prospective new client has made an enquiry about engaging the firm's services. "
            "Send the onboarding pack, complete AML checks, and schedule an initial consultation."
        ),
        "payment_confirmation": (
            f"Client has confirmed payment"
            f"{' of ' + amount if amount else ''}"
            f"{' for ' + ref if ref else ''}"
            ". Update accounts, mark the invoice as paid, and issue a formal receipt if requested."
        ),
        "contract_service_question": (
            "Client has raised questions about the firm's service agreement, fees, or scope of work. "
            "Prepare a clear explanation of the relevant terms and offer a follow-up call."
        ),
        "general_inquiry": (
            "A general client enquiry has been received. "
            "Review and respond with helpful information, or redirect to the appropriate team."
        ),
        "spam": (
            "This email appears to be promotional or irrelevant to the firm's work. "
            "No action is required — archive as spam."
        ),
    }

    return templates.get(category, "Client email requires review and response.")


# ── Task extraction ───────────────────────────────────────────────────────────

_CATEGORY_DEFAULT_TASKS: dict[str, str] = {
    "invoice": "Review submitted invoice and confirm receipt to client",
    "tax_question": "Prepare professional response to client tax query",
    "missing_document": "Contact client to request outstanding documents before filing deadline",
    "appointment_request": "Check team calendar and confirm appointment with client",
    "payroll": "Review payroll query with payroll specialist and respond before next pay run",
    "vat": "Review VAT figures and prepare draft return for client approval",
    "bank_statement": "File bank statements and assign to bookkeeping team for reconciliation",
    "client_complaint": "Escalate complaint to senior manager and draft formal response within 24 hours",
    "refund_question": "Check refund claim status with HMRC and update client with timeline",
    "urgent_client_issue": "Escalate to responsible partner immediately and acknowledge to client",
    "audit_notice": "Arrange urgent client meeting and begin preparing all records for HMRC",
    "new_client_onboarding": "Send onboarding pack and engagement letter to prospective client",
    "payment_confirmation": "Confirm payment receipt in accounts system and issue formal receipt",
    "contract_service_question": "Prepare service information and fee schedule response for client",
    "general_inquiry": "Review client enquiry and provide helpful professional response",
    "spam": "Archive email as spam — no action required",
}

_ACTION_VERBS = re.compile(
    r"(?:please\s+)?(?:could\s+you\s+)?"
    r"(send|provide|submit|upload|review|confirm|prepare|complete|arrange|"
    r"call|contact|check|follow.?up|schedule|approve|sign|clarify|advise|"
    r"process|forward|escalate|request|respond|reply|file|prepare)\b",
    re.I,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_DATE_IN_SENTENCE = re.compile(
    r"\b(?:by\s+|before\s+|due\s+(?:on\s+|by\s+)?|on\s+|for\s+|until\s+)?"
    r"(?:\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*(?:\s+\d{4})?|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:\s+\d{4})?|"
    r"next\s+\w+|today|tomorrow|monday|tuesday|wednesday|thursday|friday)\b",
    re.I,
)


def _extract_tasks(subject: str, body: str, priority: str, category: str) -> list[ExtractedTask]:
    """Extract actionable tasks from the email body."""
    tasks: list[ExtractedTask] = []
    sentences = _SENTENCE_SPLIT.split(body)
    seen: set[str] = set()

    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 20:
            continue
        m = _ACTION_VERBS.search(sent)
        if not m:
            continue
        task_text = sent[:160].rstrip(".!?,")
        key = task_text[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        due_m = _DATE_IN_SENTENCE.search(sent)
        due = due_m.group(0).strip() if due_m else None
        tasks.append(ExtractedTask(task_text=task_text, owner="Office Team", due_date=due, priority=priority))

    default_task_text = _CATEGORY_DEFAULT_TASKS.get(category, "Review and respond to client email")
    default_key = default_task_text[:60].lower()
    if default_key not in seen:
        tasks.insert(0, ExtractedTask(
            task_text=default_task_text,
            owner="Office Team",
            due_date=detect_deadline(subject, body),
            priority=priority,
        ))

    return tasks[:5]


def _tasks_from_ai(ai_tasks: list[dict], fallback_priority: str) -> list[ExtractedTask]:
    """Convert AI task dicts to ExtractedTask objects."""
    result = []
    for t in ai_tasks[:5]:
        if not isinstance(t, dict) or not t.get("task_text"):
            continue
        result.append(ExtractedTask(
            task_text=str(t["task_text"])[:200],
            owner=str(t.get("owner", "Office Team")) or "Office Team",
            due_date=t.get("due_date") or None,
            priority=str(t.get("priority", fallback_priority)),
        ))
    return result


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_email(email: dict) -> ProcessedEmail:
    """
    Full processing pipeline for a single email.

    Flow:
      rule-based (always) → optional AI enhancement → validation → safety → persist
    """
    email_id = email["id"]
    subject = email["subject"]
    body = email["body"]
    sender = email["sender"]

    # ── Step 1: Rule-based analysis (always runs, guaranteed result) ──────────
    rb_category = classify_email(subject, body)
    rb_priority = score_priority(subject, body)
    rb_deadline = detect_deadline(subject, body)
    rb_rec_action = recommend_action(rb_category, rb_priority, body)
    rb_summary = _generate_summary(rb_category, subject, body, sender)

    # Processing metadata — defaults to rule-based
    processing_mode = "Rule-based mode"
    ai_used = False
    fallback_used = True
    confidence = 0.0
    safety_note = (
        "This analysis was produced by the rule-based engine. "
        "All outputs require human review before use."
    )

    # Final analysis values start as rule-based
    category = rb_category
    priority = rb_priority
    deadline = rb_deadline
    rec_action = rb_rec_action
    summary = rb_summary

    # ── Step 2: Optional AI enhancement ──────────────────────────────────────
    ai_result: dict | None = None
    if HAS_OPENAI:
        try:
            from src.openai_client import analyze_email_with_openai
            ai_result = analyze_email_with_openai(subject, body, sender=sender)
        except Exception:
            ai_result = None

    if ai_result:
        # AI call succeeded — use AI values for primary analysis fields
        category = ai_result["category"]
        priority = ai_result["priority"]
        deadline = ai_result.get("detected_deadline") or rb_deadline
        rec_action = ai_result["recommended_action"]
        summary = ai_result["summary"]
        processing_mode = "OpenAI-enhanced mode"
        ai_used = True
        fallback_used = False
        confidence = ai_result.get("confidence", 0.0)
        safety_note = ai_result.get("safety_note", "")

    # ── Step 3: Persist analysis with metadata ────────────────────────────────
    db.update_email_analysis(
        email_id, category, priority, summary, rec_action, deadline,
        processing_mode=processing_mode,
        ai_used=ai_used,
        fallback_used=fallback_used,
        confidence=confidence,
        safety_note=safety_note,
    )

    # ── Step 4: Task extraction (delete old tasks first for idempotency) ────────
    db.delete_tasks_for_email(email_id)

    if ai_result and ai_result.get("tasks"):
        tasks = _tasks_from_ai(ai_result["tasks"], priority)
        # Ensure at least one task exists even if AI tasks were empty dicts
        if not tasks:
            tasks = _extract_tasks(subject, body, priority, category)
    else:
        tasks = _extract_tasks(subject, body, priority, category)

    for t in tasks:
        db.insert_task(
            email_id=email_id,
            task_text=t.task_text,
            owner=t.owner,
            due_date=t.due_date,
            priority=t.priority,
        )

    # ── Step 5: Draft generation (upsert for idempotency) ────────────────────
    if category == "spam":
        draft_result = DraftReplyResult(
            draft_text="No draft generated — email classified as spam.",
            category="spam",
            ai_generated=False,
        )
    else:
        # Try AI draft first
        ai_draft_text = ai_result.get("draft_reply", "") if ai_result else ""
        if ai_draft_text and ai_draft_text.strip():
            # Apply safety enforcement to AI draft
            ai_draft_text = safety.enforce_draft_safety(ai_draft_text)
            ai_draft_text = safety.append_review_notice_if_needed(ai_draft_text)
            draft_result = DraftReplyResult(
                draft_text=ai_draft_text, category=category, ai_generated=True
            )
            db.upsert_draft_reply(email_id, draft_result.draft_text, ai_generated=True)
        else:
            # Rule-based draft (already includes _REVIEW_WARNING)
            draft_result = generate_draft(category, subject, body, sender)
            db.upsert_draft_reply(email_id, draft_result.draft_text, ai_generated=False)

    return ProcessedEmail(
        email_id=email_id,
        category=category,
        priority=priority,
        summary=summary,
        recommended_action=rec_action,
        detected_deadline=deadline,
        tasks=tasks,
        draft_reply=draft_result,
        processing_mode=processing_mode,
        ai_used=ai_used,
        fallback_used=fallback_used,
        confidence=confidence,
        safety_note=safety_note,
    )


def process_all_unprocessed_emails() -> ProcessingReport:
    """Process all emails that have not yet been classified (category IS NULL)."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM emails WHERE category IS NULL ORDER BY received_at DESC"
        ).fetchall()
    emails = [dict(r) for r in rows]
    report = ProcessingReport()
    for e in emails:
        try:
            result = process_email(e)
            report.processed += 1
            report.tasks_created += len(result.tasks)
            if result.category != "spam":
                report.drafts_generated += 1
            if result.ai_used:
                report.ai_used_count += 1
            else:
                report.fallback_used_count += 1
        except Exception as exc:
            report.errors.append(str(exc))
    return report


def process_all_emails() -> ProcessingReport:
    """Re-process every email in the database."""
    emails = db.get_all_emails()
    report = ProcessingReport()
    for e in emails:
        try:
            result = process_email(e)
            report.processed += 1
            report.tasks_created += len(result.tasks)
            if result.category != "spam":
                report.drafts_generated += 1
            if result.ai_used:
                report.ai_used_count += 1
            else:
                report.fallback_used_count += 1
        except Exception as exc:
            report.errors.append(str(exc))
    return report
