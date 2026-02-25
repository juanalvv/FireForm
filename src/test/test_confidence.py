"""
Unit tests for confidence score extraction in textToJSON.
Tests parse_llm_response(), add_response_to_json(), and get_confidence_report().
"""
import json
import sys
import os
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import textToJSON


def make_t2j(fields=None):
    """Create a textToJSON instance without triggering main_loop (which calls Ollama)."""
    with patch.object(textToJSON, "main_loop", return_value=None):
        return textToJSON("dummy text", fields or ["field1"], json={})


class TestParseLlmResponse:
    def test_valid_json(self):
        t2j = make_t2j()
        raw = '{"value": "John Doe", "confidence": 0.92}'
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "John Doe"
        assert confidence == 0.92

    def test_not_found_response(self):
        t2j = make_t2j()
        raw = '{"value": "-1", "confidence": 0.0}'
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "-1"
        assert confidence == 0.0

    def test_plural_values(self):
        t2j = make_t2j()
        raw = '{"value": "Alice; Bob; Charlie", "confidence": 0.85}'
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "Alice; Bob; Charlie"
        assert confidence == 0.85

    def test_confidence_clamped_above_one(self):
        t2j = make_t2j()
        raw = '{"value": "test", "confidence": 1.5}'
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "test"
        assert confidence == 1.0

    def test_confidence_clamped_below_zero(self):
        t2j = make_t2j()
        raw = '{"value": "test", "confidence": -0.3}'
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "test"
        assert confidence == 0.0

    def test_malformed_json_fallback(self):
        t2j = make_t2j()
        raw = "just some plain text"
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "just some plain text"
        assert confidence == 0.0

    def test_malformed_json_warns_to_stderr(self, capsys):
        t2j = make_t2j()
        t2j.parse_llm_response("not valid json")
        captured = capsys.readouterr()
        assert "[WARNING]" in captured.err
        assert "Failed to parse" in captured.err

    def test_missing_value_key(self):
        t2j = make_t2j()
        raw = '{"confidence": 0.8}'
        value, confidence = t2j.parse_llm_response(raw)
        # Falls back to the raw string representation of missing key
        assert confidence == 0.8

    def test_missing_confidence_key(self):
        t2j = make_t2j()
        raw = '{"value": "hello"}'
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "hello"
        assert confidence == 0.0

    def test_whitespace_padding(self):
        t2j = make_t2j()
        raw = '  {"value": "trimmed", "confidence": 0.7}  '
        value, confidence = t2j.parse_llm_response(raw)
        assert value == "trimmed"
        assert confidence == 0.7


class TestAddResponseToJson:
    def test_stores_value_and_confidence(self):
        t2j = make_t2j()
        t2j.add_response_to_json("name", "John Doe", 0.92)
        data = t2j.get_data()
        assert data["name"] == {"value": "John Doe", "confidence": 0.92}

    def test_not_found_stores_none(self):
        t2j = make_t2j()
        t2j.add_response_to_json("missing_field", "-1", 0.0)
        data = t2j.get_data()
        assert data["missing_field"] == {"value": None, "confidence": 0.0}

    def test_plural_values_stored_as_list(self):
        t2j = make_t2j()
        t2j.add_response_to_json("items", "apple; banana; cherry", 0.85)
        data = t2j.get_data()
        assert data["items"]["value"] == ["apple", "banana", "cherry"]
        assert data["items"]["confidence"] == 0.85

    def test_low_confidence_warning(self, capsys):
        t2j = make_t2j()
        t2j.add_response_to_json("uncertain", "maybe", 0.3)
        captured = capsys.readouterr()
        assert "[WARNING]" in captured.err
        assert "0.3" in captured.err

    def test_high_confidence_no_warning(self, capsys):
        t2j = make_t2j()
        t2j.add_response_to_json("certain", "definitely", 0.95)
        captured = capsys.readouterr()
        assert "[WARNING]" not in captured.err

    def test_duplicate_field_becomes_list(self):
        t2j = make_t2j()
        t2j.add_response_to_json("name", "John", 0.9)
        t2j.add_response_to_json("name", "Jane", 0.8)
        data = t2j.get_data()
        assert isinstance(data["name"], list)
        assert len(data["name"]) == 2
        assert data["name"][0] == {"value": "John", "confidence": 0.9}
        assert data["name"][1] == {"value": "Jane", "confidence": 0.8}


class TestGetConfidenceReport:
    def test_single_fields(self):
        t2j = make_t2j()
        t2j.add_response_to_json("name", "John", 0.92)
        t2j.add_response_to_json("phone", "555-1234", 0.88)
        report = t2j.get_confidence_report()
        assert report == {"name": 0.92, "phone": 0.88}

    def test_list_field_reports_all_confidences(self):
        t2j = make_t2j()
        t2j.add_response_to_json("name", "John", 0.9)
        t2j.add_response_to_json("name", "Jane", 0.7)
        report = t2j.get_confidence_report()
        assert report["name"] == [0.9, 0.7]
