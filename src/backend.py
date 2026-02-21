import json
import os
import pathlib
import requests
from json_manager import JsonManager
from input_manager import InputManager
from pdfrw import PdfReader, PdfWriter



class textToJSON():
    def __init__(self, transcript_text, target_fields, json=None):
        self.__transcript_text = transcript_text  # str
        self.__target_fields = target_fields  # List, contains the template field.
        self.__json = json if json is not None else {}  # Avoid mutable default
        self.type_check_all()
        self.main_loop()

    
    def type_check_all(self):
        if not isinstance(self.__transcript_text, str):
            raise TypeError(
                f"ERROR in textToJSON() -> Transcript must be text. "
                f"Input:\n\ttranscript_text: {self.__transcript_text}"
            )
        if not isinstance(self.__target_fields, list):
            raise TypeError(
                f"ERROR in textToJSON() -> Target fields must be a list. "
                f"Input:\n\ttarget_fields: {self.__target_fields}"
            )

   
    def build_prompt(self, current_field):
        """ 
            This method is in charge of the prompt engineering. It creates a specific prompt for each target field. 
            @params: current_field -> represents the current element of the json that is being prompted.
        """
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

    def main_loop(self): #FUTURE -> Refactor this to its own class
        for field in self.__target_fields:
            prompt = self.build_prompt(field)
            # print(prompt)
            # ollama_url = "http://localhost:11434/api/generate"
            ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
            ollama_url = f"{ollama_host}/api/generate"

            payload = {
                "model": "mistral",
                "prompt": prompt,
                "stream": False # don't really know why --> look into this later.
            }

            response = requests.post(ollama_url, json=payload)

            # parse response
            json_data = response.json()
            parsed_response = json_data['response']
            # print(parsed_response)
            self.add_response_to_json(field, parsed_response)
            
        print("----------------------------------")
        print("\t[LOG] Resulting JSON created from the input text:")
        print(json.dumps(self.__json, indent=2))
        print("--------- extracted data ---------")

        return None

    def add_response_to_json(self, field, value):
        """Parse an LLM response and store it in the result dictionary.

        Args:
            field: The target field name.
            value: The raw string response from the LLM.

        Behavior:
            - If the LLM returned "-1", the field is skipped entirely.
            - If the value contains ";", it is split into a list.
            - Duplicate fields are merged into a list.
        """
        value = value.strip().replace('"', '')

        # Skip fields the LLM could not resolve
        if value == "-1":
            return

        # Parse plural vs singular values
        if ";" in value:
            parsed_value = self.handle_plural_values(value)
        else:
            parsed_value = value

        # Merge into existing field or create new entry
        if field in self.__json:
            existing = self.__json[field]
            if isinstance(existing, list):
                existing.append(parsed_value)
            else:
                self.__json[field] = [existing, parsed_value]
        else:
            self.__json[field] = parsed_value

    def handle_plural_values(self, plural_value):
        """Split a semicolon-separated string into a cleaned list.

        Args:
            plural_value: A string of the form 'value1; value2; ...; valueN'.

        Returns:
            A list of stripped strings: ['value1', 'value2', ..., 'valueN'].

        Raises:
            ValueError: If the input does not contain a semicolon.
        """
        if ";" not in plural_value:
            raise ValueError(
                f"Value is not plural, missing ';' separator. Value: {plural_value}"
            )

        print(f"\t[LOG]: Formatting plural values for JSON, [For input {plural_value}]...")
        values = [v.strip() for v in plural_value.split(";")]
        print(f"\t[LOG]: Resulting formatted list of values: {values}")

        return values
        

    def get_data(self):
        return self.__json

class Fill():
    """Coordinates the full pipeline from text extraction to PDF writing."""

    @staticmethod
    def fill_form(user_input: str, definitions: list, pdf_form: str) -> str:
        """Fill a PDF form with values extracted from natural-language text.

        Uses the textToJSON engine to extract field values via the LLM, then
        writes them into the PDF form fields in visual order
        (top-to-bottom, left-to-right).

        Args:
            user_input: Raw natural-language text describing the incident.
            definitions: List of field description strings to extract.
            pdf_form: Path to the fillable PDF template.

        Returns:
            Path to the newly created filled PDF file.
        """
        pdf_path = pathlib.Path(pdf_form)
        output_pdf = str(pdf_path.with_stem(pdf_path.stem + "_filled"))

        # Generate dictionary of answers from the LLM extraction engine
        t2j = textToJSON(user_input, definitions)
        textbox_answers = t2j.get_data()

        answers_list = list(textbox_answers.values())

        # Read PDF
        pdf = PdfReader(pdf_form)

        # Loop through pages and fill fields in visual order
        for page in pdf.pages:
            if page.Annots:
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
