"""
Rule-based email classifier for a tax/accounting professional services firm.
All functions are deterministic and require no API key.
16 categories, 4 priority levels, deadline detection and recommended actions.
"""
from __future__ import annotations
import re

CATEGORIES = [
    "invoice",
    "tax_question",
    "missing_document",
    "appointment_request",
    "payroll",
    "vat",
    "bank_statement",
    "client_complaint",
    "refund_question",
    "urgent_client_issue",
    "audit_notice",
    "new_client_onboarding",
    "payment_confirmation",
    "contract_service_question",
    "general_inquiry",
    "spam",
]

PRIORITIES = ["low", "medium", "high", "urgent"]

# ── Category keyword patterns (order of definition matters for classifier logic) ─

_SPAM = re.compile(
    r"\b(!!!|exclusive offer|limited time|today only|click here|unsubscribe|"
    r"promotional|don.t miss|save \d+%|upgrade now|special offer|incredible deal|"
    r"do not delay|offer expires|this weekend only)\b",
    re.I,
)

_COMPLAINT = re.compile(
    r"\b(formal(ly)? (complain|complaint|raise)|formal complaint|dissatisfied|"
    r"unacceptable|overcharged|incorrectly? (categorised|classified|recorded)|"
    r"errors? in (our |the )?(account|return|report)|"
    r"unjustified fee|escalate (to|this)|professional standards|"
    r"institute of chartered|chartered accountants)\b",
    re.I,
)

_AUDIT = re.compile(
    r"\b(audit notice|hmrc (enquiry|inquiry|investigation|audit|compliance)|"
    r"notice of (enquiry|inquiry|audit|investigation|compliance)|"
    r"formal (enquiry|inquiry)|compliance (check|review)|"
    r"under (investigation|enquiry|inquiry)|"
    r"taxes management act|section 9a|"
    r"tax (enquiry|investigation)|regulatory (review|audit))\b",
    re.I,
)

_ONBOARDING = re.compile(
    r"\b(new client enqui(ry|ries)|prospective client|"
    r"interested in (your|engaging)|would like to (engage|start using|use) your|"
    r"considering your (firm|services?)|new business (enquiry|query)|"
    r"first time (using|contacting|working with)|"
    r"switching (accounting|our) firm|looking to engage|"
    r"recommended (to|your) (firm|services?))\b",
    re.I,
)

_PAYMENT_CONF = re.compile(
    r"\b(payment confirmation|payment (has been |has now )?(?:made|sent|processed|"
    r"completed|settled|cleared)|confirm(ing)? (that )?payment|"
    r"funds (transferred|sent|cleared)|bank transfer (completed|sent|processed|confirmation)|"
    r"please find attached.*remittance|remittance advice|"
    r"invoice.*settled|settled.*invoice)\b",
    re.I,
)

_STRONG_URGENT = re.compile(
    r"\b(urgent|asap|immediately|final notice|emergency|critical|"
    r"penalty|penalties|overdue|late (filing|payment)|do not ignore)\b",
    re.I,
)

_VAT = re.compile(
    r"\b(vat|value.added tax|vat return|input vat|output vat|zero.rated|"
    r"vat registration|vat number|making tax digital|mtd for vat|"
    r"vat period|vat quarter|vat submission)\b",
    re.I,
)

_PAYROLL = re.compile(
    r"\b(payroll|tax code|p45|p60|p11d|paye|employee.*tax|"
    r"national insurance|ni contribution|starter (checklist|declaration)|"
    r"new (employee|starter)|emergency (tax code|basis)|"
    r"gross salary|payslip|pay run|rtl|real time information)\b",
    re.I,
)

_BANK_STMT = re.compile(
    r"\b(bank statements?|statements? (attached|enclosed|for quarter|received)|"
    r"account.*(ending|xxxx)|bank (account|reconciliation)|"
    r"monthly statement|sort code|account ending)\b",
    re.I,
)

_REFUND = re.compile(
    r"\b(refund|repayment|r&d (claim|credit|refund)|hmrc (refund|payment|repayment)|"
    r"tax (refund|repayment|credit)|when will (we|i) receive|"
    r"outstanding (refund|claim|payment)|claim.*outstanding)\b",
    re.I,
)

_INVOICE = re.compile(
    r"\b(invoice #?|inv-\d+|su-\d+|amount due|payment terms|"
    r"remittance|please (find|see) attached.*(invoice|inv)|"
    r"invoice for|billing|pro.forma|credit note|"
    r"overdue invoice|unpaid invoice|final reminder.*invoice)\b",
    re.I,
)

_CONTRACT = re.compile(
    r"\b(service agreement|engagement (letter|terms)|contract|"
    r"fee (structure|schedule|information)|scope of (work|service)|"
    r"retainer|terms of (service|business|engagement)|pricing structure|"
    r"what (services?|is included|do you (offer|cover))|"
    r"how much (do|would) you|your (pricing|fees|charges))\b",
    re.I,
)

_MISSING_DOC = re.compile(
    r"\b(missing (document|invoice|receipt|form)|outstanding (document|information)|"
    r"still waiting for|have not received|not yet received|"
    r"please (send|provide|submit|upload|forward).*(document|statement|invoice|form|receipt)|"
    r"document(s?) (required|needed)|checklist|clarif(y|ication) (on|about|regarding) "
    r"(the )?document)\b",
    re.I,
)

_APPOINTMENT = re.compile(
    r"\b(appointment|schedule (a|an)|meeting (on|at)|reschedule|"
    r"available (on|at|for)|book (a|an) (meeting|call|appointment)|"
    r"calendar|propose (a|some) (time|slot|date)|could we (meet|arrange)|"
    r"initial (consultation|meeting|call)|video call|zoom|teams meeting)\b",
    re.I,
)

_TAX_Q = re.compile(
    r"\b(capital gains|cgt|corporation tax|income tax|self.assessment|"
    r"sole trader|allowance|deduction|tax.free|tax return|tax liability|"
    r"tax advice|tax (relief|treatment|implication)|"
    r"(how|what) (do|should|can|would) (i|we) (claim|pay|declare|file|report)|"
    r"am i (liable|eligible|entitled)|private residence relief|"
    r"annual investment allowance|entrepreneurs.? relief)\b",
    re.I,
)

# ── Deadline detection patterns (ordered: most specific → least specific) ─────

_DEADLINE_PATTERNS = [
    # ISO date: 2026-03-15
    re.compile(r'\b(\d{4}-\d{2}-\d{2})\b'),
    # "deadline is 2026-03-15", "due date: 01/03/2026"
    re.compile(
        r'\b(?:deadline|due\s*date)\s*(?:is|:)\s*'
        r'(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        re.I,
    ),
    # "by/before/until [date phrase]" or "due [date]"
    re.compile(
        r'\b(?:by|before|until|due)\s+'
        r'((?:\d{1,2}(?:st|nd|rd|th)?\s+)?'
        r'(?:january|february|march|april|may|june|july|august|'
        r'september|october|november|december|'
        r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*'
        r'(?:\s+\d{1,2}(?:st|nd|rd|th)?)?(?:[,\s]+\d{4})?'
        r'|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?'
        r'|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\w*'
        r'|next\s+\w+)',
        re.I,
    ),
    # "by March 15", "before April 30, 2026"
    re.compile(
        r'\b(?:by|before|until)\s+'
        r'((?:january|february|march|april|may|june|july|august|'
        r'september|october|november|december|'
        r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*'
        r'\s+\d{1,2}(?:st|nd|rd|th)?(?:[,\s]+\d{4})?)',
        re.I,
    ),
    # "next Monday/Tuesday/.../week/month"
    re.compile(
        r'\b(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month))\b',
        re.I,
    ),
    # "today", "tomorrow"
    re.compile(r'\b(today|tomorrow)\b', re.I),
    # "on/for 12 June", "on March 15 at 2pm"
    re.compile(
        r'\b(?:on|for)\s+'
        r'((?:\d{1,2}(?:st|nd|rd|th)?\s+)?'
        r'(?:january|february|march|april|may|june|july|august|'
        r'september|october|november|december|'
        r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*'
        r'(?:\s+\d{1,2}(?:st|nd|rd|th)?)?(?:[,\s]+\d{4})?)',
        re.I,
    ),
    # "15 March 2026", "15 March", "15th June"
    re.compile(
        r'\b(\d{1,2}(?:st|nd|rd|th)?\s+'
        r'(?:january|february|march|april|may|june|july|august|'
        r'september|october|november|december)\w*'
        r'(?:[,\s]+\d{4})?)\b',
        re.I,
    ),
    # "March 15, 2026", "June 30"
    re.compile(
        r'\b((?:january|february|march|april|may|june|july|august|'
        r'september|october|november|december)\w*'
        r'\s+\d{1,2}(?:st|nd|rd|th)?(?:[,\s]+\d{4})?)\b',
        re.I,
    ),
    # Abbreviated month: "Jun 20", "20 Jun"
    re.compile(
        r'\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b)',
        re.I,
    ),
    re.compile(
        r'\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}\b)',
        re.I,
    ),
    # Standalone weekday (weakest — last resort)
    re.compile(r'\b(monday|tuesday|wednesday|thursday|friday)\b', re.I),
]


def classify_email(subject: str, body: str) -> str:
    """Return the most appropriate category string for the given email."""
    text = f"{subject} {body}"

    # 1. Spam — exit early
    if _SPAM.search(text):
        return "spam"

    # 2. Formal client complaint
    if _COMPLAINT.search(text):
        return "client_complaint"

    # 3. Official audit / compliance notice — high stakes, check early
    if _AUDIT.search(text):
        return "audit_notice"

    # 4. New client onboarding enquiry
    if _ONBOARDING.search(text):
        return "new_client_onboarding"

    # 5. Payment confirmation (before invoice to avoid confusion)
    if _PAYMENT_CONF.search(text):
        return "payment_confirmation"

    # 6. Strong urgency in subject (not invoice/refund) → urgent issue
    if (
        _STRONG_URGENT.search(subject)
        and not _INVOICE.search(subject)
        and not _REFUND.search(text)
    ):
        return "urgent_client_issue"

    # 7. Domain-specific categories (in priority order)
    if _VAT.search(text):
        return "vat"
    if _PAYROLL.search(text):
        return "payroll"
    if _BANK_STMT.search(text):
        return "bank_statement"
    if _REFUND.search(text):
        return "refund_question"

    # 8. Service / contract enquiries — must come before invoice (_INVOICE matches "billing")
    if _CONTRACT.search(text):
        return "contract_service_question"

    if _INVOICE.search(text):
        return "invoice"

    # 9. Missing documents (also catches document clarification)
    if _MISSING_DOC.search(text):
        return "missing_document"

    # 10. Appointment / meeting
    if _APPOINTMENT.search(text):
        return "appointment_request"

    # 11. Tax questions
    if _TAX_Q.search(text):
        return "tax_question"

    # 12. General urgency catch-all
    if _STRONG_URGENT.search(text):
        return "urgent_client_issue"

    return "general_inquiry"


def score_priority(subject: str, body: str) -> str:
    """Return 'urgent', 'high', 'medium', or 'low'."""
    text = f"{subject} {body}"

    # Count strong urgency signals
    urgent_hits = len(re.findall(
        r"\b(urgent|asap|immediately|final notice|deadline|penalty|penalties|"
        r"overdue|critical|do not ignore|late (filing|payment)|audit notice|"
        r"under investigation|hmrc enquiry)\b",
        text, re.I,
    ))
    # All-caps URGENT in subject is an instant escalation
    if urgent_hits >= 2 or re.search(r"\bURGENT\b", subject):
        return "urgent"

    # High priority signals
    if re.search(
        r"\b(formal(ly)? complain|complaint|overcharged|errors? in (our|the)|"
        r"escalate|institute of chartered|audit notice|hmrc (enquiry|compliance)|"
        r"compliance check|"
        r"due (on|by|date)|missing (document|invoice)|outstanding document|"
        r"late (filing|payment)|penalty|final notice)\b",
        text, re.I,
    ):
        return "high"

    # Medium priority signals
    if re.search(
        r"\b(invoice|vat|payroll|tax return|refund|capital gains|cgt|"
        r"appointment|schedule|please (send|review|confirm|provide)|"
        r"bank statement|new client|payment confirmation|service agreement)\b",
        text, re.I,
    ):
        return "medium"

    return "low"


def detect_deadline(subject: str, body: str) -> str | None:
    """
    Extract the first deadline or date phrase from the email.
    Returns the phrase as a string or None if no date is found.
    Patterns are ordered from most specific to least specific.
    """
    for text in (subject, body):
        for pat in _DEADLINE_PATTERNS:
            m = pat.search(text)
            if m:
                # Use group(1) when available (captured content), else group(0)
                result = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else m.group(0).strip()
                if len(result) >= 4:  # skip very short spurious matches
                    return result
    return None


def recommend_action(category: str, priority: str, body: str = "") -> str:
    """Return a concise recommended action for the account manager."""
    _ACTIONS: dict[str, str] = {
        "invoice": (
            "Log the invoice, verify amounts and supplier details, then forward to "
            "accounts payable for processing within the agreed payment terms."
        ),
        "tax_question": (
            "Review the client query carefully and prepare a factual, measured response. "
            "Do not provide definitive tax advice without senior partner sign-off."
        ),
        "missing_document": (
            "Contact the client immediately by phone or email to request the outstanding "
            "documents. Note the filing deadline and set a follow-up reminder."
        ),
        "appointment_request": (
            "Check team calendars and reply to the client with two or three proposed time "
            "slots. Send a calendar invitation once a time is confirmed."
        ),
        "payroll": (
            "Review the payroll query and consult with the payroll specialist before "
            "responding. Ensure any correction is processed before the next pay run."
        ),
        "vat": (
            "Review the VAT figures and check for any special treatment required "
            "(e.g. EU exports, partial exemption). Prepare draft return for client "
            "sign-off before submission deadline."
        ),
        "bank_statement": (
            "Acknowledge receipt, file the statements securely, and assign to the "
            "bookkeeping team for reconciliation. Flag any unusual transactions."
        ),
        "client_complaint": (
            "Escalate immediately to senior management. Acknowledge receipt to the client "
            "within 24 hours. Log in the complaints register and begin a full review."
        ),
        "refund_question": (
            "Check the claim status via the HMRC portal or with the relevant authority. "
            "Provide the client with a clear timeline and escalate if significantly overdue."
        ),
        "urgent_client_issue": (
            "Treat as highest priority. Escalate to the responsible partner immediately. "
            "Acknowledge receipt to the client within one hour."
        ),
        "audit_notice": (
            "Do not respond to the audit notice without senior partner review. "
            "Arrange an urgent client meeting and begin preparing all relevant records. "
            "Respond to HMRC within the specified deadline."
        ),
        "new_client_onboarding": (
            "Send the client onboarding pack and engagement letter. Complete AML identity "
            "verification. Schedule an initial consultation call to agree scope and fees."
        ),
        "payment_confirmation": (
            "Confirm receipt of funds in the accounts system and mark the invoice as paid. "
            "Issue a formal receipt or updated statement of account if requested."
        ),
        "contract_service_question": (
            "Prepare a clear explanation of the relevant services and fee structure. "
            "Have the response reviewed before sending. Offer a call to discuss further."
        ),
        "general_inquiry": (
            "Acknowledge receipt and provide a helpful, professional response. "
            "Redirect to the appropriate specialist if the query falls outside general scope."
        ),
        "spam": "No action required. Mark as spam and archive.",
    }

    base = _ACTIONS.get(category, "Review and respond to the client email.")
    if priority == "urgent":
        return f"URGENT — {base}"
    return base
