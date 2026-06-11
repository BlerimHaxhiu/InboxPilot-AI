# InboxPilot AI — Demo Guide

Practical, step-by-step guide for running and presenting InboxPilot AI.

---

## Quick Setup

```bash
# Clone and install
git clone https://github.com/your-username/inboxpilot-ai.git
cd inboxpilot-ai

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Run
streamlit run app.py
# Opens at http://localhost:8501
```

**No API key required.** All features work in rule-based mode.

---

## Before Any Demo

Run the sanity check to confirm everything is working:

```bash
python scripts/sanity_check.py
```

If all checks pass, you're ready.

Then reset the database so the demo starts clean:
- Navigate to **📥 Inbox Processing**
- Check the **Confirm reset** checkbox
- Click **Reset Database**

---

## Best Demo Path for Recruiters

Use this path for a focused 5-minute walkthrough.

### 1. Dashboard (30 seconds)

Navigate to **📊 Dashboard**.

If the database is empty, you'll see the "No emails yet" empty state with a call to action.

**What to say:**
> "This is the command centre. Once emails are processed, you get a real-time view of workload, urgency distribution, and review status — all derived from the pipeline output."

---

### 2. Inbox Processing — Seed and Process (60 seconds)

Navigate to **📥 Inbox Processing**.

Click **Seed Demo Data** → success banner: "20 demo emails loaded."

Click **Process Unprocessed Emails** → success banner: "Processed 20 emails — 56 tasks, 19 drafts."

**What to say:**
> "The pipeline processes all 20 emails in under 2 seconds. Each one gets a category, priority score, business summary, deadline extraction, action items, and a draft reply — all in one pass. No API key needed."

Point to the filter row. Change **Priority** to `urgent`:

**What to say:**
> "HMRC audit notices and urgent client complaints surface immediately. The team knows exactly where to focus."

Reset the filter to `All`.

---

### 3. Urgent Email — Analysis and Draft (90 seconds)

Navigate to **📋 Review Queue → Pending**.

From the dropdown, select the **HMRC Tax Enquiry** email (search for "ENQ-2026" or "Urgent Compliance").

**Left panel — point out:**
- Category: `audit_notice` — correctly identified
- Priority: `urgent` or `high` — correctly escalated
- Detected deadline: populated from the email body
- Recommended action: "Do not respond without senior partner review"

**Right panel — point out:**
- `DRAFT FOR REVIEW` marker at the top of the draft
- `[TODO: ...]` placeholder — forces the reviewer to fill in specifics
- Review note field

**What to say:**
> "Every generated draft includes placeholders for information only the reviewer knows — client account numbers, specific dates, agreed fees. The system assists; the professional decides. Nothing goes out without explicit approval."

Type a review note: `Reviewed — checked against HMRC portal. Escalating to partner.`

Click **Save Edits**.

---

### 4. Extracted Task (30 seconds)

Still in the Review Queue right panel, point to the **Extracted Tasks** section.

**What to say:**
> "The system also extracted concrete action items from this email — with due date and priority inherited from the email's urgency. These flow directly into the Task Board."

---

### 5. Draft Review — Approve a Simpler Email (30 seconds)

From the pending dropdown, select a payment confirmation or invoice email.

Click **Approve** with note: `Confirmed with accounts.`

Navigate to the **Approved** tab.

**What to say:**
> "Approved drafts move to this tab. Every action is logged with timestamp and note — a full audit trail. Firms can demonstrate to regulators exactly who reviewed what and when."

---

### 6. Task Board (45 seconds)

Navigate to **✅ Task Board**.

Point to the table: task text, priority, due date, owner, status, linked email.

Select a task. Change status to `in_progress`. Assign an owner: `Senior Partner`.

Click **Update Task**.

**What to say:**
> "The task board closes the loop. Email → triage → draft → approval → task → completion. The full workflow in one tool, without stitching together five different systems."

---

### 7. Reports and Export (30 seconds)

Navigate to **📤 Reports & Export**.

Point to the 8 metric tiles:
- Emails processed, high/urgent workload, % reviewed, % tasks complete
- Draft outcomes: approved, edited, rejected

Click **Emails CSV**.

**What to say:**
> "All data exports to CSV or JSON — ready for Excel, Power BI, or a ticketing system. The audit log export satisfies regulatory record-keeping requirements without any additional tooling."

---

### 8. About & Safety (30 seconds)

Navigate to **ℹ️ About & Safety**.

Point to the "Does NOT Do" table.

**What to say:**
> "Safety constraints are enforced in code, not policy. No send mechanism exists anywhere in the codebase. AI output goes through a validation layer and a safety enforcement layer before it reaches storage. This is deliberate — in professional services, the cost of a wrong draft going out is real."

---

## Demonstrating Fallback Mode (No API Key)

The sidebar shows a blue info box:
> "No API key set. Running fully offline."

This is the default mode. All 20 emails process, 19 drafts generate, 56 tasks extract — without any internet access or API call.

**What to say:**
> "Rule-based mode is not a degraded state — it's the tested, deterministic baseline. Every feature works. This is also what lets the test suite run fully offline: 222 tests, no mocking of external services."

---

## Demonstrating OpenAI-Enhanced Mode (With API Key)

1. Create a `.env` file:
   ```
   # Windows
   copy .env.example .env
   # macOS/Linux
   cp .env.example .env
   ```

2. Edit `.env` and set: `OPENAI_API_KEY=sk-...`

3. Restart: `streamlit run app.py`

The sidebar now shows a green success box:
> "OpenAI API key detected — AI-enhanced analysis active."

Process a fresh batch. Open the processing metadata expander on a reviewed email to show AI confidence score and processing mode.

**What to say:**
> "With an API key, the same pipeline upgrades to GPT-4o-mini analysis. The AI output goes through the same validation and safety layers. If the API call fails for any reason, it falls back to rule-based silently — the user never sees an error."

---

## Wrap-Up Q&A Answers

| Question | Answer |
|---|---|
| Does it need an internet connection? | No — fully offline in rule-based mode |
| Does it send emails? | No — no send mechanism exists anywhere |
| What if the OpenAI key fails? | Falls back to rule-based automatically |
| How many tests? | 222 pytest tests, all offline, all isolated |
| How many email categories? | 16 domain-specific categories |
| How is safety enforced? | `ai_validation.py` + `safety.py` + draft review gate |
| Is this production-ready? | No — SQLite demo prototype. Phase 7 would add Gmail/Outlook and multi-user auth |
| Why rule-based + LLM hybrid? | Deterministic baseline + tested upgrade path. Mirrors production AI in regulated industries |
