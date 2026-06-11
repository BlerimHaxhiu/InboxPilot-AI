# InboxPilot AI — Final Project Audit

Phase 6 audit completed on 2026-06-11.

---

## Audit Checklist

### Source Files

| File | Status | Notes |
|---|---|---|
| `app.py` | ✅ Clean | 6 pages, page_icon=📬, subtitle, empty states, insights |
| `src/config.py` | ✅ Clean | Loads env vars; HAS_OPENAI, PROCESSING_MODE |
| `src/database.py` | ✅ Clean | Full CRUD, migrations, export helpers, clear_all_data |
| `src/classifier.py` | ✅ Clean | 16 categories, 4 priorities, deterministic ordering |
| `src/draft_generator.py` | ✅ Clean | 16 templates, DRAFT FOR REVIEW notice |
| `src/processor.py` | ✅ Clean | Idempotent; returns ProcessingReport |
| `src/models.py` | ✅ Clean | EmailAnalysis, ExtractedTask, DraftReplyResult, ProcessedEmail, ProcessingReport |
| `src/review_workflow.py` | ✅ Clean | approve/reject/edit + query helpers |
| `src/ai_validation.py` | ✅ Clean | Normalise category, priority, enforce required fields |
| `src/safety.py` | ✅ Clean | Risky phrase replacement, review notice enforcement |
| `src/openai_client.py` | ✅ Clean | GPT-4o-mini call + validation; returns None on failure |
| `src/demo_data.py` | ✅ Clean | Idempotent seeder; deduplicates by sender+subject |
| `src/task_extractor.py` | ✅ Kept | Standalone module; has its own tests; not connected to main pipeline |
| `src/demo_emails.py` | ✅ Deleted | Broken orphan — ImportError on `get_emails` (function is `get_all_emails`) |

### Data Files

| File | Status | Notes |
|---|---|---|
| `data/demo_emails.json` | ✅ Clean | 20 realistic tax/accounting emails; fictional clients only |

### Configuration Files

| File | Status | Notes |
|---|---|---|
| `requirements.txt` | ✅ Clean | Removed unused `python-dateutil` |
| `.env.example` | ✅ Clean | Comments explaining each variable; API key left empty |
| `.gitignore` | ✅ Clean | Added `env/`, distribution artifacts, Thumbs.db |

---

## Issues Found and Fixed

### 1. `src/demo_emails.py` — Broken Import

**Issue:** Module had `from src.database import init_db, insert_email, get_emails` at module level. `get_emails` does not exist (function is `get_all_emails`). This caused an `ImportError` on import.

**Additional issues:** Schema was for generic software company emails; incompatible with demo_emails.json structure. Module was not imported anywhere in the active codebase.

**Fix:** Deleted the file.

### 2. `python-dateutil` — Unused Dependency

**Issue:** `requirements.txt` listed `python-dateutil>=2.8.2` but no file in `src/`, `app.py`, or `tests/` imported it.

**Fix:** Removed from requirements.txt.

### 3. `get_dashboard_metrics()` — Draft Count Granularity

**Issue:** `approved_drafts` combined approved and edited statuses into a single count, preventing the Reports page from showing a detailed breakdown.

**Fix:** Added `approved_only` and `edited_drafts` as separate keys; `approved_drafts` retained as the sum for the Dashboard tile.

---

## Test Summary

| Test File | Tests | Coverage Area |
|---|---|---|
| `test_classifier.py` | 38 | 16 categories, 4 priorities, edge cases |
| `test_draft_generator.py` | 26 | All 16 category templates |
| `test_processor.py` | 34 | Processing pipeline, idempotency, ProcessingReport |
| `test_review_workflow.py` | 18 | approve/reject/edit, queue queries |
| `test_task_board.py` | 18 | Task CRUD, upsert, delete_for_email |
| `test_database.py` | 23 | Email/task/draft/log CRUD, export helpers, seeder idempotency |
| `test_ai_validation.py` | 24 | Category/priority normalisation, field enforcement |
| `test_safety.py` | 18 | Risky phrase detection, draft safety, review notice |
| `test_openai_client.py` | 18 | API call, validation, fallback |
| `test_task_extractor.py` | 5 | Standalone task extractor module |
| **Total** | **222** | All offline; no API key required |

---

## Known Limitations

| Limitation | Impact | Acceptable for demo? |
|---|---|---|
| SQLite single-file database | No concurrent writes; not production-ready | Yes — demo only |
| Rule-based classifier is static | Does not learn from new email types | Yes — extensible pattern |
| OpenAI accuracy not guaranteed | GPT-4o-mini may misclassify ambiguous emails | Yes — validation layer compensates |
| No real inbox connection | Demo only; no IMAP/Gmail | Yes — explicitly documented |
| No authentication | All visitors share state on deployed instance | Yes — demo only |
| Ephemeral DB on Streamlit Cloud | Resets on restart | Yes — seeder re-runs in 2 clicks |
| `src/task_extractor.py` API differs | Uses dict return; not connected to main pipeline | Acceptable — has its own tests |

---

## Recommended Phase 7

Based on the current codebase, the highest-value next steps are:

1. **IMAP inbox polling** — real email ingestion with the review gate preserved
2. **Fine-tuned classifier** — train a small model on firm-specific email history
3. **Slack/Teams notification** — "urgent email received" push notification (view-only)
4. **Multi-user support** — separate review queues per reviewer with SQLite WAL mode or PostgreSQL
5. **Webhook export** — push approved tasks to Trello, Jira, or a ticketing system on approval
