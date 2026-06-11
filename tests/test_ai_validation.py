import pytest
from src.ai_validation import (
    normalize_category,
    normalize_priority,
    ensure_required_fields,
    validate_ai_result,
    VALID_CATEGORIES,
    VALID_PRIORITIES,
)


# ── normalize_category ────────────────────────────────────────────────────────

def test_valid_category_passes_through():
    assert normalize_category("invoice") == "invoice"
    assert normalize_category("audit_notice") == "audit_notice"
    assert normalize_category("spam") == "spam"


def test_invalid_category_becomes_general_inquiry():
    assert normalize_category("nonsense_category") == "general_inquiry"
    assert normalize_category("unknown") == "general_inquiry"
    assert normalize_category("") == "general_inquiry"


def test_category_alias_resolved():
    assert normalize_category("tax question") == "tax_question"
    assert normalize_category("client complaint") == "client_complaint"
    assert normalize_category("spam/irrelevant") == "spam"
    assert normalize_category("general inquiry") == "general_inquiry"
    assert normalize_category("new client onboarding") == "new_client_onboarding"
    assert normalize_category("contract/service question") == "contract_service_question"


def test_category_case_insensitive():
    assert normalize_category("INVOICE") == "invoice"
    assert normalize_category("Tax_Question") == "tax_question"


def test_non_string_category_becomes_general_inquiry():
    assert normalize_category(None) == "general_inquiry"
    assert normalize_category(42) == "general_inquiry"
    assert normalize_category([]) == "general_inquiry"


# ── normalize_priority ────────────────────────────────────────────────────────

def test_valid_priority_passes_through():
    for p in VALID_PRIORITIES:
        assert normalize_priority(p) == p


def test_invalid_priority_becomes_medium():
    assert normalize_priority("very_high") == "medium"
    assert normalize_priority("unknown") == "medium"
    assert normalize_priority("") == "medium"


def test_priority_alias_critical_becomes_urgent():
    assert normalize_priority("critical") == "urgent"
    assert normalize_priority("emergency") == "urgent"
    assert normalize_priority("immediate") == "urgent"


def test_priority_alias_important_becomes_high():
    assert normalize_priority("important") == "high"
    assert normalize_priority("elevated") == "high"


def test_priority_alias_normal_becomes_medium():
    assert normalize_priority("normal") == "medium"
    assert normalize_priority("standard") == "medium"


def test_priority_alias_informational_becomes_low():
    assert normalize_priority("informational") == "low"
    assert normalize_priority("fyi") == "low"


def test_non_string_priority_becomes_medium():
    assert normalize_priority(None) == "medium"
    assert normalize_priority(99) == "medium"


# ── ensure_required_fields ────────────────────────────────────────────────────

def test_ensure_fills_missing_category():
    result = ensure_required_fields({})
    assert result["category"] == "general_inquiry"


def test_ensure_fills_missing_priority():
    result = ensure_required_fields({})
    assert result["priority"] == "medium"


def test_ensure_fills_missing_summary():
    result = ensure_required_fields({"category": "invoice", "priority": "medium"})
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


def test_ensure_fills_missing_tasks_as_empty_list():
    result = ensure_required_fields({})
    assert result["tasks"] == []


def test_ensure_requires_human_review_always_true():
    result = ensure_required_fields({"requires_human_review": False})
    assert result["requires_human_review"] is True


def test_ensure_requires_human_review_when_missing():
    result = ensure_required_fields({})
    assert result["requires_human_review"] is True


def test_ensure_confidence_clamped_above_1():
    result = ensure_required_fields({"confidence": 5.0})
    assert result["confidence"] == 1.0


def test_ensure_confidence_clamped_below_0():
    result = ensure_required_fields({"confidence": -0.5})
    assert result["confidence"] == 0.0


def test_ensure_confidence_valid_value_preserved():
    result = ensure_required_fields({"confidence": 0.75})
    assert abs(result["confidence"] - 0.75) < 1e-9


def test_ensure_invalid_confidence_defaults_to_zero():
    result = ensure_required_fields({"confidence": "high"})
    assert result["confidence"] == 0.0


def test_ensure_null_deadline_normalised():
    result = ensure_required_fields({"detected_deadline": "null"})
    assert result["detected_deadline"] is None
    result2 = ensure_required_fields({"detected_deadline": "N/A"})
    assert result2["detected_deadline"] is None


def test_ensure_safety_note_filled_when_missing():
    result = ensure_required_fields({})
    assert isinstance(result["safety_note"], str)
    assert len(result["safety_note"]) > 10


def test_ensure_task_without_task_text_is_dropped():
    result = ensure_required_fields({"tasks": [{"owner": "Office Team"}]})
    assert result["tasks"] == []


def test_ensure_tasks_capped_at_five():
    tasks = [{"task_text": f"Task {i}"} for i in range(10)]
    result = ensure_required_fields({"tasks": tasks})
    assert len(result["tasks"]) <= 5


def test_ensure_task_owner_defaults_to_office_team():
    result = ensure_required_fields({"tasks": [{"task_text": "Do something"}]})
    assert result["tasks"][0]["owner"] == "Office Team"


def test_ensure_task_status_always_open():
    result = ensure_required_fields({"tasks": [{"task_text": "Do something", "status": "done"}]})
    assert result["tasks"][0]["status"] == "open"


# ── validate_ai_result ────────────────────────────────────────────────────────

def test_validate_handles_non_dict_input():
    result = validate_ai_result("not a dict")
    assert isinstance(result, dict)
    assert result["category"] == "general_inquiry"
    assert result["requires_human_review"] is True


def test_validate_handles_none_input():
    result = validate_ai_result(None)
    assert isinstance(result, dict)
    assert result["requires_human_review"] is True


def test_validate_full_valid_result():
    raw = {
        "category": "invoice",
        "priority": "medium",
        "summary": "Client submitted an invoice for payment.",
        "detected_deadline": None,
        "recommended_action": "Review and process within payment terms.",
        "tasks": [{"task_text": "Review invoice", "owner": "Office Team"}],
        "draft_reply": "Dear Client, thank you for your invoice.",
        "confidence": 0.88,
        "requires_human_review": True,
        "safety_note": "Review before sending.",
    }
    result = validate_ai_result(raw)
    assert result["category"] == "invoice"
    assert result["priority"] == "medium"
    assert result["requires_human_review"] is True
    assert abs(result["confidence"] - 0.88) < 1e-9


def test_validate_corrects_invalid_category():
    raw = {"category": "completely_wrong", "priority": "medium"}
    result = validate_ai_result(raw)
    assert result["category"] == "general_inquiry"


def test_validate_corrects_invalid_priority():
    raw = {"category": "invoice", "priority": "very_urgent_please"}
    result = validate_ai_result(raw)
    assert result["priority"] == "medium"
