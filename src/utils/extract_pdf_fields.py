from pypdf import PdfReader
import sys
import os


def extract_fields(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
    try: 
        reader = PdfReader(pdf_path)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return
    
    fields = reader.get_fields()

    if not fields:
        print("No form fields found.")
        return

    print("PDF Form Fields:\n")
    for field in fields.keys():
        print(field)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_fields.py <pdf_path>")
        sys.exit(1)

    extract_fields(sys.argv[1])