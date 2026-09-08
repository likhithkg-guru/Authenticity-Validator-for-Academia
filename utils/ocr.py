import pytesseract
import fitz
from PIL import Image
import io
import os

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_text_from_pdf(pdf_path):

    document = fitz.open(pdf_path)
    full_text = ""

    for page in document:

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        image_bytes = pix.tobytes("png")

        image = Image.open(io.BytesIO(image_bytes))

        text = pytesseract.image_to_string(image)

        full_text += text + "\n"

    document.close()

    return full_text
import re
def extract_details(text):
    details = {}

    # Candidate name
    match = re.search(r"Candidate'?s Name\s*[:\-]?\s*([A-Z][A-Z ]+)", text, re.IGNORECASE)
    if match:
        details["candidate_name"] = match.group(1).strip()

    # Register number
    match = re.search(r"Register No\.?\s*[:\-]?\s*([A-Z0-9]+)", text, re.IGNORECASE)
    if match:
        details["register_number"] = match.group(1).strip()

    # Date of birth
    match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4})", text)
    if match:
        details["date_of_birth"] = match.group(1)

    return details