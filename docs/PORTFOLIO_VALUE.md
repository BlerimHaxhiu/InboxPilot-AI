# Portfolio Value — InboxPilot AI

## What This Project Demonstrates

### 1. End-to-End Workflow Automation

InboxPilot AI is a complete, working workflow automation system — not a tutorial or code snippet. It covers:
- Data ingestion and persistence (SQLite, contextmanager pattern, foreign keys)
- Domain-specific NLP pipeline (regex classification, priority scoring, deadline extraction)
- Human-in-the-loop review workflow (no auto-send, mandatory approval, full audit trail)
- Multi-page professional UI (Streamlit 6-page app with charts, filters, export, task management)
- Optional LLM integration (OpenAI GPT-4o-mini) with full offline fallback

### 2. Production-Grade Engineering Practices

- **Typed dataclasses** (`EmailAnalysis`, `ExtractedTask`, `DraftReplyResult`, `ProcessedEmail`, `ProcessingReport`)
- **Separation of concerns**: classifier, processor, draft generator, review workflow, DB layer are fully independent modules
- **Configuration via environment variables** (python-dotenv, no hardcoded secrets)
- **222 pytest tests** with DB isolation via monkeypatching — test every layer independently
- **Idempotent processing** — reprocessing an email replaces tasks and drafts cleanly, no duplicates
- **Audit trail** via `review_log` table — every approval, rejection, and edit logged with timestamp
- **Schema migration** — `migrate_db()` safely adds new columns without dropping data

### 3. Domain Knowledge — Tax & Accounting

The classifier, summaries, tasks, and draft templates demonstrate understanding of professional services operations:
- 16 categories covering the full lifecycle of a tax/accounting inbox
- HMRC-specific workflows (audit notices, compliance checks, VAT returns)
- Correct professional tone with [TODO] placeholders and `DRAFT FOR REVIEW` warnings
- No definitive tax advice generated without disclaimers — appropriate regulatory awareness

### 4. AI Automation Engineer Relevance

This project demonstrates skills directly relevant to AI automation / applied ML engineering roles:

| Skill | How demonstrated |
|-------|-----------------|
| Rule-based NLP | 16-category regex classifier with ordered priority logic |
| LLM integration | OpenAI GPT-4o-mini with graceful degradation |
| Structured output | JSON schema, `validate_ai_result()`, confidence clamping |
| Human-in-the-loop | Mandatory review workflow, no auto-send, audit log |
| Data persistence | SQLite with PRAGMA foreign_keys, contextmanager connection |
| UI prototyping | 6-page Streamlit app with charts, export, filter, task management |
| Test coverage | 222 tests — unit, integration, idempotency, workflow, export helpers |
| Domain modelling | Professional services email taxonomy, 20 realistic test fixtures |
| Security awareness | No credentials hardcoded, no real PII, no auto-send |
| Idempotency design | Re-process safety: delete-then-insert tasks, upsert drafts |

### 5. Workflow Automation Depth

The app demonstrates a complete office workflow loop:

```
Email arrives → Classify + Prioritise → Extract Tasks → Generate Draft
     ↓                                                         ↓
Task Board ←─── assign / update ────────────────── Review Queue
     ↓                                                         ↓
Track work ──────────────────────────────── Approve / Edit / Reject
                                                               ↓
                                              Audit Log (exportable)
```

This maps directly to real automation workflows (Zapier, Make, n8n, internal tooling) where the engineering challenge is not just AI inference but safe, auditable, human-supervised action.

### 6. Extensibility

The architecture is designed for production evolution:

- **Phase 7**: Connect to Gmail/Outlook via OAuth — `demo_data.py` seeder replaced by a live connector
- **Phase 8**: Multi-user auth, team assignment, escalation rules, SLA monitoring
- **Phase 9**: Fine-tuned classifier using past approved replies as few-shot examples; RAG-enhanced drafts

---

## Why Rule-Based + LLM Hybrid?

A pure LLM approach would:
- Require an API key at all times (cost, dependency)
- Be non-deterministic (hard to test reliably)
- Be opaque (hard to explain classification decisions)

A pure rule-based approach would:
- Miss nuanced language patterns
- Struggle with novel email types not anticipated in advance

The hybrid approach delivers:
- 100% testable, offline-capable baseline
- LLM upgrade path that adds value without breaking the system
- Explainable classification (you can always show which pattern matched)
- Full test coverage without requiring a real API key

This mirrors production AI system design in regulated industries — rule-based guardrails with LLM augmentation.

---

## Test Coverage Summary

| File | Tests | What's covered |
|------|-------|----------------|
| test_classifier.py | 38 | 16 categories, deadline patterns, priority scoring |
| test_draft_generator.py | 26 | 16 templates, review warning |
| test_ai_validation.py | 24 | Category/priority normalisation, field validation |
| test_safety.py | 18 | Risky phrase detection, safety enforcement |
| test_openai_client.py | 18 | No-key fallback, mocked responses, invalid output |
| test_processor.py | 34 | Full pipeline, metadata, idempotency, ProcessingReport |
| test_database.py | 23 | CRUD, migration, metrics, export helpers, seeder idempotency |
| test_task_extractor.py | 5 | Task extraction |
| test_review_workflow.py | 18 | Approve/reject/edit, status transitions, review queries |
| test_task_board.py | 18 | Task CRUD, owner/priority update, upsert idempotency |
| **Total** | **222** | |
