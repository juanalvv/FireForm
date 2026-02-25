import pytest
from validator import validate_json


def test_all_fields_present_and_valid():
    data = {
        "Name": "John",
        "Title": "Manager"
    }
    expected = ["Name", "Title"]

    result = validate_json(data, expected)

    assert result["Name"] == "John"
    assert result["Title"] == "Manager"


def test_missing_fields_are_set_to_none():
    data = {
        "Name": "John"
    }
    expected = ["Name", "Title"]

    result = validate_json(data, expected)

    assert result["Name"] == "John"
    assert result["Title"] is None


def test_invalid_values_normalized_to_none():
    data = {
        "Name": "-1",
        "Title": ""
    }
    expected = ["Name", "Title"]

    result = validate_json(data, expected)

    assert result["Name"] is None
    assert result["Title"] is None


def test_type_error_on_invalid_input():
    with pytest.raises(TypeError):
        validate_json("not a dict", ["Name"])

    with pytest.raises(TypeError):
        validate_json({}, "not a list")