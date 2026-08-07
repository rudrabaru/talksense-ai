import pytest
from pydantic import ValidationError

from services.response_validator import _extract_json, validate_and_parse


def test_extract_json_raw():
    raw = '{"executive_summary": "test"}'
    assert _extract_json(raw) == raw


def test_extract_json_markdown():
    raw = '```json\n{"executive_summary": "test"}\n```'
    assert _extract_json(raw) == '{"executive_summary": "test"}'


def test_extract_json_markdown_no_language():
    raw = '```\n{"executive_summary": "test"}\n```'
    assert _extract_json(raw) == '{"executive_summary": "test"}'


def test_extract_json_with_surrounding_text():
    raw = 'Here is the output:\n```json\n{"executive_summary": "test"}\n```\nHope this helps!'
    assert _extract_json(raw) == '{"executive_summary": "test"}'


def test_extract_json_fallback_brackets():
    raw = 'Some text before {"executive_summary": "test"} and some after'
    assert _extract_json(raw) == '{"executive_summary": "test"}'


def test_extract_json_missing():
    raw = "There is no json here"
    with pytest.raises(ValueError, match="No valid JSON block detected"):
        _extract_json(raw)


def test_validate_happy_path():
    raw = """{
        "executive_summary": "Meeting went well.",
        "decisions": ["Approved budget"],
        "action_items": [
            {"task": "Send email", "assignee": "John"}
        ]
    }"""
    result = validate_and_parse(raw)
    assert result["executive_summary"] == "Meeting went well."
    assert result["decisions"] == ["Approved budget"]
    assert len(result["action_items"]) == 1
    assert result["action_items"][0]["task"] == "Send email"


def test_validate_missing_lists_defaults():
    raw = '{"executive_summary": "Meeting went well."}'
    result = validate_and_parse(raw)
    assert result["executive_summary"] == "Meeting went well."
    assert result["decisions"] == []
    assert result["action_items"] == []


def test_validate_empty_summary():
    raw = '{"executive_summary": "   ", "decisions": []}'
    with pytest.raises(ValidationError, match="executive_summary cannot be empty"):
        validate_and_parse(raw)


def test_validate_missing_summary():
    raw = '{"decisions": []}'
    with pytest.raises(ValidationError, match="executive_summary"):
        validate_and_parse(raw)


def test_validate_wrong_data_types():
    raw = '{"executive_summary": "test", "decisions": "Not a list"}'
    with pytest.raises(ValidationError, match="decisions"):
        validate_and_parse(raw)


def test_validate_invalid_action_item():
    raw = """{
        "executive_summary": "test",
        "action_items": [
            {"task": "Send email"}
        ]
    }"""
    with pytest.raises(ValidationError, match="assignee"):
        validate_and_parse(raw)


def test_validate_unexpected_fields():
    raw = """{
        "executive_summary": "test",
        "unexpected_field": "should be rejected"
    }"""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        validate_and_parse(raw)


def test_validate_malformed_json():
    raw = '{"executive_summary": "test", }'  # trailing comma is invalid JSON
    with pytest.raises(ValueError, match="Malformed JSON"):
        validate_and_parse(raw)
