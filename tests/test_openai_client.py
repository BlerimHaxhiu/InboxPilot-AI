"""
Tests for src/openai_client.py.

All tests run without a real OpenAI API key.
The _make_openai_call function is monkeypatched to return controlled responses.
"""
import json
import pytest
import src.openai_client as oc_module
from src.openai_client import analyze_email_with_openai, analyze_email_with_ai
from src.models import EmailAnalysis


# ── Helpers ───────────────────────────────────────────────────────────────────

def _valid_ai_response(**overrides) -> str:
    """Return a JSON string representing a valid AI response."""
    base = {
        "category": "invoice",
        "priority": "medium",
        "summary": "Client has submitted an invoice for payment.",
        "detected_deadline": None,
        "recommended_action": "Review and process within payment terms.",
        "tasks": [
            {
                "task_text": "Review the submitted invoice",
                "owner": "Office Team",
                "due_date": None,
                "priority": "medium",
            }
        ],
        "draft_reply": (
            "Dear Client,\n\nThank you for your invoice. "
            "[TODO: Add payment confirmation details.]\n\nKind regards,\n[Your Name]"
        ),
        "confidence": 0.88,
        "requires_human_review": True,
        "safety_note": "Review before sending.",
    }
    base.update(overrides)
    return json.dumps(base)


class _MockClient:
    """Minimal mock of openai.OpenAI client."""

    def __init__(self, response_content: str | None = None, raise_exc: Exception | None = None):
        self._content = response_content
        self._exc = raise_exc

        class _Completions:
            def __init__(self_, content, exc):
                self_._content = content
                self_._exc = exc

            def create(self_, **kwargs):
                if self_._exc:
                    raise self_._exc

                class _Message:
                    content = self_._content

                class _Choice:
                    message = _Message()

                class _Response:
                    choices = [_Choice()]

                return _Response()

        class _Chat:
            def __init__(self_, content, exc):
                self_.completions = _Completions(content, exc)

        self.chat = _Chat(response_content, raise_exc)


# ── No API key ────────────────────────────────────────────────────────────────

def test_analyze_email_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", False)
    result = analyze_email_with_openai("Invoice #001", "Please process this invoice.")
    assert result is None


def test_legacy_analyze_email_with_ai_returns_none_without_key(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", False)
    result = analyze_email_with_ai("Invoice #001", "Please process this invoice.")
    assert result is None


# ── Mocked valid response ─────────────────────────────────────────────────────

def test_analyze_email_returns_validated_dict_on_success(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(oc_module, "_client", lambda: _MockClient(_valid_ai_response()))

    result = analyze_email_with_openai("Invoice #001", "Please process Invoice #001.")
    assert result is not None
    assert isinstance(result, dict)
    assert result["category"] == "invoice"
    assert result["priority"] == "medium"
    assert result["requires_human_review"] is True


def test_analyze_email_result_contains_all_required_fields(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(oc_module, "_client", lambda: _MockClient(_valid_ai_response()))

    result = analyze_email_with_openai("Invoice #001", "Please process Invoice #001.")
    required_keys = {
        "category", "priority", "summary", "detected_deadline",
        "recommended_action", "tasks", "draft_reply",
        "confidence", "requires_human_review", "safety_note",
    }
    assert required_keys.issubset(result.keys())


def test_analyze_email_confidence_in_valid_range(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(oc_module, "_client", lambda: _MockClient(_valid_ai_response()))

    result = analyze_email_with_openai("Invoice #001", "...")
    assert 0.0 <= result["confidence"] <= 1.0


def test_analyze_email_requires_human_review_always_true(monkeypatch):
    """requires_human_review must be True even if model returns False."""
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(
        oc_module, "_client",
        lambda: _MockClient(_valid_ai_response(requires_human_review=False)),
    )
    result = analyze_email_with_openai("Subject", "Body")
    assert result["requires_human_review"] is True


# ── Invalid model output handling ─────────────────────────────────────────────

def test_invalid_json_response_returns_none(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(oc_module, "_client", lambda: _MockClient("not valid json {{"))

    result = analyze_email_with_openai("Subject", "Body")
    assert result is None


def test_api_exception_returns_none(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(
        oc_module, "_client",
        lambda: _MockClient(raise_exc=ConnectionError("Network error")),
    )
    result = analyze_email_with_openai("Subject", "Body")
    assert result is None


def test_non_dict_json_response_returns_none(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(oc_module, "_client", lambda: _MockClient(json.dumps(["list", "not", "dict"])))

    result = analyze_email_with_openai("Subject", "Body")
    assert result is None


def test_invalid_category_in_response_normalised(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(
        oc_module, "_client",
        lambda: _MockClient(_valid_ai_response(category="completely_made_up_category")),
    )
    result = analyze_email_with_openai("Subject", "Body")
    assert result is not None
    assert result["category"] == "general_inquiry"


def test_invalid_priority_in_response_normalised(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(
        oc_module, "_client",
        lambda: _MockClient(_valid_ai_response(priority="super_duper_urgent")),
    )
    result = analyze_email_with_openai("Subject", "Body")
    assert result is not None
    assert result["priority"] == "medium"


def test_missing_tasks_field_defaults_to_empty_list(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    response = {
        "category": "general_inquiry",
        "priority": "low",
        "summary": "A general question.",
        "confidence": 0.5,
        "requires_human_review": True,
        "safety_note": "Review required.",
    }
    monkeypatch.setattr(oc_module, "_client", lambda: _MockClient(json.dumps(response)))
    result = analyze_email_with_openai("Subject", "Body")
    assert result is not None
    assert isinstance(result["tasks"], list)


def test_make_openai_call_returns_none_on_exception(monkeypatch):
    """_make_openai_call isolates the raw API call — should return None on any error."""
    from src.openai_client import _make_openai_call
    bad_client = _MockClient(raise_exc=RuntimeError("timeout"))
    result = _make_openai_call(bad_client, [{"role": "user", "content": "test"}])
    assert result is None


# ── Legacy wrapper ────────────────────────────────────────────────────────────

def test_legacy_wrapper_returns_email_analysis_on_success(monkeypatch):
    monkeypatch.setattr(oc_module, "HAS_OPENAI", True)
    monkeypatch.setattr(oc_module, "_client", lambda: _MockClient(_valid_ai_response()))

    result = analyze_email_with_ai("Invoice #001", "Please process Invoice #001.")
    assert isinstance(result, EmailAnalysis)
    assert result.category == "invoice"
    assert result.priority == "medium"
