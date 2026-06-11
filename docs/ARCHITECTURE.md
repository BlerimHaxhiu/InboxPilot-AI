# InboxPilot AI — Architecture

## Processing Pipeline

```
Email arrives (demo data / future: live inbox)
        │
        ▼
   insert_email()               ← database.py
        │
        ▼
   process_email()              ← processor.py
        │
        ├── Step 1: Rule-based analysis (always runs)
        │    ├── classify_email()         ← classifier.py
        │    ├── score_priority()         ← classifier.py
        │    ├── detect_deadline()        ← classifier.py
        │    ├── recommend_action()       ← classifier.py
        │    └── _generate_summary()      ← processor.py
        │
        ├── Step 2: Optional AI enhancement
        │    └── analyze_email_with_openai()    ← openai_client.py
        │         └── validate_ai_result()      ← ai_validation.py
        │
        ├── Step 3: Merge (AI preferred, rule-based as fallback)
        │
        ├── Step 4: Delete existing tasks (idempotency) → Extract tasks
        │    ├── AI tasks (if provided by OpenAI)
        │    └── Rule-based _extract_tasks() (fallback)
        │
        ├── Step 5: Draft generation (upsert — idempotency)
        │    ├── AI draft (if provided, safety-enforced)
        │    └── Rule-based generate_draft() (fallback) ← draft_generator.py
        │
        ├── Step 6: Safety enforcement on all drafts
        │    ├── enforce_draft_safety()         ← safety.py
        │    └── append_review_notice_if_needed() ← safety.py
        │
        └── Step 7: Persist analysis + metadata
             └── update_email_analysis(... processing_mode, ai_used, ...)
        │
        ▼
   SQLite persistence            ← database.py
        ├── emails (analysis + metadata)
        ├── tasks
        └── draft_replies (status: pending_review)
        │
        ▼
   Human Review                  ← review_workflow.py + Streamlit UI
        ├── approve_draft()    → email status: approved
        ├── reject_draft()     → email status: rejected
        ├── edit_draft()       → email status: edited
        └── mark_email_reviewed() → email status: reviewed
        │
        ▼
   review_log                    ← full audit trail
```

## Review Queue Flow

```
New email
   │ status: pending_review
   ▼
Processed by pipeline
   │ category, priority, summary, tasks, draft stored
   ▼
get_pending_reviews()  ← review_workflow.py
   │ shows in Review Queue → Pending tab
   ▼
Human reviewer selects action:
   ├── approve_draft()  → status: approved  → Approved tab
   ├── reject_draft()   → status: rejected  → Rejected tab
   ├── edit_draft()     → status: edited    → Approved tab
   └── mark_email_reviewed() → status: reviewed → Approved tab
```

## Task Board Flow

```
process_email()
   │ delete_tasks_for_email(email_id)  ← idempotency
   ▼
insert_task(email_id, task_text, owner, due_date, priority)
   │ status: open (default)
   ▼
Task Board UI
   ├── update_task_status(id, "in_progress" | "completed" | "blocked")
   ├── update_task_owner(id, owner)
   └── update_task_priority(id, priority)
```

## Idempotency

Re-processing an email that was previously processed does not create duplicates:

```
process_email(email)
   │
   ├── delete_tasks_for_email(email_id)
   │     removes all existing tasks for this email
   │
   ├── [extract and insert tasks fresh]
   │
   └── upsert_draft_reply(email_id, draft_text)
         if pending_review draft exists → UPDATE it
         if not (e.g. was approved) → INSERT new pending_review draft
```

## AI Layer Architecture

### When OpenAI is Available

```
analyze_email_with_openai(subject, body, sender)
        │
        ├── _client()           → openai.OpenAI(api_key=...)
        ├── System prompt       → detailed instructions + safety constraints
        ├── User prompt         → email content + category list + JSON schema
        │
        ▼
   _make_openai_call(client, messages)
        │
        ▼
   json.loads(response.content)
        │
        ▼
   validate_ai_result(raw_dict)  ← ai_validation.py
        ├── normalize_category()
        ├── normalize_priority()
        └── ensure_required_fields()
            ├── Fill missing fields with safe defaults
            ├── Clamp confidence to [0.0, 1.0]
            ├── Force requires_human_review = True
            └── Normalise tasks list
        │
        ▼
   Validated dict | None (on any failure)
```

### When OpenAI is Unavailable or Fails

```
analyze_email_with_openai() returns None
        │
        ▼
Processor uses rule-based result entirely
processing_mode = "Rule-based mode"
ai_used = False
fallback_used = True
confidence = 0.0
```

## Structured JSON Output Schema

The OpenAI call requests this exact JSON structure:

```json
{
  "category": "invoice",
  "priority": "medium",
  "summary": "Client has submitted invoice INV-001 for £4,850.",
  "detected_deadline": "June 30, 2026",
  "recommended_action": "Review and process within 30-day payment terms.",
  "tasks": [
    {
      "task_text": "Review submitted invoice and confirm receipt to client",
      "owner": "Office Team",
      "due_date": null,
      "priority": "medium"
    }
  ],
  "draft_reply": "Dear Client,\n\nThank you for your invoice...",
  "confidence": 0.88,
  "requires_human_review": true,
  "safety_note": "Review all financial figures before sending."
}
```

## Validation Layer (src/ai_validation.py)

| Input | Validation | Default on failure |
|-------|------------|-------------------|
| category | Check against 16 valid values + alias map | general_inquiry |
| priority | Check against urgent/high/medium/low + aliases | medium |
| summary | String, non-empty, max 250 chars | "Email received — requires review." |
| detected_deadline | String or null; null strings normalised | null |
| tasks | List of dicts with task_text, capped at 5 | [] |
| confidence | Float clamped to [0.0, 1.0] | 0.0 |
| requires_human_review | Boolean | always True |
| safety_note | String, non-empty | default notice |

## Safety Layer (src/safety.py)

All generated drafts pass through two functions before storage:

1. `enforce_draft_safety(draft_text)` — replaces risky phrases:
   - "we guarantee" → "we aim to ensure"
   - "this email has been sent" → "this draft is pending review"
   - "as your licensed tax advisor" → "as your professional service provider"
   - Definitive tax/legal advice claims → placeholder text
   - API key patterns → `[REDACTED]`

2. `append_review_notice_if_needed(draft_text)` — ensures `DRAFT FOR REVIEW` notice is present

## Processing Metadata

Each processed email stores these additional fields in the `emails` table:

| Field | Type | Meaning |
|-------|------|---------|
| processing_mode | TEXT | "Rule-based mode" or "OpenAI-enhanced mode" |
| ai_used | INTEGER | 1 if AI analysis was used for final result |
| fallback_used | INTEGER | 1 if rule-based was the final analysis source |
| confidence | REAL | Float 0.0–1.0 (0.0 for rule-based) |
| safety_note | TEXT | Safety reminder from AI or default message |

## ProcessingReport

`process_all_unprocessed_emails()` and `process_all_emails()` return a `ProcessingReport` dataclass:

```python
@dataclass
class ProcessingReport:
    processed: int = 0
    tasks_created: int = 0
    drafts_generated: int = 0
    ai_used_count: int = 0
    fallback_used_count: int = 0
    errors: List[str] = field(default_factory=list)
```

## SQLite Schema

### emails
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | Auto-increment |
| sender | TEXT | From address |
| subject | TEXT | Email subject |
| body | TEXT | Plain text body |
| received_at | TEXT | ISO datetime string |
| category | TEXT | 16 possible values |
| priority | TEXT | urgent / high / medium / low |
| summary | TEXT | AI/rule-based summary |
| recommended_action | TEXT | Action guidance |
| detected_deadline | TEXT | Extracted date string |
| status | TEXT | pending_review / approved / edited / rejected / reviewed |
| processing_mode | TEXT | Rule-based or AI-enhanced |
| ai_used | INTEGER | 0 or 1 |
| fallback_used | INTEGER | 0 or 1 |
| confidence | REAL | 0.0–1.0 |
| safety_note | TEXT | Safety reminder |

### draft_replies
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | |
| email_id | INTEGER FK | References emails(id) |
| draft_text | TEXT | Generated draft |
| status | TEXT | pending_review / approved / edited / rejected |
| edited_text | TEXT | Human-edited version |
| ai_generated | INTEGER | 0 (rule-based) or 1 (AI) |
| created_at | TEXT | ISO datetime |

### tasks
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | |
| email_id | INTEGER FK | References emails(id) |
| task_text | TEXT | Extracted task |
| owner | TEXT | Assignable; default "Office Team" |
| due_date | TEXT | Extracted date |
| priority | TEXT | urgent / high / medium / low |
| status | TEXT | open / in_progress / completed / blocked |

### review_log
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | |
| email_id | INTEGER FK | |
| action | TEXT | draft_approved / draft_rejected / draft_edited / no_reply_needed |
| note | TEXT | Optional reviewer note |
| created_at | TEXT | ISO datetime |

## Schema Migration Strategy

`migrate_db()` is called after `init_db()` on every startup.
It uses `PRAGMA table_info` to detect existing columns and `ALTER TABLE ADD COLUMN` for any missing ones.
Tables are never dropped or recreated.
Safe to run against any existing database from Phase 2, 3, or 4.

## Human-in-the-Loop Workflow

All generated drafts are stored with `status = 'pending_review'`.
Review actions:
1. Recorded in `review_log` with timestamp and optional note
2. Draft status updated (approved / edited / rejected)
3. Email status updated (approved / edited / rejected / reviewed)

No draft is ever automatically sent or marked as sent.

## Reporting and Export

`database.py` provides three DataFrame export helpers:

| Function | Returns |
|---|---|
| `get_processed_emails_dataframe()` | All emails with all analysis fields |
| `get_tasks_dataframe()` | All tasks with owner, status, priority, due date |
| `get_review_log_dataframe()` | Review log joined with email subject and sender |
| `get_all_drafts(status=None)` | Draft replies joined with email metadata |

`get_dashboard_metrics()` returns a dict with:

| Key | Meaning |
|---|---|
| `total` | Total email count |
| `urgent` / `high` | Count by priority |
| `pending_review` | Emails awaiting review |
| `tasks` | Total extracted tasks |
| `drafts_pending` | Draft replies awaiting review |
| `approved_drafts` | Sum of approved + edited drafts |
| `approved_only` | Just approved (not edited) |
| `edited_drafts` | Just edited (approved with edits) |
| `rejected_drafts` | Rejected drafts |
