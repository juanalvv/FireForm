import json
import os
import requests
from json_manager import JsonManager
from input_manager import InputManager
from pdfrw import PdfReader, PdfWriter



class textToJSON():
    def __init__(self, transcript_text, target_fields, json={}):
        self.__transcript_text = transcript_text # str
        self.__target_fields = target_fields # List, contains the template field.
        self.__json = json # dictionary
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
        """
            This method is in charge of the prompt engineering. It creates a specific prompt for each target field.
            @params: current_field -> represents the current element of the json that is being prompted.
        """
        prompt = f"""
            SYSTEM PROMPT:
            You are an AI assistant designed to help fillout json files with information extracted from transcribed voice recordings.
            You will receive the transcription, and the name of the JSON field whose value you have to identify in the context.
            Return ONLY valid JSON with this exact format: {{"value": "<extracted_value>", "confidence": <0.0_to_1.0>}}
            The "confidence" field is a number from 0.0 to 1.0 indicating how confident you are in the extracted value.
            If the field name is plural, and you identify more than one possible value in the text, separate them with ";" inside the "value" string.
            If you don't identify the value in the provided text, return: {{"value": "-1", "confidence": 0.0}}
            ---
            DATA:
            Target JSON field to find in text: {current_field}

            TEXT: {self.__transcript_text}
            """

        return prompt

    def parse_llm_response(self, raw_response):
        """
            Parses the LLM JSON response and extracts value and confidence.
            Returns (value, confidence) tuple.
            Falls back to (raw_text, 0.0) on parse failure.
        """
        try:
            data = json.loads(raw_response.strip())
            value = str(data.get("value", raw_response.strip()))
            confidence = float(data.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))
            return value, confidence
        except (json.JSONDecodeError, ValueError, TypeError):
            return raw_response.strip(), 0.0

    def main_loop(self): #FUTURE -> Refactor this to its own class
        for field in self.__target_fields:
            prompt = self.build_prompt(field)
            ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
            ollama_url = f"{ollama_host}/api/generate"

            payload = {
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }

            response = requests.post(ollama_url, json=payload)

            # parse response
            json_data = response.json()
            raw_response = json_data['response']
            value, confidence = self.parse_llm_response(raw_response)
            self.add_response_to_json(field, value, confidence)

        print("----------------------------------")
        print("\t[LOG] Resulting JSON created from the input text:")
        print(json.dumps(self.__json, indent=2))
        print("--------- extracted data ---------")

        return None

    def add_response_to_json(self, field, value, confidence):
        """
            this method adds the following value under the specified field,
            or under a new field if the field doesn't exist, to the json dict.
            Stores each field as {"value": parsed_value, "confidence": confidence}.
        """
        value = value.strip().replace('"', '')
        parsed_value = None

        if value != "-1":
            parsed_value = value

        if ";" in value:
            parsed_value = self.handle_plural_values(value)

        if confidence < 0.5:
            print(f"\t[WARNING] Low confidence ({confidence}) for field '{field}'")

        entry = {"value": parsed_value, "confidence": confidence}

        if field in self.__json.keys():
            existing = self.__json[field]
            if isinstance(existing, list):
                existing.append(entry)
            else:
                self.__json[field] = [existing, entry]
        else:
            self.__json[field] = entry

        return

    def handle_plural_values(self, plural_value):
        """ 
            This method handles plural values.
            Takes in strings of the form 'value1; value2; value3; ...; valueN' 
            returns a list with the respective values -> [value1, value2, value3, ..., valueN]
        """
        if ";" not in plural_value:
            raise ValueError(f"Value is not plural, doesn't have ; separator, Value: {plural_value}")
        
        print(f"\t[LOG]: Formating plural values for JSON, [For input {plural_value}]...")
        values = plural_value.split(";")
        
        # Remove trailing leading whitespace
        for i in range(len(values)):
            current = i+1 
            if current < len(values):
                clean_value = values[current].lstrip()
                values[current] = clean_value

        print(f"\t[LOG]: Resulting formatted list of values: {values}")
        
        return values
        

    def get_data(self):
        return self.__json

    def get_confidence_report(self):
        """Returns a {field: confidence} dict for easy inspection by callers."""
        report = {}
        for field, entry in self.__json.items():
            if isinstance(entry, dict) and "confidence" in entry:
                report[field] = entry["confidence"]
            elif isinstance(entry, list):
                report[field] = [
                    item["confidence"] if isinstance(item, dict) and "confidence" in item else 0.0
                    for item in entry
                ]
            else:
                report[field] = 0.0
        return report

class Fill():
    def __init__(self):
        pass
    
    def fill_form(user_input: str, definitions: list, pdf_form: str):
        """
        Fill a PDF form with values from user_input using testToJSON.
        Fields are filled in the visual order (top-to-bottom, left-to-right).
        """

        output_pdf = pdf_form[:-4] + "_filled.pdf"

        # Generate dictionary of answers from your original function 
        t2j = textToJSON(user_input, definitions)
        textbox_answers = t2j.get_data()  # This is a dictionary

        answers_list = [
            entry["value"] if isinstance(entry, dict) and "value" in entry else entry
            for entry in textbox_answers.values()
        ]

        # Read PDF 
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
                        field_name = annot.T[1:-1]
                        
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
