import json
import os
import requests
from pdfrw import PdfReader, PdfWriter


# ==========================================================
# LLM CLIENT LAYER
# ==========================================================
class OllamaClient:
    """
    Handles communication with Ollama.
    This isolates HTTP logic from extraction logic.
    """

    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_url = f"{self.ollama_host}/api/generate"

    def generate(self, prompt: str) -> str:
        payload = {
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print("\n[ERROR] Failed to connect to Ollama.")
            print("Reason:", e)
            return "-1"

        try:
            json_data = response.json()
            return json_data.get("response", "-1")
        except Exception as e:
            print("\n[ERROR] Failed to parse Ollama response.")
            print("Reason:", e)
            return "-1"


# ==========================================================
# EXTRACTION LAYER
# ==========================================================
class textToJSON:
    def __init__(self, transcript_text, target_fields, json={}):
        self.__transcript_text = transcript_text
        self.__target_fields = target_fields
        self.__json = json
        self.type_check_all()
        self.main_loop()

    def type_check_all(self):
        if type(self.__transcript_text) != str:
            raise TypeError("Transcript must be text.")
        elif type(self.__target_fields) != list:
            raise TypeError("Target fields must be a list.")

    def build_prompt(self, current_field):
        prompt = f"""
SYSTEM PROMPT:
You are an AI assistant designed to extract a specific field value from a transcript.
Return only the value. If not found, return "-1".

FIELD:
{current_field}

TRANSCRIPT:
{self.__transcript_text}
"""
        return prompt

    def main_loop(self):

        # ✅ FIX: Define Ollama host and URL once (outside loop)
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        ollama_url = f"{ollama_host}/api/generate"

        for field in self.__target_fields:
            prompt = self.build_prompt(field)

            payload = {
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }

            response = requests.post(ollama_url, json=payload)
            json_data = response.json()
            parsed_response = json_data.get("response", "-1")

            self.add_response_to_json(field, parsed_response)

        print("----------------------------------")
        print("\t[LOG] Resulting JSON created from the input text:")
        print(json.dumps(self.__json, indent=2))
        print("--------- extracted data ---------")

    def add_response_to_json(self, field, value):
        value = value.strip().replace('"', '')

        if value == "-1":
            self.__json[field] = None
            return

        if ";" in value:
            self.__json[field] = [v.strip() for v in value.split(";")]
        else:
            self.__json[field] = value

    def get_data(self):
        return self.__json


# ==========================================================
# PDF FILLING LAYER
# ==========================================================
class Fill:

    @staticmethod
    def fill_form(user_input: str, definitions: list, pdf_form: str):
        """
        Fill a PDF form with extracted values.
        """

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