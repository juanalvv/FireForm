import pytest
from backend import textToJSON
from validator import validate_json


class FakeLLM:
    """
    Mock LLM client that returns predefined responses
    in the order fields are requested.
    """
    def __init__(self, responses):
        self.responses = responses
        self.index = 0

    def generate(self, prompt: str) -> str:
        response = self.responses[self.index]
        self.index += 1
        return response


def test_full_extraction_and_validation_pipeline():
    transcript = "Name is John. Title is Manager."
    expected_fields = ["Name", "Title", "Department"]

    # Simulate LLM returning:
    # - Valid Name
    # - Valid Title
    # - Missing Department
    fake_llm = FakeLLM(["John", "Manager", "-1"])

    extractor = textToJSON(
        transcript_text=transcript,
        target_fields=expected_fields,
        llm_client=fake_llm
    )

    extracted = extractor.get_data()

    validated = validate_json(extracted, expected_fields)

    assert validated["Name"] == "John"
    assert validated["Title"] == "Manager"
    assert validated["Department"] is None