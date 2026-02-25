import json
import os
import requests
from json_manager import JsonManager
from input_manager import InputManager
from pdfrw import PdfReader, PdfWriter, PdfName


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
        """ 
            this method adds the following value under the specified field, 
            or under a new field if the field doesn't exist, to the json dict 
        """
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

def _get_pdf_field_value(annot):
    """
    Returns a best-effort string value from a PDF widget annotation.
    Handles text fields + buttons (checkbox/radio) reasonably.
    """
    # Text-like fields usually store value in /V
    if annot.V is not None:
        try:
            return str(annot.V).strip("()")
        except Exception:
            return str(annot.V)

    # Buttons often store state in /AS (e.g., /Yes, /Off)
    if annot.AS is not None:
        return str(annot.AS)

    return ""

def _get_sorted_widget_annots(pdf):
    """
    Returns widget annotations in the same visual order used for filling:
    page order, then top-to-bottom, left-to-right within each page.
    """
    ordered = []

    for page in pdf.pages:
        if not page.Annots:
            continue

        page_widgets = [
            annot for annot in page.Annots
            if str(getattr(annot, "Subtype", "")) == "/Widget"
        ]

        page_widgets = sorted(
            page_widgets,
            key=lambda a: (-float(a.Rect[1]), float(a.Rect[0]))
        )
        ordered.extend(page_widgets)

    return ordered

def verify_filled_pdf(output_pdf_path: str, expected_pairs: list):
    """
    expected_pairs: list of dicts like:
      [{"field": "employee_name", "expected": "John Doe"}, ...]
    Returns a report dict.
    """
    pdf = PdfReader(output_pdf_path)
    annots = _get_sorted_widget_annots(pdf)

    # Build actual list in same order (positional verification)
    actual_pairs = []
    for a in annots:
        field_name = str(a.T).strip("()") if a.T else "<unnamed>"
        actual_pairs.append({
            "field": field_name,
            "actual": _get_pdf_field_value(a)
        })

    # Compare expected vs actual by index (matches current pipeline design)
    results = []
    ok = mismatch = missing = 0

    for i, exp in enumerate(expected_pairs):
        exp_field = exp.get("field", f"field_{i}")
        exp_val = str(exp.get("expected", ""))

        act = actual_pairs[i] if i < len(actual_pairs) else {"field": "<missing_widget>", "actual": ""}
        act_val = str(act.get("actual", ""))

        if act_val == exp_val:
            status = "ok"
            ok += 1
        elif act_val.strip() == "":
            status = "missing"
            missing += 1
        else:
            status = "mismatch"
            mismatch += 1

        results.append({
            "index": i,
            "expected_field": exp_field,
            "pdf_field": act.get("field"),
            "expected": exp_val,
            "actual": act_val,
            "status": status
        })

    return {
        "summary": {"ok": ok, "missing": missing, "mismatch": mismatch},
        "results": results
    }
    
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

        answers_list = list(textbox_answers.values())

        # Read PDF 
        pdf = PdfReader(pdf_form)

        sorted_annots = _get_sorted_widget_annots(pdf)

        expected_pairs = []
        answer_index = 0
        for annot in sorted_annots:
            if not annot.T:
                continue

            if answer_index >= len(answers_list):
                break

            field_name = str(annot.T).strip("()")
            assigned_value = str(answers_list[answer_index])

            annot.V = assigned_value
            annot.AP = None

            expected_pairs.append({"field": field_name, "expected": assigned_value})
            answer_index += 1

        PdfWriter().write(output_pdf, pdf)

        report = verify_filled_pdf(output_pdf, expected_pairs)

        print("\nVerification Summary:")
        print(f"✔ ok: {report['summary']['ok']}")
        print(f"⚠ missing: {report['summary']['missing']}")
        print(f"✖ mismatch: {report['summary']['mismatch']}")

#write a JSON report next to output PDF
        try:
            import json
            verify_path = output_pdf + ".verify.json"
            with open(verify_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"Verification report saved to: {verify_path}")
        except Exception as e:
            print(f"(warn) Could not write verification report: {e}")
        return output_pdf


