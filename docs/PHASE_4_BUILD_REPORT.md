# Phase 4 Build Report — InboxPilot AI

**Date:** 2026-06-11  
**Status:** Complete  
**Test result:** 173 passed, 0 failed (75 new tests added)

---

## Goal

Upgrade InboxPilot AI from a rule-based prototype into a professional AI automation demo that shows:

- AI-assisted email classification via OpenAI GPT-4o-mini
- Structured JSON output with strict validation
- Safe fallback architecture (rule-based always runs first)
- Human-in-the-loop review enforced at every stage
- Safety enforcement layer that prevents risky language in drafts
- Processing metadata stored per email (mode, ai_used, confidence, safety_note)

---

## Files Created

| File | Purpose |
|------|---------|
| `src/ai_validation.py` | Normalise and validate AI JSON output before use |
| `src/safety.py` | Risky phrase detection, enforcement, review notice management |
| `tests/test_ai_validation.py` | 33 tests for validation layer |
| `tests/test_safety.py` | 21 tests for safety layer |
| `tests/test_openai_client.py` | 14 tests for openai_client (no real key needed) |
| `docs/PHASE_4_BUILD_REPORT.md` | This file |

---

## Files Modified

| File | Changes |
|------|---------|
| `src/models.py` | Added 5 optional metadata fields to `ProcessedEmail` |
| `src/openai_client.py` | Complete rewrite: `analyze_email_with_openai()`, system prompt, `_make_openai_call()` isolated |
| `src/database.py` | `migrate_db()`, `_add_columns_if_missing()`, `insert_draft_reply(ai_generated=)`, `update_email_analysis()` with metadata kwargs |
| `src/processor.py` | New 5-step pipeline: rule-based first → AI → validate → safety → persist |
| `app.py` | Safety warning in sidebar, per-email AI metadata expander |
| `tests/test_processor.py` | +9 Phase 4 tests (fallback, metadata, DB persistence, mocked AI) |
| `README.md` | Complete rewrite: Phase 4 sections, pipeline diagram, safety docs |
| `docs/ARCHITECTURE.md` | AI layer, fallback flow, JSON schema, migration strategy |
| `docs/SAFETY_AND_LIMITATIONS.md` | AI safety boundaries, validated output, fallback mode |

---

## OpenAI Integration Summary

### New function: `analyze_email_with_openai(subject, body, sender) -> dict | None`

- Builds a detailed system prompt that specifies exactly what the model may and may not do
- Passes the 16 valid categories, JSON schema, and all safety constraints to the model
- Uses `response_format={"type": "json_object"}` for reliable JSON output
- Parses and validates the response through `validate_ai_result()`
- Returns `None` on any failure — never raises, never crashes the app

### System prompt safety constraints (verbatim in the prompt):
- "You must not provide final tax or legal advice"
- "You must not claim to be a licensed tax advisor or chartered accountant"
- "You must not state that any email has been sent or will be sent automatically"
- "requires_human_review must always be true"
- All drafts must use [TODO: ...] placeholders

---

## Fallback Behavior

The rule-based pipeline always runs before the AI call. If the AI call:
- Fails (network error, timeout, rate limit) → rule-based result used silently
- Returns invalid JSON → `None` returned, rule-based result used
- Returns wrong category → validated and normalised before use
- Returns `requires_human_review: false` → overridden to `True` by validation layer

`processing_mode`, `ai_used`, `fallback_used` stored in DB on every email.

---

## Validation Behavior

`validate_ai_result()` in `src/ai_validation.py`:

| Input issue | Correction |
|-------------|------------|
| Invalid/unknown category | → `general_inquiry` |
| Category alias (e.g. "tax question") | → `tax_question` |
| Invalid priority | → `medium` |
| Priority alias (e.g. "critical") | → `urgent` |
| Missing summary | → "Email received — requires review." |
| Missing tasks | → `[]` |
| `requires_human_review: false` | → `true` |
| `confidence > 1.0` | → `1.0` |
| `confidence < 0.0` | → `0.0` |
| `confidence: "high"` (non-numeric) | → `0.0` |
| `detected_deadline: "null"` | → `None` |
| Missing safety_note | → default notice |

---

## Safety Layer

`src/safety.py` provides three functions:

1. `contains_risky_claims(draft_text) -> bool`  
   Returns True if any of 11 risky patterns are detected.

2. `enforce_draft_safety(draft_text) -> str`  
   Replaces risky phrases with safe alternatives. Redacts API keys.

3. `append_review_notice_if_needed(draft_text) -> str`  
   Appends `DRAFT FOR REVIEW` notice if not already present. Never duplicates.

All drafts (AI and rule-based) pass through `enforce_draft_safety` + `append_review_notice_if_needed` before being saved to the database.

---

## Database Migration

`migrate_db()` safely adds Phase 4 columns to existing databases:

**emails table:**
- `processing_mode TEXT`
- `ai_used INTEGER DEFAULT 0`
- `fallback_used INTEGER DEFAULT 1`
- `confidence REAL`
- `safety_note TEXT`

**draft_replies table:**
- `ai_generated INTEGER DEFAULT 0`

Migration uses `PRAGMA table_info` to detect existing columns and `ALTER TABLE ADD COLUMN` for missing ones. No data is lost. Safe to run against Phase 2 and Phase 3 databases.

---

## UI Changes

- Sidebar: OPENAI_API_KEY status message (detected / not found)
- Sidebar: Safety reminder banner
- Email Review: "Processing metadata" expander showing:
  - Mode metric (AI / Rule-based)
  - AI used metric (Yes / No)
  - Confidence score (% or N/A)
  - Processing mode label
  - Fallback used flag
  - Safety note

---

## Tests

```
173 passed, 0 failed in 2.34s
```

| File | Tests | What's tested |
|------|-------|---------------|
| test_ai_validation.py | 33 | Category/priority normalization, field validation, confidence clamping, task cleaning |
| test_safety.py | 21 | Risky phrase detection, replacement, review notice, combined pipeline |
| test_openai_client.py | 14 | No-key fallback, mocked valid response, invalid JSON, invalid category/priority, API exceptions |
| test_processor.py (P4 additions) | 9 | Fallback mode, metadata fields, DB persistence, mocked AI integration |

All tests run without a real OpenAI API key using `monkeypatch` and a manual `_MockClient`.

---

## Known Limitations

- Confidence scores are self-reported by the model — not externally calibrated
- AI draft quality depends on the model's context window; very long emails may be truncated
- No retry logic on API failures — fails immediately and falls back to rule-based
- The `_REVIEW_WARNING` constant in `draft_generator.py` and `_REVIEW_NOTICE` in `safety.py` are independent strings; both share the "DRAFT FOR REVIEW" marker but are defined separately

---

## What Remains for Phase 5

- Gmail / Outlook OAuth connector to replace manual demo seeding
- Real-time inbox polling (webhook or scheduled refresh)
- Multi-user authentication and role-based permissions
- Email thread tracking (reply chain context for drafts)
- Response SLA monitoring and dashboard analytics
- Retry logic with exponential backoff for OpenAI API failures
- Caching layer to avoid re-processing already-analysed emails
- Fine-tuned or few-shot classifier using past approved replies as examples
