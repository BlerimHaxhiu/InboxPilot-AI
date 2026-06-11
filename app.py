"""
InboxPilot AI — Streamlit Application
Phase 6: Portfolio-ready workflow automation demo
Run: streamlit run app.py
"""
import os
import io
import sys
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import streamlit as st

from src.config import PROCESSING_MODE, HAS_OPENAI
from src import database as db
from src.demo_data import seed_demo_data
from src.processor import process_all_unprocessed_emails, process_all_emails
from src.review_workflow import (
    approve_draft,
    reject_draft,
    edit_draft,
    mark_email_reviewed,
    get_pending_reviews,
    get_approved_reviews,
    get_rejected_reviews,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="InboxPilot AI",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
.stAlert p { margin: 0; }
</style>
""", unsafe_allow_html=True)

db.init_db()

# ── Constants ─────────────────────────────────────────────────────────────────

_PRIORITY_ICONS = {"urgent": "🔴", "high": "🟠", "medium": "🔵", "low": "🟢"}
_STATUS_ICONS = {
    "pending_review": "🟡",
    "approved": "✅",
    "edited": "✅",
    "reviewed": "✅",
    "rejected": "✗",
}
_CAT_LABELS = {
    "invoice": "Invoice",
    "tax_question": "Tax Question",
    "missing_document": "Missing Doc",
    "appointment_request": "Appointment",
    "payroll": "Payroll",
    "vat": "VAT",
    "bank_statement": "Bank Stmt",
    "client_complaint": "Complaint",
    "refund_question": "Refund",
    "urgent_client_issue": "Urgent Issue",
    "audit_notice": "Audit Notice",
    "new_client_onboarding": "New Client",
    "payment_confirmation": "Payment Conf.",
    "contract_service_question": "Contract/Svc",
    "general_inquiry": "General",
    "spam": "Spam",
}
_ALL_CATEGORIES = ["All"] + sorted(_CAT_LABELS.keys())
_TASK_STATUSES = ["open", "in_progress", "completed", "blocked"]

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📬 InboxPilot AI")
    st.caption(
        "AI-assisted email triage, task extraction, and draft review "
        "for professional service firms."
    )
    st.divider()

    if HAS_OPENAI:
        st.success(
            f"**{PROCESSING_MODE}**  \n"
            "OpenAI API key detected — AI-enhanced analysis active."
        )
    else:
        st.info(
            f"**{PROCESSING_MODE}**  \n"
            "No API key set. Running fully offline. "
            "All features available without OpenAI."
        )

    st.divider()
    st.markdown("**Navigate**")
    page = st.radio(
        "Navigate",
        [
            "📊 Dashboard",
            "📥 Inbox Processing",
            "📋 Review Queue",
            "✅ Task Board",
            "📤 Reports & Export",
            "ℹ️ About & Safety",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.warning(
        "**Safety:** Draft replies require human review. "
        "The app never sends emails automatically."
    )


# ── Shared helpers ────────────────────────────────────────────────────────────

def _email_label(e: dict) -> str:
    icon = _PRIORITY_ICONS.get(e.get("priority") or "", "⚫")
    pri = (e.get("priority") or "—").upper()
    status = e.get("status", "unprocessed")
    return f"#{e['id']} [{icon} {pri}] {e['subject'][:50]} ({status})"


def _no_data_prompt(message: str = "No data yet."):
    """Standardised empty-state message with a call to action."""
    st.info(
        f"{message}  \n\n"
        "**To get started:** go to **📥 Inbox Processing** in the sidebar, "
        "click **Seed Demo Data**, then **Process Unprocessed Emails**."
    )


def _render_review_panel(email_id: int):
    """Full two-column review panel: original email + analysis on the left; tasks + draft on the right."""
    email = db.get_email(email_id)
    if not email:
        st.error("Email not found.")
        return

    col_left, col_right = st.columns([1, 1])

    # ── Left: original email + analysis ──────────────────────────────────────
    with col_left:
        st.subheader("Original Email")
        st.markdown(f"**From:** {email['sender']}")
        st.markdown(f"**Subject:** {email['subject']}")
        st.markdown(f"**Received:** {email['received_at']}")
        status_val = email.get("status") or "unprocessed"
        status_icon = _STATUS_ICONS.get(status_val, "⚫")
        st.markdown(f"**Status:** {status_icon} `{status_val}`")
        st.divider()
        st.text_area(
            "Body",
            value=email["body"],
            height=220,
            disabled=True,
            key=f"orig_body_{email_id}",
        )

        if email.get("category"):
            st.subheader("Analysis")
            col_a, col_b = st.columns(2)
            col_a.markdown(
                f"**Category:**  \n`{_CAT_LABELS.get(email['category'], email['category'])}`"
            )
            col_b.markdown(
                f"**Priority:**  \n"
                f"{_PRIORITY_ICONS.get(email.get('priority') or '', '')} "
                f"`{(email.get('priority') or '—').upper()}`"
            )
            if email.get("summary"):
                st.info(f"**Summary:** {email['summary']}")
            if email.get("detected_deadline"):
                st.warning(f"**Deadline detected:** {email['detected_deadline']}")
            if email.get("recommended_action"):
                st.markdown(f"**Recommended action:** {email['recommended_action']}")

            proc_mode = email.get("processing_mode") or "Rule-based mode"
            ai_used_val = bool(email.get("ai_used"))
            conf_val = email.get("confidence") or 0.0
            s_note = email.get("safety_note") or ""
            with st.expander("Processing metadata"):
                m1, m2, m3 = st.columns(3)
                m1.metric("Mode", "AI" if ai_used_val else "Rule-based")
                m2.metric("AI used", "Yes" if ai_used_val else "No")
                m3.metric("Confidence", f"{conf_val:.0%}" if ai_used_val else "N/A")
                st.caption(f"**Processing mode:** {proc_mode}")
                if s_note:
                    st.caption(f"**Safety note:** {s_note}")
        else:
            st.info(
                "This email has not been processed yet. "
                "Go to **📥 Inbox Processing** and click **Process Unprocessed Emails**."
            )

    # ── Right: tasks + draft controls ────────────────────────────────────────
    with col_right:
        tasks = db.get_tasks(email_id=email_id)
        if tasks:
            st.subheader(f"Extracted Tasks ({len(tasks)})")
            for t in tasks:
                s_icon = {
                    "open": "⏳", "in_progress": "🔄",
                    "completed": "✅", "blocked": "🚫",
                }.get(t["status"], "⏳")
                with st.expander(
                    f"{s_icon} [{(t.get('priority') or '—').upper()}] {t['task_text'][:65]}"
                ):
                    if t.get("due_date"):
                        st.caption(f"Due: {t['due_date']}")
                    if t.get("owner"):
                        st.caption(f"Owner: {t['owner']}")
                    col_ta, col_tb = st.columns(2)
                    with col_ta:
                        if t["status"] != "completed":
                            if st.button("✅ Complete", key=f"tdone_{t['id']}"):
                                db.update_task_status(t["id"], "completed")
                                st.rerun()
                    with col_tb:
                        if t["status"] == "completed":
                            if st.button("↩ Reopen", key=f"treopen_{t['id']}"):
                                db.update_task_status(t["id"], "open")
                                st.rerun()

        draft = db.get_draft_for_email(email_id)
        st.subheader("Draft Reply")

        if not draft:
            if email.get("category") == "spam":
                st.info("No draft required — email classified as spam and archived.")
            else:
                st.info(
                    "No draft generated yet. "
                    "Process the email first to generate a draft reply."
                )
        elif draft.get("status") == "rejected":
            st.error("This draft was rejected.")
            st.text_area(
                "Rejected draft (read-only)",
                value=draft["draft_text"],
                height=120,
                disabled=True,
                key=f"rej_{email_id}",
            )
        else:
            current_text = draft.get("edited_text") or draft["draft_text"]
            draft_status = draft.get("status", "pending_review")
            ds_icon = _STATUS_ICONS.get(draft_status, "🟡")
            st.caption(f"{ds_icon} Draft status: **{draft_status}**")

            ai_badge = "🤖 AI-generated" if draft.get("ai_generated") else "📝 Rule-based"
            st.caption(ai_badge)

            st.warning(
                "Review required: edit the draft below, then approve or reject. "
                "Fill in all `[TODO: ...]` placeholders before approving."
            )

            edited = st.text_area(
                "Draft reply (edit before approving)",
                value=current_text,
                height=300,
                key=f"draft_edit_{email_id}",
            )

            review_note = st.text_input(
                "Review note (optional)",
                placeholder="e.g. Approved after fee check with partner",
                key=f"note_{email_id}",
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Approve", key=f"approve_{email_id}", type="primary"):
                    note = review_note or "Approved"
                    if edited != current_text:
                        edit_draft(email_id, edited, note=f"Approved with edits — {note}")
                    else:
                        approve_draft(email_id, note=note)
                    st.success("Draft approved and logged.")
                    st.rerun()
            with col2:
                if st.button("💾 Save Edits", key=f"save_{email_id}"):
                    edit_draft(email_id, edited, note=review_note or "Manual edits saved")
                    st.success("Edits saved.")
                    st.rerun()
            with col3:
                if st.button("✗ Reject", key=f"reject_{email_id}"):
                    reject_draft(email_id, note=review_note or "Rejected by reviewer")
                    st.warning("Draft rejected.")
                    st.rerun()

        if email.get("status") == "pending_review":
            st.divider()
            if st.button(
                "Mark Reviewed — no reply needed", key=f"noreply_{email_id}"
            ):
                mark_email_reviewed(email_id, "no_reply_needed")
                st.success("Marked as reviewed.")
                st.rerun()

        log = db.get_review_log(email_id)
        if log:
            with st.expander(f"Audit log ({len(log)} entr{'y' if len(log)==1 else 'ies'})"):
                for entry in log:
                    note_str = f": {entry['note']}" if entry.get("note") else ""
                    st.caption(
                        f"`{entry['created_at'][:16]}` — **{entry['action']}**{note_str}"
                    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def _page_dashboard():
    st.title("📊 Dashboard")
    st.caption(
        "Real-time overview of your email processing pipeline. "
        "Seed and process demo emails to populate this view."
    )

    metrics = db.get_dashboard_metrics()

    if metrics["total"] == 0:
        _no_data_prompt("No emails in the database yet.")
        return

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Total Emails", metrics["total"])
    c2.metric("🔴 Urgent", metrics["urgent"])
    c3.metric("🟠 High Priority", metrics["high"])
    c4.metric("🟡 Pending Review", metrics["pending_review"])
    c5.metric("✅ Drafts Approved", metrics["approved_drafts"])
    c6.metric("✗ Drafts Rejected", metrics["rejected_drafts"])
    c7.metric("📌 Tasks Extracted", metrics["tasks"])

    st.divider()

    all_emails = db.get_all_emails()
    df = pd.DataFrame(all_emails)
    has_analysis = df["category"].notna().any()

    if has_analysis:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("Emails by Category")
            cat_counts = (
                df["category"]
                .dropna()
                .map(lambda c: _CAT_LABELS.get(c, c))
                .value_counts()
                .reset_index()
            )
            cat_counts.columns = ["Category", "Count"]
            st.bar_chart(cat_counts.set_index("Category"))

        with chart_col2:
            st.subheader("Emails by Priority")
            pri_order = ["urgent", "high", "medium", "low"]
            pri_counts = (
                df["priority"]
                .dropna()
                .value_counts()
                .reindex(pri_order, fill_value=0)
                .reset_index()
            )
            pri_counts.columns = ["Priority", "Count"]
            st.bar_chart(pri_counts.set_index("Priority"))

        st.divider()
    else:
        st.info(
            "Emails are loaded but not yet processed. "
            "Go to **📥 Inbox Processing** and click **Process Unprocessed Emails**."
        )

    log_all = db.get_review_log_all()
    if log_all:
        st.subheader("Recent Review Activity")
        for entry in log_all[:8]:
            subject = entry.get("email_subject", "—")[:50]
            note_str = f" — {entry['note']}" if entry.get("note") else ""
            st.caption(
                f"`{entry['created_at'][:16]}` **{entry['action']}** on "
                f"*{subject}* (#{entry['email_id']}){note_str}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — INBOX PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def _page_inbox():
    st.title("📥 Inbox Processing")
    st.caption(
        "Load demo emails, run the processing pipeline, and browse the classified inbox."
    )

    # ── Controls ──────────────────────────────────────────────────────────────
    with st.expander("⚙️ Pipeline Controls", expanded=True):
        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            if st.button("🌱 Seed Demo Data", use_container_width=True):
                with st.spinner("Loading 20 demo emails..."):
                    n = seed_demo_data()
                if n > 0:
                    st.success(f"✅ {n} demo email(s) loaded successfully.")
                else:
                    st.info(
                        "Demo emails are already present. "
                        "Reset the database first to reload them."
                    )
                st.rerun()

        with col_b:
            if st.button("⚡ Process Unprocessed", use_container_width=True):
                with st.spinner("Processing emails..."):
                    report = process_all_unprocessed_emails()
                if report.processed == 0:
                    st.info("No unprocessed emails found. All emails have already been classified.")
                else:
                    st.success(
                        f"✅ Processed **{report.processed}** email(s) — "
                        f"{report.tasks_created} tasks extracted, "
                        f"{report.drafts_generated} drafts generated."
                    )
                    if report.errors:
                        st.warning(
                            f"{len(report.errors)} error(s) during processing: "
                            f"{'; '.join(report.errors[:3])}"
                        )
                st.rerun()

        with col_c:
            if st.button("🔄 Re-process All", use_container_width=True):
                with st.spinner("Re-processing all emails..."):
                    report = process_all_emails()
                st.success(
                    f"✅ Re-processed **{report.processed}** email(s) — "
                    f"{report.tasks_created} tasks, {report.drafts_generated} drafts."
                )
                st.rerun()

        with col_d:
            reset_confirmed = st.checkbox(
                "Confirm reset", key="inbox_reset_check",
                help="Check this box to enable the reset button."
            )
            if st.button(
                "🗑️ Reset Database",
                use_container_width=True,
                disabled=not reset_confirmed,
                type="secondary",
            ):
                db.clear_all_data()
                st.success("Database cleared. All data removed; schema preserved.")
                st.rerun()

    # ── Filters ───────────────────────────────────────────────────────────────
    all_emails = db.get_all_emails()
    if not all_emails:
        _no_data_prompt("No emails loaded yet. Click **Seed Demo Data** above to get started.")
        return

    fc1, fc2, fc3 = st.columns(3)
    filter_cat = fc1.selectbox("Category", _ALL_CATEGORIES, key="ib_cat")
    filter_priority = fc2.selectbox(
        "Priority", ["All", "urgent", "high", "medium", "low"], key="ib_pri"
    )
    filter_status = fc3.selectbox(
        "Status",
        ["All", "pending_review", "approved", "edited", "rejected", "reviewed"],
        key="ib_stat",
    )

    filtered = all_emails
    if filter_cat != "All":
        filtered = [e for e in filtered if e.get("category") == filter_cat]
    if filter_priority != "All":
        filtered = [e for e in filtered if e.get("priority") == filter_priority]
    if filter_status != "All":
        filtered = [e for e in filtered if e.get("status") == filter_status]

    st.subheader(f"Inbox — {len(filtered)} email(s)")

    if not filtered:
        st.info("No emails match the current filter. Try adjusting the filter options above.")
    else:
        rows = []
        for e in filtered:
            rows.append({
                "ID": e["id"],
                "P": _PRIORITY_ICONS.get(e.get("priority") or "", "⚫"),
                "Sender": e["sender"],
                "Subject": e["subject"][:65],
                "Category": _CAT_LABELS.get(e.get("category") or "", "—"),
                "Priority": (e.get("priority") or "—").upper(),
                "Status": e.get("status") or "unprocessed",
                "Deadline": e.get("detected_deadline") or "—",
                "Received": (e.get("received_at") or "")[:16],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — REVIEW QUEUE
# ══════════════════════════════════════════════════════════════════════════════

def _page_review_queue():
    st.title("📋 Review Queue")
    st.caption(
        "Review, edit, approve, or reject AI-generated draft replies. "
        "Every action is recorded in the audit log."
    )

    pending = get_pending_reviews()
    approved = get_approved_reviews()
    rejected = get_rejected_reviews()

    tab_pending, tab_approved, tab_rejected = st.tabs([
        f"🟡 Pending ({len(pending)})",
        f"✅ Approved ({len(approved)})",
        f"✗ Rejected ({len(rejected)})",
    ])

    # ── Pending ───────────────────────────────────────────────────────────────
    with tab_pending:
        if not pending:
            if db.get_dashboard_metrics()["total"] == 0:
                _no_data_prompt("No emails in the database.")
            else:
                st.success(
                    "🎉 No emails pending review — all processed emails have been actioned. "
                    "Re-process emails or reset the database to start a fresh demo."
                )
        else:
            st.caption(
                f"{len(pending)} email(s) awaiting review. "
                "Select an email below, review the draft, then approve, edit, or reject."
            )
            options = {_email_label(e): e["id"] for e in pending}
            selected_label = st.selectbox(
                "Select email to review", list(options.keys()), key="rq_pending_sel"
            )
            st.divider()
            _render_review_panel(options[selected_label])

    # ── Approved ──────────────────────────────────────────────────────────────
    with tab_approved:
        if not approved:
            st.info("No approved emails yet. Approve drafts in the Pending tab.")
        else:
            st.caption(f"{len(approved)} email(s) reviewed and accepted.")
            for e in approved:
                with st.expander(
                    f"{_PRIORITY_ICONS.get(e.get('priority') or '', '')} "
                    f"#{e['id']} {e['subject'][:60]} — `{e.get('status')}`"
                ):
                    st.markdown(f"**From:** {e['sender']}")
                    if e.get("summary"):
                        st.caption(f"Summary: {e['summary']}")
                    draft = db.get_draft_for_email(e["id"])
                    if draft:
                        final_text = draft.get("edited_text") or draft["draft_text"]
                        st.text_area(
                            "Final draft (read-only)",
                            value=final_text,
                            height=120,
                            disabled=True,
                            key=f"ap_draft_{e['id']}",
                        )
                    log = db.get_review_log(e["id"])
                    if log:
                        for entry in log:
                            note_str = f": {entry['note']}" if entry.get("note") else ""
                            st.caption(
                                f"`{entry['created_at'][:16]}` **{entry['action']}**{note_str}"
                            )

    # ── Rejected ──────────────────────────────────────────────────────────────
    with tab_rejected:
        if not rejected:
            st.info("No rejected drafts.")
        else:
            st.caption(f"{len(rejected)} email(s) where the draft was rejected.")
            for e in rejected:
                with st.expander(
                    f"{_PRIORITY_ICONS.get(e.get('priority') or '', '')} "
                    f"#{e['id']} {e['subject'][:60]}"
                ):
                    st.markdown(f"**From:** {e['sender']}")
                    if e.get("summary"):
                        st.caption(f"Summary: {e['summary']}")
                    draft = db.get_draft_for_email(e["id"])
                    if draft:
                        st.text_area(
                            "Rejected draft (read-only)",
                            value=draft["draft_text"],
                            height=100,
                            disabled=True,
                            key=f"rej_view_{e['id']}",
                        )
                    log = db.get_review_log(e["id"])
                    if log:
                        for entry in log:
                            note_str = f": {entry['note']}" if entry.get("note") else ""
                            st.caption(
                                f"`{entry['created_at'][:16]}` **{entry['action']}**{note_str}"
                            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — TASK BOARD
# ══════════════════════════════════════════════════════════════════════════════

def _page_task_board():
    st.title("✅ Task Board")
    st.caption(
        "All action items extracted from processed emails. "
        "Update status, owner, and priority as work progresses."
    )

    tc1, _tc2 = st.columns([1, 3])
    status_filter = tc1.selectbox(
        "Filter by status",
        ["all"] + _TASK_STATUSES,
        key="tb_status",
    )

    tasks_all = db.get_tasks(status=None if status_filter == "all" else status_filter)

    if not tasks_all:
        if status_filter == "all":
            _no_data_prompt("No tasks found.")
        else:
            st.info(
                f"No tasks with status **{status_filter}**. "
                "Change the filter above to see other tasks."
            )
        return

    rows = []
    for t in tasks_all:
        email_rec = db.get_email(t["email_id"]) or {}
        rows.append({
            "ID": t["id"],
            "Task": t["task_text"][:85],
            "Priority": (t.get("priority") or "—").upper(),
            "Due Date": t.get("due_date") or "—",
            "Owner": t.get("owner") or "Office Team",
            "Status": t.get("status") or "open",
            "Email Subject": email_rec.get("subject", "—")[:55],
            "From": email_rec.get("sender", "—"),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"{len(tasks_all)} task(s) shown")

    st.divider()
    st.subheader("Update Task")

    task_ids = [t["id"] for t in tasks_all]
    sel_task_id = st.selectbox(
        "Select task to update",
        task_ids,
        format_func=lambda x: next(
            (t["task_text"][:70] for t in tasks_all if t["id"] == x), str(x)
        ),
        key="tb_task_sel",
    )
    sel_task = next((t for t in tasks_all if t["id"] == sel_task_id), None)

    if sel_task:
        ua, ub, uc = st.columns(3)

        new_status = ua.selectbox(
            "Status",
            _TASK_STATUSES,
            index=_TASK_STATUSES.index(sel_task["status"])
            if sel_task.get("status") in _TASK_STATUSES else 0,
            key="tb_new_status",
        )

        new_owner = ub.text_input(
            "Owner", value=sel_task.get("owner") or "Office Team", key="tb_owner"
        )

        _pri_list = ["urgent", "high", "medium", "low"]
        new_priority = uc.selectbox(
            "Priority",
            _pri_list,
            index=_pri_list.index(sel_task["priority"])
            if sel_task.get("priority") in _pri_list else 2,
            key="tb_priority",
        )

        if st.button("💾 Update Task", key="tb_update_btn", type="primary"):
            db.update_task_status(sel_task_id, new_status)
            db.update_task_owner(sel_task_id, new_owner)
            db.update_task_priority(sel_task_id, new_priority)
            st.success(
                f"Task #{sel_task_id} updated — "
                f"status: **{new_status}**, owner: **{new_owner}**, "
                f"priority: **{new_priority}**."
            )
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — REPORTS & EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def _page_reports():
    st.title("📤 Reports & Export")
    st.caption(
        "Workflow insights and data exports. "
        "Download processed data for Excel, Power BI, or your ticketing system."
    )

    metrics = db.get_dashboard_metrics()

    if metrics["total"] == 0:
        _no_data_prompt("No data to report yet.")
        return

    emails_df = db.get_processed_emails_dataframe()
    tasks_df = db.get_tasks_dataframe()
    log_df = db.get_review_log_dataframe()
    drafts_raw = db.get_all_drafts()
    drafts_df = pd.DataFrame(drafts_raw) if drafts_raw else pd.DataFrame()

    # ── Workflow Insights ─────────────────────────────────────────────────────
    st.subheader("Workflow Insights")

    total = metrics["total"]
    reviewed = total - metrics["pending_review"]
    pct_reviewed = (reviewed / total * 100) if total > 0 else 0.0

    total_tasks = metrics["tasks"]
    completed_tasks = len(db.get_completed_tasks())
    pct_tasks_done = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

    workload = metrics["urgent"] + metrics["high"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Emails Processed", total)
    c2.metric("🔴🟠 High/Urgent Workload", workload)
    c3.metric("Reviews Complete", f"{pct_reviewed:.0f}%")
    c4.metric("Tasks Complete", f"{pct_tasks_done:.0f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Drafts Approved", metrics["approved_only"])
    c6.metric("Drafts Edited+Saved", metrics["edited_drafts"])
    c7.metric("Drafts Rejected", metrics["rejected_drafts"])
    c8.metric("Open Tasks", total_tasks - completed_tasks)

    # Most common category and priority
    if not emails_df.empty and "category" in emails_df.columns:
        cats = emails_df["category"].dropna()
        pris = emails_df["priority"].dropna()
        if not cats.empty:
            top_cat = _CAT_LABELS.get(cats.mode()[0], cats.mode()[0])
            top_pri = pris.mode()[0] if not pris.empty else "—"
            st.info(
                f"**Most common category:** {top_cat} &nbsp;|&nbsp; "
                f"**Most common priority:** {top_pri.upper()}"
            )

    st.divider()

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.subheader("Downloads")

    col_e, col_t, col_l, col_d = st.columns(4)

    with col_e:
        st.markdown("**Emails**")
        if not emails_df.empty:
            csv_buf = io.StringIO()
            emails_df.to_csv(csv_buf, index=False)
            st.download_button(
                "📥 Emails CSV",
                csv_buf.getvalue(),
                "inboxpilot_emails.csv",
                "text/csv",
                use_container_width=True,
            )
            st.download_button(
                "📥 Emails JSON",
                emails_df.to_json(orient="records", indent=2),
                "inboxpilot_emails.json",
                "application/json",
                use_container_width=True,
            )
        else:
            st.caption("No email data yet.")

    with col_t:
        st.markdown("**Tasks**")
        if not tasks_df.empty:
            tasks_buf = io.StringIO()
            tasks_df.to_csv(tasks_buf, index=False)
            st.download_button(
                "📥 Tasks CSV",
                tasks_buf.getvalue(),
                "inboxpilot_tasks.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.caption("No task data yet.")

    with col_l:
        st.markdown("**Review Log**")
        if not log_df.empty:
            log_buf = io.StringIO()
            log_df.to_csv(log_buf, index=False)
            st.download_button(
                "📥 Review Log CSV",
                log_buf.getvalue(),
                "inboxpilot_review_log.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.caption("No review log entries yet.")

    with col_d:
        st.markdown("**Draft Replies**")
        if not drafts_df.empty:
            drafts_buf = io.StringIO()
            drafts_df.to_csv(drafts_buf, index=False)
            st.download_button(
                "📥 Drafts CSV",
                drafts_buf.getvalue(),
                "inboxpilot_drafts.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.caption("No draft data yet.")

    st.divider()

    # ── Category breakdown ─────────────────────────────────────────────────────
    if not emails_df.empty and "category" in emails_df.columns:
        has_cats = emails_df["category"].notna().any()
        if has_cats:
            st.subheader("Category Breakdown")
            cat_summary = (
                emails_df.dropna(subset=["category"])
                .groupby("category")
                .agg(
                    Count=("id", "count"),
                    Urgent=("priority", lambda x: (x == "urgent").sum()),
                    High=("priority", lambda x: (x == "high").sum()),
                    Medium=("priority", lambda x: (x == "medium").sum()),
                    Low=("priority", lambda x: (x == "low").sum()),
                )
                .reset_index()
                .sort_values("Count", ascending=False)
            )
            cat_summary["category"] = cat_summary["category"].map(
                lambda c: _CAT_LABELS.get(c, c)
            )
            cat_summary.columns = ["Category", "Count", "Urgent", "High", "Medium", "Low"]
            st.dataframe(cat_summary, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — ABOUT & SAFETY
# ══════════════════════════════════════════════════════════════════════════════

def _page_about():
    st.title("ℹ️ About & Safety")
    st.caption(
        "InboxPilot AI is a portfolio demo of AI-assisted workflow automation "
        "for professional service firms. All safety constraints are enforced in code."
    )

    st.markdown("""
### What InboxPilot AI Does

InboxPilot AI demonstrates a complete office workflow automation system:

1. **Classify** — 16 domain-specific categories using a rule-based regex classifier
2. **Prioritise** — urgent / high / medium / low scoring
3. **Detect deadlines** — extract date phrases from email text
4. **Summarise** — category-specific business summaries
5. **Extract tasks** — actionable items with owners and due dates
6. **Generate drafts** — professional reply templates with `[TODO]` placeholders
7. **Route for review** — human review queue (approve / edit / reject)
8. **Maintain audit trail** — every review action logged with timestamp and note
9. **Export** — CSV and JSON downloads for downstream integration

---

### What InboxPilot AI Does NOT Do

| Constraint | Detail |
|---|---|
| **No automatic email sending** | All drafts require explicit human approval — no send mechanism exists |
| **No final tax or legal advice** | Drafts use `[TODO]` placeholders — professional sign-off required |
| **No real client data** | Demo dataset uses entirely fictional clients and figures |
| **No live inbox connection** | Processes a local demo dataset — no Gmail, IMAP, or Exchange |
| **No credentials stored** | API key (optional) loaded from `.env` — never hardcoded |

---

### AI Safety Boundaries

When `OPENAI_API_KEY` is set, every AI response passes through two layers before storage:

**Validation layer (`src/ai_validation.py`)**
- Invalid categories → default to `general_inquiry`
- Invalid priorities → default to `medium`
- `requires_human_review` is always forced to `True`
- Confidence clamped to `[0.0, 1.0]`
- Missing fields filled with safe defaults

**Safety enforcement layer (`src/safety.py`)**
- "we guarantee" → "we aim to ensure"
- "this email has been sent" → "this draft is pending review"
- "as your licensed tax advisor" → "as your professional service provider"
- API key patterns → `[REDACTED]`
- `DRAFT FOR REVIEW` notice appended if missing

---

### Human Review Checklist

Before approving any draft:

- [ ] Verify the category and priority are correct
- [ ] Read the full original email to confirm context
- [ ] Fill in all `[TODO: ...]` placeholders
- [ ] Confirm any financial figures or dates are accurate
- [ ] For tax or legal matters, obtain appropriate professional sign-off
- [ ] Check tone is appropriate for the specific client relationship
- [ ] Verify the AI confidence level and safety note (if shown)

---

### Processing Modes

| Mode | When | Confidence |
|------|------|------------|
| **Rule-based** (default) | No API key | 0.0 (deterministic) |
| **OpenAI-enhanced** (optional) | `OPENAI_API_KEY` set | 0.0–1.0 (model-reported) |

Rule-based mode is not a degraded state — it is the stable, fully tested baseline.
If the OpenAI API call fails for any reason, the processor falls back to rule-based silently.

---

### Tech Stack

| Component | Technology |
|---|---|
| UI | Streamlit ≥1.35 |
| Database | SQLite (local, no server) |
| Classification | Rule-based regex + optional OpenAI GPT-4o-mini |
| AI validation | `src/ai_validation.py` |
| Safety enforcement | `src/safety.py` |
| Draft generation | Template engine + optional OpenAI |
| Testing | pytest — 213 tests, all offline |
| Export | pandas + Streamlit download buttons |
""")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════

if page == "📊 Dashboard":
    _page_dashboard()
elif page == "📥 Inbox Processing":
    _page_inbox()
elif page == "📋 Review Queue":
    _page_review_queue()
elif page == "✅ Task Board":
    _page_task_board()
elif page == "📤 Reports & Export":
    _page_reports()
elif page == "ℹ️ About & Safety":
    _page_about()
