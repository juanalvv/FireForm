import json
import os
import requests
from json_manager import JsonManager
from input_manager import InputManager
from pdfrw import PdfReader, PdfWriter
from validator import validate_json


class textToJSON():
    def __init__(self, transcript_text, target_fields, json={}):
        self.__transcript_text = transcript_text  # str
        self.__target_fields = target_fields  # List
        self.__json = json  # dictionary
        self.type_check_all()
        self.main_loop()

    def type_check_all(self):
        if type(self.__transcript_text) != str:
            raise TypeError(f"ERROR in textToJSON() ->\
                Transcript must be text. Input:\n\ttranscript_text: {self.__transcript_text}")
        elif type(self.__target_fields) != list:
            raise TypeError(f"ERROR in textToJSON() ->\
                Target fields must be a list. Input:\n\ttarget_fields: {self.__target_fields}")

    def build_prompt(self, current_field):
        prompt = f""" 
            SYSTEM PROMPT:
            You are an AI assistant designed to help fillout json files with information extracted from transcribed voice recordings. 
            You will receive the transcription, and the name of the JSON field whose value you have to identify in the context. Return 
            only a single string containing the identified value for the JSON field. 
            If the field name is plural, and you identify more than one possible value in the text, return both separated by a ";".
            If you don't identify the value in the provided text, return "-1".
            ---
            DATA:
            Target JSON field to find in text: {current_field}
            
            TEXT: {self.__transcript_text}
            """
        return prompt

    def main_loop(self):
        for field in self.__target_fields:
            prompt = self.build_prompt(field)

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
            except requests.exceptions.RequestException as e:
                print("\n[ERROR] Failed to connect to Ollama.")
                print("Reason:", e)
                print("Marking field as not extracted.")

                self.add_response_to_json(field, "-1")
                continue

            try:
                json_data = response.json()
                parsed_response = json_data.get("response", "-1")
            except Exception as e:
                print("\n[ERROR] Failed to parse Ollama response.")
                print("Reason:", e)
                parsed_response = "-1"

            self.add_response_to_json(field, parsed_response)

        print("----------------------------------")
        print("\t[LOG] Resulting JSON created from the input text:")
        print(json.dumps(self.__json, indent=2))
        print("--------- extracted data ---------")

    def add_response_to_json(self, field, value):
        value = value.strip().replace('"', '')
        parsed_value = None
        plural = False

        if value != "-1":
            parsed_value = value

        if ";" in value:
            parsed_value = self.handle_plural_values(value)
            plural = True

        if field in self.__json.keys():
            self.__json[field].append(parsed_value)
        else:
            self.__json[field] = parsed_value

    def handle_plural_values(self, plural_value):
        if ";" not in plural_value:
            raise ValueError(f"Value is not plural, doesn't have ; separator, Value: {plural_value}")

        print(f"\t[LOG]: Formating plural values for JSON, [For input {plural_value}]...")
        values = plural_value.split(";")

        for i in range(len(values)):
            current = i + 1
            if current < len(values):
                clean_value = values[current].lstrip()
                values[current] = clean_value

        print(f"\t[LOG]: Resulting formatted list of values: {values}")
        return values

    def get_data(self):
        return validate_json(self.__json, self.__target_fields)


class Fill():
    def __init__(self):
        pass

    def fill_form(user_input: str, definitions: list, pdf_form: str):

        output_pdf = pdf_form[:-4] + "_filled.pdf"

        t2j = textToJSON(user_input, definitions)
        textbox_answers = t2j.get_data()

        answers_list = list(textbox_answers.values())

        pdf = PdfReader(pdf_form)

        for page in pdf.pages:
            if page.Annots:
                sorted_annots = sorted(
                    page.Annots,
                    key=lambda a: (-float(a.Rect[1]), float(a.Rect[0]))
                )

                i = 0
                for annot in sorted_annots:
                    if annot.Subtype == '/Widget' and annot.T:
                        field_name = annot.T[1:-1]

                        if i < len(answers_list):
                            annot.V = f'{answers_list[i]}'
                            annot.AP = None
                            i += 1
                        else:
                            break

        PdfWriter().write(output_pdf, pdf)
        return output_pdf