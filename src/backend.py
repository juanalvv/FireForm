import json
import os
import requests
from pydantic import create_model, ValidationError, Field
from typing import Dict, List, Optional

# Keep your existing imports
from json_manager import JsonManager
from input_manager import InputManager
from pdfrw import PdfReader, PdfWriter

class textToJSON():
    def __init__(self, transcript_text, target_fields, json_data=None):
        # Renamed 'json' input to 'json_data' to avoid shadowing python's json module
        if json_data is None:
            json_data = {}
        self.__transcript_text = transcript_text
        self.__target_fields = target_fields
        self.__json = json_data
        
        self.type_check_all()
        # Instead of looping 20 times, we now run one smart extraction
        self.extract_data_with_pydantic()

    def type_check_all(self):
        if not isinstance(self.__transcript_text, str):
            raise TypeError(f"Transcript must be text. Got: {type(self.__transcript_text)}")
        if not isinstance(self.__target_fields, list):
            raise TypeError(f"Target fields must be a list. Got: {type(self.__target_fields)}")

    def extract_data_with_pydantic(self):
        """
        Dynamically creates a Pydantic model based on target_fields,
        asks the LLM to fill it once, and validates the output.
        """
        print(f"\t[LOG] Generating Pydantic Schema for {len(self.__target_fields)} fields...")

        # 1. Dynamically create a Pydantic model based on the list of fields
        # This creates a class strictly defining what we want (e.g., {'address': str, 'date': str})
        field_definitions = {
            field: (Optional[str], Field(default="-1", description=f"Extract value for {field}")) 
            for field in self.__target_fields
        }
        DynamicIncidentModel = create_model('DynamicIncidentModel', **field_definitions)

        # 2. Get the JSON schema to show the AI exactly what we want
        schema_json = json.dumps(DynamicIncidentModel.model_json_schema(), indent=2)

        # 3. Build a single, powerful prompt
        prompt = f"""
        SYSTEM: You are an AI data extraction assistant. 
        Your job is to extract incident details from the transcript into a strict JSON format.
        
        RULES:
        1. Output ONLY a valid JSON object matching the schema below.
        2. If a field is missing in the text, use the value "-1".
        3. If multiple values exist for a field, join them with a semicolon ";".
        4. Do not include any conversational text like "Here is the JSON".
        
        SCHEMA:
        {schema_json}

        TRANSCRIPT: 
        {self.__transcript_text}
        """

        # 4. Call Ollama (One single request instead of a loop!)
        print("\t[LOG] Sending request to Ollama (Single Shot Extraction)...")
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        ollama_url = f"{ollama_host}/api/generate"
        
        payload = {
            "model": "mistral", # Ensure this model is pulled in Ollama
            "prompt": prompt,
            "format": "json",   # Force Ollama into JSON mode
            "stream": False
        }

        try:
            response = requests.post(ollama_url, json=payload)
            response.raise_for_status()
            
            raw_response = response.json()['response']
            
            # 5. Validate with Pydantic
            # This is the magic: It checks types and ensures keys exist.
            validated_data = DynamicIncidentModel.model_validate_json(raw_response)
            
            # Convert back to dict to store in self.__json
            # mode='json' ensures everything is serializable
            self.__json = validated_data.model_dump(mode='json')
            
            print("\t[LOG] Pydantic Validation Successful!")
            print(json.dumps(self.__json, indent=2))

        except ValidationError as e:
            print(f"\t[ERROR] AI returned invalid JSON schema: {e}")
            # Fallback or retry logic could go here
        except requests.exceptions.RequestException as e:
            print(f"\t[ERROR] Could not connect to Ollama: {e}")
        except Exception as e:
            print(f"\t[ERROR] Unexpected error: {e}")

    def get_data(self):
        # The Fill class relies on the order of values matching the order of target_fields.
        # Dictionaries in Python 3.7+ preserve insertion order, but to be safe for the PDF filler:
        ordered_data = {}
        for field in self.__target_fields:
            ordered_data[field] = self.__json.get(field, "-1")
        return ordered_data