from src.task_extractor import extract_tasks


def test_extracts_action_verb():
    tasks = extract_tasks(
        "Please review the document",
        "Could you please review the attached document by Friday?",
    )
    assert len(tasks) >= 1
    assert any("review" in t["title"].lower() for t in tasks)


def test_extracts_due_date():
    tasks = extract_tasks(
        "Submit report",
        "Please submit the quarterly report by Friday EOD.",
    )
    assert len(tasks) >= 1
    due = tasks[0].get("due_date") or ""
    assert "friday" in due.lower() or "eod" in due.lower()


def test_fallback_creates_task():
    tasks = extract_tasks("Info", "This is a purely informational message.")
    assert len(tasks) >= 1
    assert "Info" in tasks[0]["title"]


def test_caps_at_five_tasks():
    body = (
        "Please review the code. "
        "Please send the report. "
        "Please confirm the meeting. "
        "Please fix the bug. "
        "Please update the document. "
        "Please schedule the call. "
    )
    tasks = extract_tasks("Multi-action email", body)
    assert len(tasks) <= 5


def test_priority_is_valid():
    tasks = extract_tasks("Action required", "Please send the data by tomorrow.")
    for t in tasks:
        assert 1 <= t["priority"] <= 5
