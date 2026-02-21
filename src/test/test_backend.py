"""
Tests for backend.py - covers the bug fixes from PR #1.

These tests mock the Ollama API so they run fast and don't need
a running LLM instance. We're testing the extraction logic, not
whether Mistral gives good answers.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from backend import textToJSON, Fill


# Helpers

def _mock_ollama_response(value):
    """Build a fake requests.Response that looks like what Ollama returns."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": value}
    return mock_resp


def _make_t2j_with_responses(text, fields, responses):
    """
    Create a textToJSON instance with mocked Ollama responses.

    `responses` should be a list of strings, one per field, in the same order.
    """
    side_effects = [_mock_ollama_response(r) for r in responses]
    with patch("backend.requests.post", side_effect=side_effects):
        return textToJSON(text, fields)


# Issue #1: Mutable default argument

class TestMutableDefault:

    @patch("backend.requests.post")
    def test_instances_dont_share_state(self, mock_post):
        """Two textToJSON instances created without passing json= should
        have completely independent dictionaries."""
        mock_post.return_value = _mock_ollama_response("some value")

        t1 = textToJSON("first call", ["field_a"])
        t2 = textToJSON("second call", ["field_b"])

        # t1 should only have field_a, t2 should only have field_b
        assert "field_a" in t1.get_data()
        assert "field_b" not in t1.get_data()
        assert "field_b" in t2.get_data()
        assert "field_a" not in t2.get_data()

    @patch("backend.requests.post")
    def test_dict_objects_are_different(self, mock_post):
        """The underlying dict objects should not be the same reference."""
        mock_post.return_value = _mock_ollama_response("val")

        t1 = textToJSON("text", ["f1"])
        t2 = textToJSON("text", ["f2"])

        assert t1.get_data() is not t2.get_data()


# Issue #3: @staticmethod on Fill.fill_form

class TestFillStaticMethod:

    def test_fill_form_is_static(self):
        """fill_form should be callable on both the class and an instance."""
        # This would have failed before the fix because Python would pass
        # the instance as the first arg (user_input), shifting everything.
        assert isinstance(
            Fill.__dict__["fill_form"],
            staticmethod
        )

    @patch("backend.PdfWriter")
    @patch("backend.PdfReader")
    @patch("backend.textToJSON")
    def test_fill_form_via_instance(self, mock_t2j, mock_reader, mock_writer):
        """Calling fill_form on an instance should work without crashing."""
        mock_t2j.return_value.get_data.return_value = {"Name": "John"}
        mock_reader.return_value.pages = []

        # This is the call that would have crashed before the fix
        result = Fill().fill_form("some text", ["Name"], "report.pdf")
        assert result == "report_filled.pdf"


# Issue #4: "-1" (not found) handling

class TestNotFoundHandling:

    def test_minus_one_is_skipped(self):
        """Fields where the LLM returns '-1' should not appear in the output."""
        t2j = _make_t2j_with_responses(
            "Officer Smith at 123 Main St",
            ["officer_name", "phone_number"],
            ["Officer Smith", "-1"],
        )
        data = t2j.get_data()
        assert data["officer_name"] == "Officer Smith"
        assert "phone_number" not in data

    def test_minus_one_with_whitespace(self):
        """'-1' with surrounding whitespace should also be skipped."""
        t2j = _make_t2j_with_responses(
            "some text",
            ["missing_field"],
            ["  -1  "],
        )
        assert "missing_field" not in t2j.get_data()

    def test_all_fields_not_found(self):
        """If the LLM can't find anything, the result should be empty."""
        t2j = _make_t2j_with_responses(
            "nothing useful here",
            ["a", "b", "c"],
            ["-1", "-1", "-1"],
        )
        assert t2j.get_data() == {}


# Issue #9: handle_plural_values strips all elements

class TestPluralValues:

    def test_basic_plural_split(self):
        """Semicolon-separated values should be split into a list."""
        t2j = _make_t2j_with_responses(
            "Victims are Alice and Bob",
            ["victim_names"],
            ["Alice; Bob"],
        )
        assert t2j.get_data()["victim_names"] == ["Alice", "Bob"]

    def test_first_element_is_stripped(self):
        """The first element should also have whitespace stripped.
        This was the actual bug - the old code skipped index 0."""
        t2j = _make_t2j_with_responses(
            "some text",
            ["names"],
            [" Alice ; Bob ; Charlie "],
        )
        result = t2j.get_data()["names"]
        assert result == ["Alice", "Bob", "Charlie"]
        # Make sure none of them have leading/trailing spaces
        for name in result:
            assert name == name.strip()

    def test_three_values(self):
        t2j = _make_t2j_with_responses(
            "text",
            ["agencies"],
            ["County PD; State Police; FBI"],
        )
        assert t2j.get_data()["agencies"] == ["County PD", "State Police", "FBI"]

    def test_handle_plural_raises_on_no_semicolon(self):
        """Calling handle_plural_values without a semicolon should raise."""
        t2j = _make_t2j_with_responses("text", ["f"], ["val"])
        with pytest.raises(ValueError, match="missing ';' separator"):
            t2j.handle_plural_values("no semicolon here")


# Issue #13: isinstance checks

class TestTypeValidation:

    def test_rejects_non_string_transcript(self):
        """Passing a non-string transcript should raise TypeError."""
        with pytest.raises(TypeError, match="Transcript must be text"):
            with patch("backend.requests.post"):
                textToJSON(12345, ["field"])

    def test_rejects_non_list_fields(self):
        """Passing a non-list for target_fields should raise TypeError."""
        with pytest.raises(TypeError, match="Target fields must be a list"):
            with patch("backend.requests.post"):
                textToJSON("text", "not a list")

    def test_accepts_string_subclass(self):
        """isinstance should accept subclasses of str (unlike type())."""
        class MyStr(str):
            pass

        t2j = _make_t2j_with_responses(
            MyStr("text from subclass"),
            ["field"],
            ["extracted"],
        )
        assert t2j.get_data()["field"] == "extracted"


# Issue #14: pathlib output path

class TestOutputPath:

    @patch("backend.PdfWriter")
    @patch("backend.PdfReader")
    @patch("backend.textToJSON")
    def test_standard_pdf_extension(self, mock_t2j, mock_reader, mock_writer):
        """Normal .pdf input should produce _filled.pdf output."""
        mock_t2j.return_value.get_data.return_value = {"f": "v"}
        mock_reader.return_value.pages = []

        result = Fill.fill_form("text", ["f"], "report.pdf")
        assert result == "report_filled.pdf"

    @patch("backend.PdfWriter")
    @patch("backend.PdfReader")
    @patch("backend.textToJSON")
    def test_uppercase_pdf_extension(self, mock_t2j, mock_reader, mock_writer):
        """Uppercase .PDF should also work correctly."""
        mock_t2j.return_value.get_data.return_value = {"f": "v"}
        mock_reader.return_value.pages = []

        result = Fill.fill_form("text", ["f"], "REPORT.PDF")
        assert result == "REPORT_filled.PDF"

    @patch("backend.PdfWriter")
    @patch("backend.PdfReader")
    @patch("backend.textToJSON")
    def test_path_with_directories(self, mock_t2j, mock_reader, mock_writer):
        """Paths with directories should keep the directory part intact."""
        mock_t2j.return_value.get_data.return_value = {"f": "v"}
        mock_reader.return_value.pages = []

        result = Fill.fill_form("text", ["f"], "/home/user/forms/intake.pdf")
        # Should keep the full path, just change the stem
        assert "intake_filled" in result
        assert result.endswith(".pdf")


# Integration-style: full extraction pipeline (mocked LLM)

class TestFullExtraction:

    def test_multi_field_extraction(self):
        """Simulate a realistic multi-field extraction with mixed results."""
        t2j = _make_t2j_with_responses(
            "Officer Smith responded to 456 Oak Street. Two victims: "
            "Mark Johnson and Jane Doe. No phone number available.",
            [
                "reporting_officer",
                "incident_location",
                "victim_names",
                "phone_number",
            ],
            [
                "Officer Smith",
                "456 Oak Street",
                "Mark Johnson; Jane Doe",
                "-1",
            ],
        )
        data = t2j.get_data()

        assert data["reporting_officer"] == "Officer Smith"
        assert data["incident_location"] == "456 Oak Street"
        assert data["victim_names"] == ["Mark Johnson", "Jane Doe"]
        assert "phone_number" not in data  # -1 should be skipped

    def test_quotes_are_stripped_from_values(self):
        """LLM sometimes wraps values in quotes, those should be removed."""
        t2j = _make_t2j_with_responses(
            "some text",
            ["name"],
            ['"John Doe"'],
        )
        assert t2j.get_data()["name"] == "John Doe"
