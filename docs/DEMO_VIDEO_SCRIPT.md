# InboxPilot AI — Demo Video Script

**Target length:** 2–3 minutes  
**Format:** Screen recording with voiceover  
**Audience:** Technical recruiters and hiring managers for AI Automation Engineer roles

---

## [0:00–0:15] Opening

**Show:** App landing screen (Dashboard — empty state)

**Say:**
> "This is InboxPilot AI — an AI-assisted email workflow automation prototype for professional service firms. It demonstrates a complete end-to-end pipeline: classify emails, score urgency, extract action items, generate draft replies, and route everything through a human review queue — all running locally with no external dependencies."

---

## [0:15–0:35] The Problem

**Show:** Stay on Dashboard — point to the empty state message

**Say:**
> "Professional service firms like accounting and tax practices receive dozens of structured client emails every day. Invoices, VAT queries, payroll requests, HMRC audit notices. Processing them manually means slow responses, missed deadlines, and hours of repetitive typing. The question is: can we automate the triage pipeline without taking human judgement out of client-facing communications?"

---

## [0:35–1:00] Seeding and Processing

**Show:** Navigate to 📥 Inbox Processing. Click **Seed Demo Data**, then **Process Unprocessed Emails**.

**Say:**
> "I'll load 20 realistic demo emails — a simulated inbox for a tax and accounting practice. Then I'll run the processing engine. In under two seconds, every email is classified across 16 domain-specific categories, scored by urgency, given a business summary, had its deadlines extracted, had action items pulled out, and had a professional draft reply generated."

**Show:** Processing success banner. The table populates with emails, priority icons, categories, and detected deadlines.

> "Notice the priority icons — red for urgent, orange for high. HMRC audit notices and client complaints surface immediately."

---

## [1:00–1:30] Dashboard Overview

**Show:** Navigate to 📊 Dashboard.

**Say:**
> "The dashboard gives an office manager everything they need at a glance. Total emails processed, urgent and high-priority workload, how many drafts are pending review, and how many tasks have been extracted. The category chart shows the spread — invoices, VAT queries, audit notices, payroll — exactly what a real practice inbox looks like."

---

## [1:30–2:00] Review Queue — Human-in-the-Loop

**Show:** Navigate to 📋 Review Queue → Pending. Select a high-priority email (HMRC audit notice or urgent complaint).

**Say:**
> "This is the core of the system — the human review queue. On the left: the original email, the AI classification, the priority score, the extracted deadline, and a business summary. On the right: the generated draft reply."

**Show:** The draft text with `[TODO: ...]` placeholders visible. The "DRAFT FOR REVIEW" notice.

> "Every draft has mandatory placeholders that require the reviewer to fill in specifics before sending. The app has no send mechanism — the draft has to be physically approved by a human first."

**Show:** Type a review note, click **Approve**. The audit log entry appears.

> "Every approval — and every rejection — is timestamped and logged. This is the audit trail."

---

## [2:00–2:20] Task Board

**Show:** Navigate to ✅ Task Board.

**Say:**
> "Every processed email automatically generates structured action items — extracted from the email body. Each task has an owner, a due date, and a priority. I can update a task's status to in progress, assign it to a team member, and track it through to completion — directly from the same tool."

---

## [2:20–2:40] Reports and Export

**Show:** Navigate to 📤 Reports & Export.

**Say:**
> "The Reports page gives management-level visibility: what percentage of emails have been reviewed, what percentage of tasks are complete, which category dominates the current workload. All data exports to CSV or JSON — ready to load into Excel, Power BI, or a ticketing system."

---

## [2:40–2:55] Safety and Closing

**Show:** Navigate to ℹ️ About & Safety. Point to the "Does NOT Do" table.

**Say:**
> "One important point: InboxPilot AI is designed with safety as an architectural constraint, not a policy. There is no email send mechanism anywhere in the code. Every draft requires explicit approval. All AI output passes through a validation layer and a safety enforcement layer before it reaches the database. This is what responsible AI automation looks like in a regulated professional services context."

**Show:** Return to Dashboard.

> "The project runs fully offline — no API key, no cloud calls, no authentication. If you add an OpenAI API key, it upgrades to GPT-4o-mini enhanced mode with automatic fallback. 222 automated tests cover every layer. The architecture is built to extend — IMAP polling, multi-user roles, and calendar integration are all natural next steps."

> "InboxPilot AI. AI-assisted workflow automation. Thank you for watching."

---

## Recording Tips

- **Screen resolution:** 1920×1080 or 1440×900
- **Font size:** Increase browser zoom to 110–125% for readability
- **Before recording:** Reset the database so the demo starts clean
- **Recommended order:** Dashboard (empty) → Inbox Processing → Dashboard (populated) → Review Queue → Task Board → Reports → About & Safety
- **Silence between steps:** 0.5–1 second pause when switching pages
- **Total runtime target:** 2 minutes 30 seconds — keep it tight
