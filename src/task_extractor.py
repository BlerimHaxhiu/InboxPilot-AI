"""
Extracts actionable tasks from email text.
Tries OpenAI if the API key is set, falls back to rule-based extraction.
"""
from __future__ import annotations
import os
import re
from datetime import datetime, timedelta

_DUE_DATE_PATTERNS = [
    # "by Friday", "by June 14", "by EOD", "by Thursday noon"
    re.compile(
        r"\bby\s+((?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|eod|cob|noon|"
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)(?:\s+(?:eod|cob|noon|am|pm))?)\b",
        re.I,
    ),
    # "due on June 15", "due by Friday"
    re.compile(r"\bdue\s+(?:on|by)\s+(\S+(?:\s+\S+)?)", re.I),
    # "tomorrow", "this week", "next week"
    re.compile(r"\b(tomorrow|this\s+week|next\s+week|today)\b", re.I),
    # "June 13, 2pm"
    re.compile(
        r"\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2}(?:,? \d{4})?)\b",
        re.I,
    ),
]

_ACTION_VERBS = re.compile(
    r"(?:please\s+)?(?:could\s+you\s+)?"
    r"(review|submit|send|provide|update|fix|confirm|reply|respond|complete|prepare|schedule|"
    r"approve|investigate|check|look into|process|finalize)\b",
    re.I,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _extract_due_date(text: str) -> str | None:
    for pat in _DUE_DATE_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


def _extract_rule_based(subject: str, body: str) -> list[dict]:
    tasks = []
    sentences = _SENTENCE_SPLIT.split(body)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        match = _ACTION_VERBS.search(sent)
        if match:
            # Trim the sentence to a reasonable task title (max 120 chars)
            title = sent[:120].rstrip(".!?,")
            due = _extract_due_date(sent) or _extract_due_date(body)
            tasks.append(
                {
                    "title": title,
                    "description": sent if len(sent) > len(title) else None,
                    "due_date": due,
                    "priority": 2,
                }
            )
    # Fallback: create a generic task from the subject if nothing found
    if not tasks:
        due = _extract_due_date(body)
        tasks.append(
            {
                "title": f"Action: {subject[:100]}",
                "description": None,
                "due_date": due,
                "priority": 3,
            }
        )
    # Deduplicate by title similarity
    seen: set[str] = set()
    unique = []
    for t in tasks:
        key = t["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique[:5]  # cap at 5 tasks per email


def _extract_openai(subject: str, body: str) -> list[dict] | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        import json

        client = OpenAI(api_key=api_key)
        prompt = (
            "Extract all actionable tasks from the following email. "
            "Return JSON array of objects with keys: title (string), "
            "due_date (string or null), priority (1-5, 1=highest).\n\n"
            f"Subject: {subject}\n\n{body}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        content = resp.choices[0].message.content
        data = json.loads(content)
        tasks = data.get("tasks", data) if isinstance(data, dict) else data
        if isinstance(tasks, list):
            out = []
            for t in tasks:
                out.append(
                    {
                        "title": str(t.get("title", ""))[:120],
                        "description": None,
                        "due_date": t.get("due_date"),
                        "priority": int(t.get("priority", 3)),
                    }
                )
            return out
    except Exception:
        pass
    return None


def extract_tasks(subject: str, body: str) -> list[dict]:
    """Return a list of task dicts with keys: title, description, due_date, priority."""
    ai_tasks = _extract_openai(subject, body)
    if ai_tasks is not None:
        return ai_tasks
    return _extract_rule_based(subject, body)
