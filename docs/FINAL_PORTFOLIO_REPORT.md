# InboxPilot AI — Final Portfolio Report

---

## 1. Project Summary

InboxPilot AI is an AI-assisted email workflow automation prototype for professional service firms (tax, accounting, legal). It demonstrates a complete end-to-end pipeline: classify incoming emails, score urgency, detect deadlines, extract action items, generate draft replies, and route everything through a human review queue with a full audit trail.

The project runs as a 6-page Streamlit application with a local SQLite database, no external services required, and optional OpenAI GPT-4o-mini enhancement when an API key is available.

---

## 2. Business Problem Solved

Professional service firms receive high volumes of structured client emails daily:
- Invoice submissions and payment queries
- VAT return and payroll requests
- HMRC audit notices with compliance deadlines
- Client complaints requiring prompt escalation
- Missing document requests blocking ongoing work

Manual processing is slow, inconsistent, and creates risk: missed deadlines, duplicated effort, no audit trail, and client reply quality that depends entirely on the individual handling the inbox.

InboxPilot AI automates the triage and drafting pipeline while keeping human professionals in control of every outgoing communication.

---

## 3. Main Features

| Feature | Description |
|---|---|
| Email classification | 16 domain-specific categories: invoice, VAT, payroll, audit_notice, client_complaint, and 11 more |
| Priority scoring | 4 levels: urgent / high / medium / low — deterministic rule-based scoring |
| Deadline detection | Regex extraction of date phrases from email body |
| Business summary | Category-specific summaries generated per email |
| Task extraction | Actionable items with owner defaults and due dates |
| Draft reply generation | 16 professional templates with `[TODO]` placeholders |
| Human review queue | Approve / edit / reject workflow — no auto-send |
| Audit trail | Every review action logged with timestamp and note |
| Task board | Track extracted tasks through to completion |
| Management reports | Workload metrics, review %, task completion %, category breakdown |
| Data export | CSV and JSON for emails, tasks, drafts, and review log |
| Optional AI mode | OpenAI GPT-4o-mini integration with full fallback |

---

## 4. Architecture Summary

```
Demo Emails (data/demo_emails.json)
         ↓
    demo_data.py — idempotent seeder
         ↓
    processor.py — orchestrates the pipeline
         ↓
    ┌────────────────────┐    ┌─────────────────────┐
    │  Rule-based engine │    │  OpenAI client      │
    │  classifier.py     │    │  (optional)         │
    │  draft_generator   │ OR │  ai_validation.py   │
    └────────────────────┘    │  safety.py          │
                              └─────────────────────┘
         ↓
    database.py — SQLite storage
    (emails / tasks / draft_replies / review_log)
         ↓
    app.py — Streamlit 6-page UI
    (Dashboard / Inbox / Review Queue / Task Board / Reports / About)
```

Each layer is fully independent and tested in isolation. The processor returns a `ProcessingReport` dataclass. Processing is idempotent: re-running never duplicates tasks or drafts.

---

## 5. Safety Design

Safety is enforced at three layers:

**Layer 1 — AI validation (`src/ai_validation.py`)**
- Invalid categories normalised to `general_inquiry`
- Invalid priorities normalised to `medium`
- `requires_human_review` always forced to `True`
- Confidence clamped to `[0.0, 1.0]`
- Missing fields filled with safe defaults

**Layer 2 — Safety enforcement (`src/safety.py`)**
- "we guarantee" → "we aim to ensure"
- "this email has been sent" → "this draft is pending review"
- "as your licensed tax advisor" → "as your professional service provider"
- API key patterns → `[REDACTED]`
- `DRAFT FOR REVIEW` notice appended if missing

**Layer 3 — Human review gate**
- All drafts stored with `status='pending_review'`
- No send mechanism exists anywhere in the codebase
- Approval/rejection/editing all require explicit user action
- Every action logged to `review_log` with timestamp and note

---

## 6. Rule-Based Fallback Explanation

Rule-based mode is not a degraded fallback — it is the primary, fully tested baseline.

- **16 category patterns** using ordered regex matching
- **4 priority tiers** with explicit scoring logic
- **Deadline extraction** via date phrase regex
- **16 draft templates** with professional tone and mandatory placeholders
- **Deterministic** — the same email always produces the same result
- **Fully testable** — no mocking of external services needed

All 222 tests run in rule-based mode. No API key is ever required.

---

## 7. Optional OpenAI Mode Explanation

When `OPENAI_API_KEY` is set:

1. The processor calls `analyze_email_with_openai()` with a structured JSON prompt
2. The response is validated by `ai_validation.py` (normalises, clamps, enforces required fields)
3. The draft text passes through `safety.py` (replaces risky phrases)
4. Results stored with `ai_used=True` and the model-reported confidence score
5. If the API call fails for any reason → silent fallback to rule-based

The model used is GPT-4o-mini. The prompt requests structured JSON output with category, priority, summary, recommended_action, detected_deadline, requires_human_review, confidence, and safety_note fields.

---

## 8. Human-in-the-Loop Workflow

```
Email processed → draft stored (status=pending_review)
         ↓
Human opens Review Queue
         ↓
Reads original email ←→ Reads generated draft
         ↓
Edits [TODO] placeholders
         ↓
Adds review note
         ↓
Clicks Approve / Save Edits / Reject
         ↓
Action logged to review_log (timestamp + note)
         ↓
Draft status updated (approved / edited / rejected)
         ↓
Email status updated (approved / edited / rejected)
```

No draft is ever sent automatically. The review queue is the only path to marking a draft as approved.

---

## 9. Testing Summary

| File | Tests | Coverage |
|---|---|---|
| test_classifier.py | 38 | 16 categories, priorities, deadline extraction |
| test_draft_generator.py | 26 | All 16 templates, review warning |
| test_ai_validation.py | 24 | Category/priority normalisation, field enforcement |
| test_safety.py | 18 | Risky phrases, safety enforcement, review notice |
| test_openai_client.py | 18 | API call, validation, no-key fallback |
| test_processor.py | 34 | Full pipeline, idempotency, ProcessingReport |
| test_database.py | 23 | CRUD, migrations, export helpers, seeder idempotency |
| test_review_workflow.py | 18 | Approve/reject/edit, queue queries |
| test_task_board.py | 18 | Task CRUD, owner/priority update, upsert |
| test_task_extractor.py | 5 | Standalone task extractor module |
| **Total** | **222** | All offline — no API key required |

All tests use isolated temporary databases via pytest monkeypatching. No test touches the production `data/inboxpilot.db` file.

---

## 10. Demo Instructions

```bash
pip install -r requirements.txt
streamlit run app.py
# Navigate to http://localhost:8501
```

1. 📥 **Inbox Processing** → Seed Demo Data → Process Unprocessed Emails
2. 📊 **Dashboard** → Review metrics and charts
3. 📋 **Review Queue** → Select an urgent email → Review draft → Approve
4. ✅ **Task Board** → Update a task status and owner
5. 📤 **Reports & Export** → Download Emails CSV
6. ℹ️ **About & Safety** → Review safety constraints

Full demo script: `docs/DEMO_GUIDE.md`  
Video script: `docs/DEMO_VIDEO_SCRIPT.md`

---

## 11. Limitations

| Limitation | Detail |
|---|---|
| No Gmail/Outlook connection | Demo dataset only — no live inbox polling |
| No authentication | Single-user local prototype |
| SQLite concurrency | Not suitable for concurrent multi-user writes |
| Classifier is static | Rule-based patterns don't learn from new data |
| GPT-4o-mini accuracy | Limited for highly ambiguous or multi-topic emails |
| No background processing | Pipeline runs on-click — no scheduling |
| Demo data is fictional | All clients, figures, and scenarios are fabricated |

---

## 12. Future Improvements

| Priority | Feature |
|---|---|
| High | Gmail / Outlook OAuth connector — replace demo seeder with live polling |
| High | Multi-user support — role-based review queues per team member |
| Medium | Calendar integration — booked appointments sync to calendar |
| Medium | Vector search — find similar past emails for context on new drafts |
| Medium | Approval routing — escalation rules for high-priority items |
| Low | Fine-tuned classifier — trained on firm-specific approved replies |
| Low | Richer analytics — response time tracking, SLA monitoring |
| Low | Webhook export — push approved tasks to Jira/Trello on approval |

---

## 13. Suggested GitHub Repository Description

```
AI-assisted email workflow automation prototype for professional service firms.
```

---

## 14. Suggested GitHub Topics

```
ai-automation
streamlit
python
email-processing
workflow-automation
human-in-the-loop
openai
sqlite
portfolio-project
nlp
```

---

## 15. Suggested Commit Message

```
Finalize InboxPilot AI portfolio prototype

Phase 7: repository cleanup, README polish, demo video script,
sanity check script, deployment guide, final portfolio report.
222 tests passing.
```
