import json
import os
import time
import logging
import requests
from pdfrw import PdfReader, PdfWriter
from validator import validate_json


# ----------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class textToJSON:
    """
    Converts transcript text into structured JSON using an LLM.
    Supports dependency injection for testing.
    """

    def __init__(self, transcript_text, target_fields, json=None, llm_client=None):
        self.__transcript_text = transcript_text
        self.__target_fields = target_fields
        self.__json = json or {}

        # Dependency injection (used in tests)
        self.llm_client = llm_client

        self.type_check_all()
        self.main_loop()

    def type_check_all(self):
        if not isinstance(self.__transcript_text, str):
            raise TypeError("Transcript must be text.")

        if not isinstance(self.__target_fields, list):
            raise TypeError("Target fields must be a list.")

    def build_prompt(self, current_field):
        return f"""
SYSTEM PROMPT:
You are an AI assistant designed to extract a specific field value.
Return only the value. If not found, return "-1".

FIELD:
{current_field}

TEXT:
{self.__transcript_text}
"""

    # ----------------------------------------------------------
    # 🔥 Improved Ollama Call with Retry + Logging
    # ----------------------------------------------------------
    def _call_ollama(self, prompt):
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        ollama_url = f"{ollama_host}/api/generate"

        payload = {
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }

        max_retries = 3
        delay_seconds = 2

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    ollama_url,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                json_data = response.json()
                return json_data.get("response", "-1")

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Ollama request failed (attempt {attempt+1}/{max_retries}): {e}"
                )
                time.sleep(delay_seconds)

        logger.error("Ollama request failed after maximum retries.")
        return "-1"

    # ----------------------------------------------------------
    # Extraction Loop
    # ----------------------------------------------------------
    def main_loop(self):
        for field in self.__target_fields:
            prompt = self.build_prompt(field)

            # Use injected LLM for tests
            if self.llm_client:
                parsed_response = self.llm_client.generate(prompt)
            else:
                parsed_response = self._call_ollama(prompt)

            self.add_response_to_json(field, parsed_response)

        # Schema validation before final output
        self.__json = validate_json(self.__json, self.__target_fields)

    def add_response_to_json(self, field, value):
        value = (value or "").strip().replace('"', '')

        if value in ("-1", "", None):
            self.__json[field] = None
            return

        if ";" in value:
            self.__json[field] = [v.strip() for v in value.split(";")]
        else:
            self.__json[field] = value

    def get_data(self):
        return self.__json


class Fill:
    """
    Handles PDF autofill using extracted and validated JSON data.
    """

    @staticmethod
    def fill_form(user_input: str, definitions: list, pdf_form: str):

        output_pdf = pdf_form[:-4] + "_filled.pdf"

        extractor = textToJSON(user_input, definitions)
        textbox_answers = extractor.get_data()

        answers_list = list(textbox_answers.values())

        pdf = PdfReader(pdf_form)

        for page in pdf.pages:
            if not page.Annots:
                continue

            sorted_annots = sorted(
                page.Annots,
                key=lambda a: (-float(a.Rect[1]), float(a.Rect[0]))
            )

            i = 0
            for annot in sorted_annots:
                if annot.Subtype == '/Widget' and annot.T:
                    if i < len(answers_list):
                        annot.V = f'{answers_list[i]}'
                        annot.AP = None
                        i += 1
                    else:
                        break

        PdfWriter().write(output_pdf, pdf)

        return output_pdf