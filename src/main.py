import os
from backend import Fill  
from commonforms import prepare_form 
from pypdf import PdfReader
from pathlib import Path
from typing import Union

def input_fields(num_fields: int):
    fields = []
    for i in range(num_fields):
        field = input(f"Enter description for field {i + 1}: ")
        fields.append(field)
    return fields

def run_pdf_fill_process(user_input: str, definitions: list, pdf_form_path: Union[str, os.PathLike]):
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
        return None # Or raise an exception

    print("[3] Starting extraction and PDF filling process...")
    try:
        output_name = Fill.fill_form(
            user_input=user_input,
            definitions=definitions,
            pdf_form=pdf_form_path
        )
        
        print("\n----------------------------------")
        print(f"✅ Process Complete.")
        print(f"Output saved to: {output_name}")
        
        return output_name
        
    except Exception as e:
        print(f"An error occurred during PDF generation: {e}")
        # Re-raise the exception so the frontend can handle it
        raise e


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    file = BASE_DIR / "inputs" / "file.pdf"
    prepared_pdf = BASE_DIR / "temp_outfile.pdf"
    
    #file = "/Users/vincentharkins/Desktop/FireForm/src/inputs/file.pdf"
    user_input = "Hi. The employee's name is John Doe. His job title is managing director. His department supervisor is Jane Doe. His phone number is 123456. His email is jdoe@ucsc.edu. The signature is <Mamañema>, and the date is 01/02/2005"
    descriptions = ["Employee's name", "Employee's job title", "Employee's department supervisor", "Employee's phone number", "Employee's email", "Signature", "Date"]
    prepare_form(str(file), str(prepared_pdf))
    
    reader = PdfReader(prepared_pdf)
    fields = reader.get_fields()
    if(fields):
        num_fields = len(fields)
    else:
        num_fields = 0
        
    descriptions = input_fields(num_fields) # Uncomment to edit fields
    
    run_pdf_fill_process(user_input, descriptions, str(file))
