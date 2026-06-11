"""
Rule-based draft reply generator for a tax/accounting professional services firm.
Uses OpenAI when OPENAI_API_KEY is set; otherwise falls back to professional templates.
ALL drafts must be reviewed and approved by a qualified team member before use.
"""
from __future__ import annotations
import os
import re
from src.models import DraftReplyResult

_REVIEW_WARNING = (
    "\n\n---\n"
    "DRAFT FOR REVIEW: This reply was generated automatically. "
    "Please review, edit as needed, and obtain sign-off from a qualified team member "
    "before sending. Do not send this message in its current form without review."
)

_TEMPLATES: dict[str, str] = {
    "invoice": (
        "Dear {name},\n\n"
        "Thank you for sending {ref}. I confirm receipt and will forward it to our "
        "accounts team for processing in line with the agreed payment terms.\n\n"
        "You can expect payment within [TODO: confirm payment timeframe, e.g. 30 days "
        "of the invoice date]. Should you need a purchase order number or have any queries "
        "regarding the invoice, please do not hesitate to contact us.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "tax_question": (
        "Dear {name},\n\n"
        "Thank you for your tax query. I have noted the details you provided and will "
        "review your situation carefully.\n\n"
        "[TODO: Insert factual response here. Ensure all technical details are verified "
        "before sending. Do not provide definitive tax advice without appropriate senior "
        "sign-off and consideration of the client's full circumstances.]\n\n"
        "Please note that this response is for general guidance purposes only and does "
        "not constitute formal tax advice. A formal written opinion will follow where "
        "required, and any advice given is based solely on the information you have "
        "provided to us.\n\n"
        "If you have any further questions or would like to discuss your position in more "
        "detail, please do not hesitate to get in touch.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "missing_document": (
        "Dear {name},\n\n"
        "Thank you for your message. Further to our records, we are still awaiting the "
        "following documents to complete your filing:\n\n"
        "[TODO: List the specific outstanding documents and the deadline for receipt.]\n\n"
        "Please note that failure to provide these documents by [TODO: deadline] may "
        "result in a late filing and the associated HMRC penalties. If you are "
        "experiencing any difficulties obtaining the documents, please contact us as "
        "soon as possible so we can discuss your options.\n\n"
        "You can send the documents securely via [TODO: portal/email/post].\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "appointment_request": (
        "Dear {name},\n\n"
        "Thank you for getting in touch to arrange a meeting. I am pleased to confirm "
        "that we can accommodate your request.\n\n"
        "[TODO: Confirm the agreed date and time, or propose two or three alternative "
        "slots if the requested times are not available.]\n\n"
        "The meeting will be held [TODO: at our office at [address] / via video call — "
        "link to follow]. Please bring along [TODO: relevant documents, accounts, or "
        "records]. A calendar invitation will follow this email.\n\n"
        "We look forward to speaking with you.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "payroll": (
        "Dear {name},\n\n"
        "Thank you for your payroll query. I have reviewed the details you provided and "
        "will investigate further with our payroll team.\n\n"
        "[TODO: Provide specific guidance on the tax code, NI contribution, or payroll "
        "matter raised. Confirm all details with a payroll specialist before sending "
        "this response.]\n\n"
        "Please note that any payroll adjustments will need to be processed before the "
        "next payroll run on [TODO: date]. We will confirm once the correction has been "
        "actioned and update your payslip accordingly.\n\n"
        "If you have any further questions, please do not hesitate to contact us.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "vat": (
        "Dear {name},\n\n"
        "Thank you for providing the figures for your VAT return. I am reviewing the "
        "details and will prepare a draft return for your approval before submission.\n\n"
        "[TODO: Summarise the VAT position, note the net VAT payable/reclaimable, and "
        "highlight any areas requiring special treatment — e.g. EU exports, partial "
        "exemption, or input VAT recovery queries. Do not submit without client "
        "sign-off and review by a qualified VAT adviser where needed.]\n\n"
        "The filing deadline for this VAT period is [TODO: date]. I will send the "
        "draft return for your review and approval by [TODO: earlier date]. Please do "
        "not hesitate to contact me if you have any questions in the meantime.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "bank_statement": (
        "Dear {name},\n\n"
        "Thank you for sending the bank statements. I confirm receipt of all documents "
        "and have passed them to our bookkeeping team for reconciliation.\n\n"
        "[TODO: Note the accounts received and the period covered. If any statements "
        "are missing or if there are highlighted transactions requiring clarification, "
        "list them here.]\n\n"
        "We will be in touch if we identify any items that require further explanation "
        "or supporting documentation. You can expect the reconciliation to be completed "
        "by [TODO: estimated date].\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "client_complaint": (
        "Dear {name},\n\n"
        "Thank you for bringing this to our attention. I am sorry to hear that you have "
        "experienced issues with our service, and I want to assure you that we take your "
        "concerns very seriously.\n\n"
        "[TODO: After completing a thorough internal review, provide a specific and "
        "factual response to each point raised in the complaint. This response must be "
        "reviewed and approved by a senior partner before being sent.]\n\n"
        "I will conduct a full review of the matters you have raised and respond in "
        "writing with our findings within [TODO: timeframe, typically 5 business days]. "
        "Your complaint reference number is [TODO: assign reference]. If you would like "
        "to discuss this matter further before then, please contact me directly on "
        "[TODO: phone number].\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]\n"
        "[Note: This is a complaint response draft and must be approved by a senior "
        "partner before sending.]"
    ),
    "refund_question": (
        "Dear {name},\n\n"
        "Thank you for following up regarding your refund claim. I fully understand the "
        "importance of this for your cash flow, and I apologise for the delay you have "
        "experienced.\n\n"
        "[TODO: Check the current status of the claim via the HMRC portal or tax account. "
        "Insert the current status and expected payment date here. If the claim is "
        "significantly overdue, note the escalation steps being taken.]\n\n"
        "I will continue to monitor the position and will update you as soon as we have "
        "further information from HMRC. If there is no update within [TODO: timeframe], "
        "we will escalate the matter formally.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "urgent_client_issue": (
        "Dear {name},\n\n"
        "Thank you for bringing this urgent matter to our attention. I confirm we have "
        "received your message and are treating it as an immediate priority.\n\n"
        "[TODO: Describe the specific actions being taken and provide a clear timeline "
        "for resolution. Obtain approval from the responsible partner before sending.]\n\n"
        "A senior member of our team will be in contact with you [TODO: within X hours / "
        "by [time] today]. If you need to speak with someone urgently in the meantime, "
        "please call [TODO: direct phone number].\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "audit_notice": (
        "Dear {name},\n\n"
        "Thank you for forwarding the HMRC audit notice to us. I confirm receipt and "
        "can assure you that we are reviewing the details as a matter of urgency.\n\n"
        "[TODO: Summarise the key requirements of the notice and the response deadline. "
        "This draft MUST be reviewed and approved by a senior partner before sending. "
        "Do not respond to HMRC directly without our guidance.]\n\n"
        "Please do not respond directly to HMRC without consulting us first. We will "
        "manage the correspondence on your behalf and ensure the response is accurate "
        "and submitted within the required timeframe.\n\n"
        "I will be in touch within [TODO: 1-2 business days] to arrange a call and "
        "discuss the next steps in detail.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]\n"
        "[IMPORTANT: Must be reviewed by senior partner before sending.]"
    ),
    "new_client_onboarding": (
        "Dear {name},\n\n"
        "Thank you for getting in touch and for your kind interest in our services. "
        "We would be delighted to welcome you as a new client.\n\n"
        "To get started, we will need to complete the following:\n\n"
        "1. Client onboarding form (enclosed/attached)\n"
        "2. Proof of identity and address (AML requirements)\n"
        "3. Engagement letter — setting out the scope of services and our fees\n"
        "4. [TODO: Any specific documents relevant to the client's business type]\n\n"
        "I would suggest we arrange a brief introductory call to discuss your "
        "requirements in more detail and agree the scope of our services. Please let "
        "me know your availability and I will confirm a suitable time.\n\n"
        "[TODO: Confirm service scope and fee estimate before sending. Review with "
        "partner if group engagement or significant complexity.]\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "payment_confirmation": (
        "Dear {name},\n\n"
        "Thank you for your email and for confirming payment. I am pleased to confirm "
        "that we have received {ref} and will update our records accordingly.\n\n"
        "[TODO: Confirm the payment has been received in the accounts system and the "
        "invoice has been marked as settled.]\n\n"
        "Please find attached a formal receipt for your records. If you require an "
        "updated statement of account, please let us know and we will send this to you "
        "at your earliest convenience.\n\n"
        "Thank you again for your prompt payment.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "contract_service_question": (
        "Dear {name},\n\n"
        "Thank you for your enquiry regarding our services and fee structure. I am happy "
        "to provide you with further information.\n\n"
        "[TODO: Outline the specific services relevant to the client's query, the "
        "applicable fee structure, and any key terms of engagement. Have this reviewed "
        "before sending, and do not quote specific fees without partner approval.]\n\n"
        "Our standard engagement letter sets out the full scope of services, our "
        "responsibilities and yours, fees, and the terms of our engagement. I will "
        "send this to you shortly for your review.\n\n"
        "If you would find it helpful, I would be happy to arrange a brief call to "
        "walk you through our services and answer any questions you may have. Please "
        "let me know if that would be useful.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "general_inquiry": (
        "Dear {name},\n\n"
        "Thank you for your email. I have received your enquiry and will look into this "
        "for you.\n\n"
        "[TODO: Provide a helpful, professional response to the specific question raised. "
        "Where specialist knowledge is required, ensure the response is reviewed by the "
        "appropriate team member before sending.]\n\n"
        "If you have any further questions, please feel free to contact me directly.\n\n"
        "Kind regards,\n[Your Name]\n[Firm Name]"
    ),
    "spam": (
        "No draft generated — this email has been classified as promotional or spam. "
        "No response is required."
    ),
}


def _sender_name(sender: str) -> str:
    local = sender.split("@")[0]
    parts = re.split(r"[._\-]", local)
    return parts[0].capitalize() if parts else "there"


def _extract_invoice_ref(subject: str, body: str) -> str:
    m = re.search(r"\b((?:INV|SU|ACC|REF|PO)[#\-\s]?[\w\-]+|\d{4,})\b", subject + " " + body, re.I)
    return m.group(0) if m else "your invoice"


def _rule_based_draft(category: str, subject: str, body: str, sender: str) -> str:
    template = _TEMPLATES.get(category, _TEMPLATES["general_inquiry"])
    name = _sender_name(sender)
    ref = _extract_invoice_ref(subject, body)
    return template.format(name=name, ref=ref) + (
        _REVIEW_WARNING if category not in ("spam",) else ""
    )


def _openai_draft(category: str, subject: str, body: str, sender: str) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        system = (
            "You are a professional email assistant at a tax and accounting firm. "
            "Write a courteous, professional draft reply to the following client email. "
            "Use [TODO: ...] placeholders for specific information the sender must supply. "
            "Never provide definitive tax or legal advice as a conclusion. "
            "Include a note at the end that this draft requires review by a qualified team "
            "member before sending. This is a draft only — never imply it has been sent."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Category: {category}\n"
                        f"From: {sender}\n"
                        f"Subject: {subject}\n\n"
                        f"{body}"
                    ),
                },
            ],
            max_tokens=700,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


def generate_draft(
    category: str, subject: str, body: str, sender: str
) -> DraftReplyResult:
    """
    Generate a professional draft reply.
    Returns DraftReplyResult. Draft MUST be reviewed before any use.
    """
    ai_text = _openai_draft(category, subject, body, sender)
    if ai_text:
        return DraftReplyResult(draft_text=ai_text, category=category, ai_generated=True)
    rule_text = _rule_based_draft(category, subject, body, sender)
    return DraftReplyResult(draft_text=rule_text, category=category, ai_generated=False)
