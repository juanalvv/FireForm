import os
from backend import Fill, textToJSON
from commonforms import prepare_form
from pypdf import PdfReader
from pathlib import Path
from typing import Union
from input_manager import InputManager
from json_manager import JsonManager


def input_fields(num_fields: int):
    fields = []
    for i in range(num_fields):
        field = input(f"Enter description for field {i + 1}: ")
        fields.append(field)
    return fields


def run_pdf_fill_process(
    user_input: str, definitions: list, pdf_form_path: Union[str, os.PathLike]
):
    """
    This function is called by the frontend server.
    It receives the raw data, runs the PDF filling logic,
    and returns the path to the newly created file.
    """

    print("[1] Received request from frontend.")
    print(f"[2] PDF template path: {pdf_form_path}")

    # Normalize Path/PathLike to a plain string for downstream code
    pdf_form_path = os.fspath(pdf_form_path)

    if not os.path.exists(pdf_form_path):
        print(f"Error: PDF template not found at {pdf_form_path}")
        return None  # Or raise an exception

    print("[3] Starting extraction and PDF filling process...")
    try:
        output_name = Fill.fill_form(
            user_input=user_input,
            definitions=definitions,
            pdf_form=pdf_form_path,
        )

        print("\n----------------------------------")
        print(f"✅ Process Complete.")
        print(f"Output saved to: {output_name}")

        return output_name

    except Exception as e:
        print(f"An error occurred during PDF generation: {e}")
        raise e


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    input_pdf = BASE_DIR / "inputs" / "file.pdf"
    prepared_pdf = BASE_DIR / "outputs" / "temp_outfile.pdf"

    # Initialize managers
    manager = InputManager()
    json_mgr = JsonManager()

    # Prepare the PDF form
    prepare_form(str(input_pdf), str(prepared_pdf))

    # Get PDF field names to use as definitions
    reader = PdfReader(str(prepared_pdf))
    fields = reader.get_fields()

    if fields:
        definitions = list(fields.keys())
    else:
        num_fields = int(input("Enter number of fields: "))
        definitions = input_fields(num_fields)

    # Read transcript from file
    user_input = manager.file_to_text(str(BASE_DIR / "inputs" / "input.txt"))

    # Process and fill form
    output_pdf = run_pdf_fill_process(
        user_input, definitions, str(prepared_pdf)
    )

    # Extract and save the data
    if output_pdf:
        t2j = textToJSON(user_input, definitions)
        textbox_answers = t2j.get_data()
        json_mgr.save_json(
            textbox_answers, str(BASE_DIR / "outputs" / "extracted_data.json")
        )
