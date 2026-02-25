import json
import os
import requests
from pdfrw import PdfReader, PdfWriter


class FormAnalyzer():
    """
    Uses an LLM (text-only, no vision) to analyze extracted PDF text
    and identify the fillable form fields. Works with any form.
    """

    @staticmethod
    def analyze_fields(pdf_text: str, existing_field_names: list = None) -> list:
        """
        Send the extracted PDF text to the LLM to identify form fields and
        return a list of dicts with 'name' and 'description' for each field.
        
        If existing_field_names are provided (from pypdf), the LLM enriches
        them with better descriptions. Otherwise, it discovers fields from text.
        """
        if existing_field_names:
            fields_hint = "\n".join(f"  - {f}" for f in existing_field_names)
            prompt = f"""You are a form analysis assistant. Below is text extracted from a PDF form, along with the technical field names found in the form.

For each field, provide a clear, human-readable description of what value should be entered.

RULES:
- Return ONLY a valid JSON array of objects, each with "name" (the exact technical field name) and "description" (a clear explanation).
- Do NOT rename or change the "name" — use the exact field names provided.
- Do NOT include any explanation or extra text, just the JSON array.

TECHNICAL FIELD NAMES:
{fields_hint}

FORM TEXT:
{pdf_text}

JSON output:"""
        else:
            prompt = f"""You are a form analysis assistant. Below is text extracted from a PDF form.

Identify ALL fillable fields in this form (blanks, underlines, or areas where a user would write/type information).

RULES:
- Return ONLY a valid JSON array of objects, each with "name" (a short technical name) and "description" (what should be filled in).
- Do NOT include any explanation or extra text, just the JSON array.
- Be thorough — identify every field where data needs to be entered.

FORM TEXT:
{pdf_text}

JSON output:"""

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        ollama_url = f"{ollama_host}/api/generate"

        payload = {
            "model": os.getenv("OLLAMA_MODEL", "llama3:latest"),
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        print("\t[LOG] Asking LLM to analyze form fields...")
        response = requests.post(ollama_url, json=payload)
        json_data = response.json()
        raw_response = json_data['response'].strip()

        try:
            fields = json.loads(raw_response)
            # Handle case where LLM wraps array in an object
            if isinstance(fields, dict):
                # Try to find the array inside
                for key, val in fields.items():
                    if isinstance(val, list):
                        fields = val
                        break
            if isinstance(fields, list):
                print(f"\t[LOG] LLM identified {len(fields)} fields.")
                return fields
        except json.JSONDecodeError:
            pass

        print("\t[WARN] LLM field analysis failed. Using fallback.")
        if existing_field_names:
            return [{"name": f, "description": f} for f in existing_field_names]
        return []


class textToJSON():
    def __init__(self, transcript_text, field_names, form_context=""):
        self.__transcript_text = transcript_text  # str
        self.__field_names = field_names  # List of PDF field names
        self.__form_context = form_context  # Extracted text from the PDF form for context
        self.__json = {}  # dictionary
        self.type_check_all()
        self.extract_all_fields()

    def type_check_all(self):
        if type(self.__transcript_text) != str:
            raise TypeError(f"ERROR in textToJSON() -> "
                f"Transcript must be text. Input:\n\ttranscript_text: {self.__transcript_text}")
        elif type(self.__field_names) != list:
            raise TypeError(f"ERROR in textToJSON() -> "
                f"Field names must be a list. Input:\n\tfield_names: {self.__field_names}")

    def build_prompt(self):
        """
        Build a single prompt that asks the LLM to extract ALL field values at once.
        Uses the form's own text as context so the LLM understands what each field means.
        """
        fields_list = "\n".join(f"  - {f}" for f in self.__field_names)

        form_section = ""
        if self.__form_context:
            form_section = f"""\nFORM CONTEXT (extracted text from the PDF form, use this to understand what each field means):
{self.__form_context}\n"""

        prompt = f"""You are a data extraction assistant. You are given a form with specific fields and a text description. Extract the correct value for each form field from the text.

RULES:
- Return ONLY a valid JSON object mapping each field name to its extracted value.
- Use the form context to understand what each field represents.
- If a value is not found in the text, set it to null.
- Do NOT include any explanation, markdown formatting, or extra text.
- Return ONLY the raw JSON object, nothing else.
{form_section}
FORM FIELDS TO FILL:
{fields_list}

USER INPUT TEXT:
{self.__transcript_text}

JSON output:"""

        return prompt

    def extract_all_fields(self):
        """
        Make a single LLM call to extract all field values at once.
        """
        prompt = self.build_prompt()

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        ollama_url = f"{ollama_host}/api/generate"

        payload = {
            "model": os.getenv("OLLAMA_MODEL", "llama3:latest"),
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        print("\t[LOG] Sending single LLM request for all fields...")
        response = requests.post(ollama_url, json=payload)

        json_data = response.json()
        raw_response = json_data['response'].strip()

        print(f"\t[LOG] LLM raw response: {raw_response}")

        try:
            extracted = json.loads(raw_response)
            self.__json = extracted
        except json.JSONDecodeError:
            print("\t[WARN] LLM did not return valid JSON. Attempting field-by-field fallback...")
            self.__json = {field: None for field in self.__field_names}

        # Log results
        print("----------------------------------")
        print("\t[LOG] Extracted data:")
        print(json.dumps(self.__json, indent=2))
        print("----------------------------------")

    def get_data(self):
        return self.__json


class Fill():
    def __init__(self):
        pass

    def fill_form(user_input: str, field_names: list, pdf_form: str, form_context: str = ""):
        """
        Fill a PDF form using LLM-extracted values.
        Fields are matched by their annotation name (not position).
        """
        output_pdf = pdf_form[:-4] + "_filled.pdf"

        # Extract all values via a single LLM call
        t2j = textToJSON(user_input, field_names, form_context=form_context)
        extracted_data = t2j.get_data()

        # Read PDF
        pdf = PdfReader(pdf_form)

        # Fill fields by matching annotation names
        for page in pdf.pages:
            if page.Annots:
                for annot in page.Annots:
                    if annot.Subtype == '/Widget' and annot.T:
                        field_name = annot.T[1:-1]  # Remove parentheses

                        if field_name in extracted_data:
                            value = extracted_data[field_name]
                            if value is not None:
                                annot.V = f'({value})'
                                annot.AP = None
                                print(f"\t[LOG] Filled '{field_name}' -> '{value}'")

        PdfWriter().write(output_pdf, pdf)

        return output_pdf
