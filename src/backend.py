import os
import requests
from pdfrw import PdfReader, PdfWriter
from validator import validate_json


class textToJSON:
    """
    Converts transcript text into structured JSON using an LLM.
    Supports dependency injection for testing.
    """

    def __init__(self, transcript_text, target_fields, json_data=None, llm_client=None):
        self.__transcript_text = transcript_text
        self.__target_fields = target_fields
        self.__json = json_data or {}
        self.llm_client = llm_client

        self._type_check()
        self._run_extraction()

    def _type_check(self):
        if not isinstance(self.__transcript_text, str):
            raise TypeError("Transcript must be a string.")

        if not isinstance(self.__target_fields, list):
            raise TypeError("Target fields must be a list.")

    def _build_prompt(self, field):
        return f"""
SYSTEM PROMPT:
Extract the value for the specified field from the transcript.
Return only the value. If not found, return "-1".

FIELD:
{field}

TRANSCRIPT:
{self.__transcript_text}
"""

    def _call_ollama(self, prompt):
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        ollama_url = f"{ollama_host}/api/generate"

        payload = {
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(ollama_url, json=payload, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            return json_data.get("response", "-1")
        except Exception:
            return "-1"

    def _run_extraction(self):
        for field in self.__target_fields:
            prompt = self._build_prompt(field)

            if self.llm_client:
                parsed_response = self.llm_client.generate(prompt)
            else:
                parsed_response = self._call_ollama(prompt)

            self._add_response(field, parsed_response)

        # Apply schema validation after extraction
        self.__json = validate_json(self.__json, self.__target_fields)

    def _add_response(self, field, value):
        value = (value or "").strip().replace('"', '')

        if value in ("-1", "", None):
            self.__json[field] = None
        elif ";" in value:
            self.__json[field] = [v.strip() for v in value.split(";")]
        else:
            self.__json[field] = value

    def get_data(self):
        return self.__json


class Fill:
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
                        annot.V = f"{answers_list[i]}"
                        annot.AP = None
                        i += 1
                    else:
                        break

        PdfWriter().write(output_pdf, pdf)
        return output_pdf