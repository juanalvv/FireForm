import json
import os
import requests
from pydantic import create_model, Field, ValidationError
from typing import Optional

# Keep existing imports just in case, though we primarily use pydantic/requests now
from json_manager import JsonManager
from input_manager import InputManager
from pdfrw import PdfReader, PdfWriter


class textToJSON():
    def __init__(self, transcript_text, target_fields, json_data=None):
        # Fixed BUG: Mutable default argument issue (Issue #29)
        if json_data is None:
            json_data = {}
            
        self.__transcript_text = transcript_text # str
        self.__target_fields = target_fields # List, contains the template field.
        self.__json = json_data # dictionary
        
        self.type_check_all()
        # Run the new single-shot Pydantic extraction
        self.extract_data_with_pydantic()


    def type_check_all(self):
        if type(self.__transcript_text) != str:
            raise TypeError(f"ERROR in textToJSON() ->\
                Transcript must be text. Input:\n\ttranscript_text: {self.__transcript_text}")
        elif type(self.__target_fields) != list:  
            raise TypeError(f"ERROR in textToJSON() ->\
                Target fields must be a list. Input:\n\ttarget_fields: {self.__target_fields}")


    def extract_data_with_pydantic(self):
        """
        Dynamically generates a Pydantic schema, asks the LLM to fill all fields 
        in a single request, and strictly validates the output.
        """
        print(f"\t[LOG] Generating Pydantic Schema for {len(self.__target_fields)} fields...")

        # 1. Map fields safely. PDF fields often have spaces (e.g., "Date of Incident").
        safe_fields = {}
        self.__field_mapping = {}

        for i, original_field in enumerate(self.__target_fields):
            safe_name = f"field_{i}"
            self.__field_mapping[safe_name] = original_field
            safe_fields[safe_name] = (
                Optional[str], 
                Field(default="-1", description=f"Extract value for: '{original_field}'")
            )

        # 2. Dynamically create the Pydantic Model
        DynamicIncidentModel = create_model('DynamicIncidentModel', **safe_fields)
        schema_json = json.dumps(DynamicIncidentModel.model_json_schema(), indent=2)

        # 3. Build a single, comprehensive prompt
        prompt = f"""
            SYSTEM PROMPT:
            You are an AI assistant designed to extract information from transcribed voice recordings and fill out JSON files.
            
            RULES:
            1. Output ONLY a valid JSON object matching the exact schema provided. Do not include conversational text.
            2. If you don't find a value for a specific field in the text, you MUST return "-1".
            3. If a field name is plural and you identify multiple values, return them as a single string separated by a ";" (e.g., "value1; value2").
            
            SCHEMA (Use these exact keys):
            {schema_json}

            TRANSCRIPT: 
            {self.__transcript_text}
        """

        # 4. Call Ollama once (Single-shot extraction)
        print("\t[LOG] Sending single-shot extraction request to Ollama...")
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        ollama_url = f"{ollama_host}/api/generate"

        payload = {
            "model": "mistral",
            "prompt": prompt,
            "format": "json", # Forces Ollama into strict JSON mode
            "stream": False 
        }

        try:
            response = requests.post(ollama_url, json=payload)
            response.raise_for_status()
            
            raw_response = response.json()['response']
            
            # 5. Validate output strictly against our Pydantic schema
            validated_data = DynamicIncidentModel.model_validate_json(raw_response)
            extracted_dict = validated_data.model_dump()

            # 6. Map safe fields back to original PDF fields
            for safe_key, parsed_value in extracted_dict.items():
                original_field_name = self.__field_mapping[safe_key]
                self.add_response_to_json(original_field_name, parsed_value)

            print("----------------------------------")
            print("\t[LOG] Resulting JSON created and validated via Pydantic:")
            print(json.dumps(self.__json, indent=2))
            print("--------- extracted data ---------")

        except ValidationError as e:
            print(f"\t[ERROR] AI returned invalid schema data. Pydantic Error:\n{e}")
        except Exception as e:
            print(f"\t[ERROR] An error occurred during extraction:\n{e}")


    def add_response_to_json(self, field, value):
        # Legacy helper maintained to ensure lists are handled correctly
        if not isinstance(value, str):
            value = str(value)
            
        value = value.strip().replace('"', '')
        parsed_value = None

        if value != "-1":
            parsed_value = value       
        
        if ";" in value:
            parsed_value = self.handle_plural_values(value)

        if field in self.__json.keys():
            if not isinstance(self.__json[field], list):
                self.__json[field] = [self.__json[field]]
            self.__json[field].append(parsed_value)
        else: 
            self.__json[field] = parsed_value

    def handle_plural_values(self, plural_value):
        print(f"\t[LOG]: Formatting plural values for JSON, [For input {plural_value}]...")
        values = plural_value.split(";")
        values = [v.strip() for v in values if v.strip()]
        print(f"\t[LOG]: Resulting formatted list of values: {values}")
        return values
        
    def get_data(self):
        ordered_data = {}
        for field in self.__target_fields:
            ordered_data[field] = self.__json.get(field, "-1")
        return ordered_data


class Fill():
    def __init__(self):
        pass
    
    @staticmethod
    def fill_form(user_input: str, definitions: list, pdf_form: str):
        """
        Fill a PDF form with values from user_input using textToJSON.
        Fields are filled in the visual order (top-to-bottom, left-to-right).
        """

        output_pdf = pdf_form[:-4] + "_filled.pdf"

        # 1. Generate dictionary of answers from the AI
        t2j = textToJSON(user_input, definitions)
        textbox_answers = t2j.get_data()  # This is a dictionary

        # ---------------------------------------------------------
        # 2. NEW: CLI FALLBACK (Human-in-the-Loop)
        # ---------------------------------------------------------
        print("\n\t[SYSTEM] Verifying extracted data completeness...")
        
        missing_fields = False
        for field_name, extracted_value in textbox_answers.items():
            if extracted_value == "-1":
                if not missing_fields:
                    print("\n\t⚠️ MISSING DATA DETECTED ")
                    print("\tThe AI could not find all required fields in the transcript.")
                    missing_fields = True
                
                # Prompt the user interactively in the terminal
                user_correction = input(f"\t Please enter the value for '{field_name}' (or press Enter to leave blank): ")
                
                # Update the dictionary with human input
                if user_correction.strip() != "":
                    textbox_answers[field_name] = user_correction.strip()
                else:
                    textbox_answers[field_name] = ""
                    
        if not missing_fields:
            print("\t All fields successfully extracted!")
        else:
            print("\n\t Manual data entry complete.")
        # ---------------------------------------------------------

        answers_list = list(textbox_answers.values())

        # 3. Read and Fill PDF 
        pdf = PdfReader(pdf_form)

        # Loop through pages 
        for page in pdf.pages:
            if page.Annots:
                sorted_annots = sorted(
                    page.Annots,
                    key=lambda a: (-float(a.Rect[1]), float(a.Rect[0]))
                )

                i = 0
                for annot in sorted_annots:
                    if annot.Subtype == '/Widget' and annot.T:
                        # field_name = annot.T[1:-1]
                        
                        if i < len(answers_list):
                            annot.V = f'{answers_list[i]}'
                            annot.AP = None
                            i += 1
                        else:
                            # Stop if we run out of answers
                            break 

        PdfWriter().write(output_pdf, pdf)
        
        # Your main.py expects this function to return the path
        return output_pdf