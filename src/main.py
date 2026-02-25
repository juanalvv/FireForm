import os
from backend import Fill
from pypdf import PdfReader
import pdfplumber
from pathlib import Path
from typing import Union


def run_pdf_fill_process(user_input: str, field_names: list, pdf_form_path: Union[str, os.PathLike], form_context: str = ""):
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
        return None

    print(f"[3] Detected {len(field_names)} form fields: {field_names}")
    print("[4] Starting extraction and PDF filling process...")

    try:
        output_name = Fill.fill_form(
            user_input=user_input,
            field_names=field_names,
            pdf_form=pdf_form_path,
            form_context=form_context
        )

        print("\n----------------------------------")
        print(f"Process Complete.")
        print(f"Output saved to: {output_name}")

        return output_name

    except Exception as e:
        print(f"An error occurred during PDF generation: {e}")
        raise e


def extract_field_names(pdf_path: str) -> list:
    """
    Read form field names directly from the PDF metadata.
    No AI/vision model needed — just reads the PDF's built-in form fields.
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()

    if fields:
        field_names = list(fields.keys())
        print(f"[INFO] Found {len(field_names)} form fields: {field_names}")
        return field_names
    else:
        print("[WARN] No form fields found in PDF metadata.")
        return []


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text content from the PDF using pdfplumber.
    This gives the LLM extra context about the form.
    """
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    pdf_file = BASE_DIR / "inputs" / "file.pdf"

    # Step 1: Extract text from PDF
    print("[INFO] Extracting text from PDF...")
    pdf_text = extract_pdf_text(str(pdf_file))

    # Step 2: Try to read built-in field names (works for fillable PDFs)
    field_names = extract_field_names(str(pdf_file))

    # Step 3: Use LLM to analyze the form and get field descriptions
    from backend import FormAnalyzer
    analyzed_fields = FormAnalyzer.analyze_fields(pdf_text, existing_field_names=field_names or None)

    if not analyzed_fields:
        print("Could not detect any form fields. Exiting.")
        exit(1)

    # Step 4: Prompt user for each field (showing LLM-generated description)
    print(f"\n{len(analyzed_fields)} fields detected. Enter the value for each:")
    print("-" * 50)
    field_values = {}
    for i, field in enumerate(analyzed_fields):
        name = field.get("name", f"field_{i}")
        desc = field.get("description", name)
        value = input(f"  {name} ({desc}): ")
        field_values[name] = value.strip() if value.strip() else None
    print("-" * 50)

    # Step 5: Fill PDF
    from pdfrw import PdfReader as PdfrwReader, PdfWriter

    output_pdf = str(pdf_file)[:-4] + "_filled.pdf"
    pdf = PdfrwReader(str(pdf_file))

    for page in pdf.pages:
        if page.Annots:
            for annot in page.Annots:
                if annot.Subtype == '/Widget' and annot.T:
                    field_name = annot.T[1:-1]
                    if field_name in field_values and field_values[field_name] is not None:
                        annot.V = f'({field_values[field_name]})'
                        annot.AP = None

    PdfWriter().write(output_pdf, pdf)
    print("\n----------------------------------")
    print(f"Process Complete.")
    print(f"Output saved to: {output_pdf}")
