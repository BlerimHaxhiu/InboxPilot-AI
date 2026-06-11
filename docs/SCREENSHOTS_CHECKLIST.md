# InboxPilot AI — Screenshots Checklist

Capture these screenshots after a fresh seed + process run.  
Save all files to `docs/screenshots/` and embed them in `README.md`.

---

## Setup Before Capturing

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

1. Navigate to **📥 Inbox Processing**
2. Click **Seed Demo Data** — loads 20 demo emails
3. Click **Process Unprocessed Emails** — runs the full pipeline
4. Proceed through the screenshot list below in order

---

## Screenshot 1 — Dashboard

**Filename:** `docs/screenshots/dashboard.png`

**Page:** 📊 Dashboard

**What to show:**
- All 7 metric tiles populated (total, urgent, high, pending, approved, rejected, tasks)
- Both bar charts visible (Emails by Category, Emails by Priority)
- Recent Review Activity section at the bottom (approve at least one draft first)

**Why it matters:**
Shows real-time aggregation across four database tables and demonstrates classification spread across 16 categories without manual tagging.

---

## Screenshot 2 — Inbox Processing

**Filename:** `docs/screenshots/inbox-processing.png`

**Page:** 📥 Inbox Processing

**What to show:**
- Pipeline Controls row (4 buttons visible)
- Filter row (Category / Priority / Status dropdowns)
- Full email table — at least 10 rows with priority icons, categories, detected deadlines visible

**Why it matters:**
Illustrates the classification pipeline output. Priority icons and category labels demonstrate the rule engine working without any ML framework.

---

## Screenshot 3 — Email Detail (Review Queue — Pending)

**Filename:** `docs/screenshots/review-queue.png`

**Page:** 📋 Review Queue → Pending tab

**What to show:**
- An urgent or high-priority email selected (HMRC audit or client complaint recommended)
- Left column: original email body + analysis (category, priority, summary, deadline)
- Right column: editable draft with `[TODO: ...]` placeholder visible + DRAFT FOR REVIEW notice
- Approve / Save Edits / Reject buttons visible

**Why it matters:**
Core human-in-the-loop design. Shows that no draft is sent automatically — explicit approval is required.

---

## Screenshot 4 — Approved Tab

**Filename:** `docs/screenshots/review-queue-approved.png`

**Page:** 📋 Review Queue → Approved tab

**What to show:**
- Approved tab with count badge
- At least one approved email expanded showing final draft text (read-only)
- Audit log entries with timestamps visible

**Why it matters:**
Demonstrates the audit trail — every approval is logged with timestamp and note.

---

## Screenshot 5 — Task Board

**Filename:** `docs/screenshots/task-board.png`

**Page:** ✅ Task Board

**What to show:**
- Task table with 10+ rows: task text, priority, due date, owner, status, linked email subject
- Update Task form visible below the table with a task selected

**Why it matters:**
Shows end-to-end extraction from email body to actionable task with owner and deadline.

---

## Screenshot 6 — Reports & Export

**Filename:** `docs/screenshots/reports-export.png`

**Page:** 📤 Reports & Export

**What to show:**
- All 8 insight metric tiles visible (top two rows)
- "Most common category / priority" info box
- Download buttons section (4 columns)
- Category Breakdown table at bottom

**Why it matters:**
Shows management-level reporting output and data export capability.

---

## Screenshot 7 — About & Safety

**Filename:** `docs/screenshots/about-safety.png`

**Page:** ℹ️ About & Safety

**What to show:**
- "What InboxPilot AI Does NOT Do" table
- Human Review Checklist section
- Processing Modes table

**Why it matters:**
Shows engineering maturity: explicit safety constraints documented at architecture level.

---

## Screenshot 8 — Rule-Based Mode Sidebar

**Filename:** `docs/screenshots/rule-based-mode.png`

**What to show:**
- Sidebar with "📬 InboxPilot AI" title
- Blue info box: "No API key set. Running fully offline."
- Safety notice at the bottom of sidebar

**Why it matters:**
The "works without API key" indicator is a key portfolio differentiator.

---

## Screenshot 9 — OpenAI-Enhanced Mode (if available)

**Filename:** `docs/screenshots/openai-enhanced-mode.png`

**Precondition:** `OPENAI_API_KEY` must be set in `.env`

**What to show:**
- Sidebar green success box: "OpenAI API key detected — AI-enhanced analysis active."
- Processing metadata expander open on a review panel showing AI confidence score

**Why it matters:**
Demonstrates the dual-mode design — same UI, upgraded backend when key is available.

**Skip this screenshot if no API key is available.** Do not fake it.

---

## Embedding in README

Once screenshots are captured, replace the placeholder table in `README.md`:

```markdown
| Dashboard | Review Queue | Task Board |
|---|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Review Queue](docs/screenshots/review-queue.png) | ![Task Board](docs/screenshots/task-board.png) |
```

Add a second row for Reports and About:

```markdown
| Reports & Export | About & Safety |
|---|---|
| ![Reports](docs/screenshots/reports-export.png) | ![About](docs/screenshots/about-safety.png) |
```
