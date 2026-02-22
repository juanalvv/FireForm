import json
import os
import requests
from json_manager import JsonManager
from input_manager import InputManager
from pdfrw import PdfReader, PdfWriter
from validator import validate_json   # 🔥 NEW IMPORT


class textToJSON():
    def __init__(self, transcript_text, target_fields, json={}):
        self.__transcript_text = transcript_text
        self.__target_fields = target_fields
        self.__json = json
        self.type_check_all()
        self.main_loop()

    def type_check_all(self):
        if type(self.__transcript_text) != str:
            raise TypeError(
                f"ERROR in textToJSON() -> Transcript must be text.\n"
                f"\ttranscript_text: {self.__transcript_text}"
            )
        elif type(self.__target_fields) != list:
            raise TypeError(
                f"ERROR in textToJSON() -> Target fields must be a list.\n"
                f"\ttarget_fields: {self.__target_fields}"
            )

    def build_prompt(self, current_field):
        prompt = f"""
SYSTEM PROMPT:
You are an AI assistant designed to help fill out JSON files with information extracted from transcribed voice recordings.
You will receive the transcription and the name of the JSON field whose value you must identify.
Return only the value. If not found, return "-1".

DATA:
Target JSON field to find in text: {current_field}

TEXT: {self.__transcript_text}
"""
        return prompt

    def main_loop(self):

        # Define once before loop (your earlier PR fix)
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

        # 🔥 NEW: Enforce schema validation before returning data
        self.__json = validate_json(self.__json, self.__target_fields)

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


class Fill():

    @staticmethod
    def fill_form(user_input: str, definitions: list, pdf_form: str):

        output_pdf = pdf_form[:-4] + "_filled.pdf"

        t2j = textToJSON(user_input, definitions)
        textbox_answers = t2j.get_data()

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