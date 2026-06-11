# Phase 3 Build Report — InboxPilot AI

**Date:** 2026-06-11  
**Status:** Complete  
**Test result:** 98 passed, 0 failed

---

## What Was Built

Phase 3 upgraded InboxPilot AI from a working foundation into a recruiter-ready demo prototype. The focus was on demo quality, classifier accuracy, and a production-grade Streamlit UI.

---

## Files Changed

| File | Change |
|------|--------|
| `data/demo_emails.json` | Expanded from 12 to 20 emails covering all 16 categories |
| `src/classifier.py` | Fully rewritten: 16 categories, 11-pattern deadline detector, `_CONTRACT` before `_INVOICE` fix |
| `src/models.py` | `ExtractedTask.owner` default changed to `"Office Team"` |
| `src/database.py` | `get_dashboard_metrics()` returns 8 keys including `high`, `approved_drafts`, `rejected_drafts`; new `clear_all_data()` |
| `src/processor.py` | `_extract_amount()`, `_extract_ref()`, 16 summary templates, `_CATEGORY_DEFAULT_TASKS`, owner="Office Team" |
| `src/draft_generator.py` | 16 professional templates, `_REVIEW_WARNING` constant, 4 new category templates |
| `app.py` | Complete rewrite: 7 metrics, charts, 3-tab layout, export, reset with confirmation, mode indicator |
| `tests/test_classifier.py` | +12 tests: 4 new categories, 5 deadline patterns, 2 priority tests |
| `tests/test_draft_generator.py` | +20 tests: 4 new categories, 15-category `_REVIEW_WARNING` parametrize |
| `tests/test_processor.py` | +5 tests: summary quality, owner="Office Team", task cap, default task, audit notice pipeline |
| `README.md` | Updated: 16 categories, Phase 3 features, export, 98 tests |
| `docs/DEMO_GUIDE.md` | New 5-minute recruiter demo script |
| `docs/PORTFOLIO_VALUE.md` | Updated: AI automation engineer skills mapping |
| `docs/PHASE_3_BUILD_REPORT.md` | This file |

---

## Features Implemented

### Demo Data (20 emails)
- 8 new emails added to reach 20: appointment reschedule, new client onboarding, payment confirmation, late filing concern, HMRC audit notice (ENQ-2026-44821), capital gains follow-up, contract/service query, document clarification
- All emails are realistic for a UK tax/accounting practice
- Emails cover all 16 classifier categories

### Classifier (16 categories)
- 4 new categories: `audit_notice`, `new_client_onboarding`, `payment_confirmation`, `contract_service_question`
- 11-pattern deadline detector ordered most-specific to least-specific (ISO date → month-day → today/tomorrow → weekday)
- Fixed: `bank statement\b` → `bank statements?` (missed plural)
- Fixed: `_CONTRACT` moved before `_INVOICE` to prevent `billing` keyword collision
- Fixed: `compliance check` added to high-priority pattern (audit emails were scoring `medium`)

### Processor
- `_extract_amount()`: extracts £/$€ amounts using regex, embedded in summaries
- `_extract_ref()`: extracts INV/REF/ACC/ENQ references, embedded in summaries
- 16 category-specific summary templates with extracted amounts and refs
- `_CATEGORY_DEFAULT_TASKS`: all 16 categories have a specific default task
- Default task inserted at position 0; verb-matched tasks fill up to cap of 5
- All tasks have `owner="Office Team"`

### Draft Generator
- 16 professional templates covering all categories
- `_REVIEW_WARNING` constant appended to every non-spam draft
- `audit_notice` template explicitly warns client not to contact HMRC directly
- `new_client_onboarding` template covers AML checks, engagement letter, consultation
- `payment_confirmation` template acknowledges receipt and requests accounts confirmation
- `contract_service_question` template offers engagement letter and callback

### Streamlit UI (app.py — complete rewrite)
- **7 metrics**: total, urgent, high, pending review, approved drafts, rejected drafts, tasks
- **Charts**: category distribution (bar chart) + priority distribution (bar chart)
- **Sidebar filters**: category, priority, status — applied to inbox table
- **Export**: Emails CSV, Emails JSON, Tasks CSV via `st.download_button`
- **Reset**: requires confirmation checkbox before clearing all data
- **Mode indicator**: shows rule-based or OpenAI-enhanced with explanatory text
- **Email Review**: full 2-column layout — original + analysis on left, tasks + draft on right
- **Draft workflow**: approve / save edits / reject with optional review note
- **Audit log expander**: shows timestamped history per email
- **Task Board**: filterable table, mark open/in_progress/done via dropdown

---

## Test Results

```
98 passed, 0 failed in 1.18s
```

Breakdown:
- `test_classifier.py`: 31 tests (10 original + 12 new + 9 priority/deadline)
- `test_draft_generator.py`: 32 tests (11 original + 4 new categories + 15 parametrized + 2 warning)
- `test_processor.py`: 16 tests (11 original + 5 new)
- `test_database.py`: 14 tests (unchanged)
- `test_task_extractor.py`: 5 tests (unchanged)

---

## Bugs Fixed in Phase 3

1. **`bank statement` vs `bank statements`** — `_BANK_STMT` regex used `\bbank statement\b` which failed on plural. Fixed with `bank statements?`.

2. **`billing` collision** — `_INVOICE` pattern matched `billing` before `_CONTRACT` could check. Fixed by moving `_CONTRACT` before `_INVOICE` in classifier ordering.

3. **Audit notice priority** — Emails with `HMRC Compliance Check` in subject scored `medium` because `compliance check` was absent from priority patterns. Fixed by adding `hmrc (enquiry|compliance)` and `compliance check` to the high-priority regex.

---

## Known Limitations

- Deadline extraction returns a phrase string, not a parsed `datetime` — suitable for display but not calendar integration
- Classifier uses regex only in rule-based mode — novel phrasing not matching patterns will fall through to `general_inquiry`
- No multi-user support — all drafts visible to any user of the local app
- Export does not include draft reply text — intentional (drafts may contain sensitive TODO placeholders)
- `st.rerun()` pattern means Streamlit re-runs the full script on every interaction — acceptable for a demo, would need caching for a production inbox volume

---

## What Remains for Phase 4

- Gmail / Outlook OAuth connector to replace manual demo seeding
- Real-time inbox polling (websocket or scheduled refresh)
- Multi-user authentication and role-based permissions (reviewer vs approver)
- Email thread tracking (reply chain context for drafts)
- SLA and response-time analytics
- Fine-tuned or prompt-engineered classifier using past approved replies as few-shot examples
