import pytesseract
import fitz
from PIL import Image
import io


# -----------------------------------------
# TESSERACT PATH
# -----------------------------------------

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# -----------------------------------------
# PDF OCR
# -----------------------------------------

def extract_text_from_pdf(pdf_path):

    document = fitz.open(pdf_path)

    full_text = ""

    for page in document:

        # Convert PDF page into image
        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2)
        )

        image_bytes = pix.tobytes("png")

        image = Image.open(
            io.BytesIO(image_bytes)
        )

        # OCR
        text = pytesseract.image_to_string(
            image
        )

        full_text += text + "\n"

    document.close()

    return full_text