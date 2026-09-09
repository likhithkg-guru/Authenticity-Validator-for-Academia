from flask import Flask, render_template, request
import os
from werkzeug.utils import secure_filename

# Utility functions
from utils.ocr import extract_text_from_pdf
from utils.verifier import extract_details, verify_document
from utils.image_analyzer import analyze_image
from utils.authenticity import compare_documents


app = Flask(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

UPLOAD_FOLDER = "static/uploads"

REFERENCE_FOLDER = "reference_documents"

REFERENCE_FILE = "genuine_sample.pdf"


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# UPLOAD PAGE
# =========================================================

@app.route("/upload")
def upload():

    return render_template(
        "upload.html"
    )


# =========================================================
# ANALYZE DOCUMENT
# =========================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    # -----------------------------------------------------
    # Check uploaded file
    # -----------------------------------------------------

    if "document" not in request.files:

        return "No document uploaded"


    file = request.files["document"]


    # -----------------------------------------------------
    # Check filename
    # -----------------------------------------------------

    if file.filename == "":

        return "No file selected"


    # -----------------------------------------------------
    # Secure filename
    # -----------------------------------------------------

    filename = secure_filename(
        file.filename
    )


    # -----------------------------------------------------
    # Create file path
    # -----------------------------------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )


    # -----------------------------------------------------
    # Save uploaded document
    # -----------------------------------------------------

    file.save(filepath)


    # =====================================================
    # STEP 1 — OCR
    # =====================================================

    text = extract_text_from_pdf(
        filepath
    )


    # =====================================================
    # STEP 2 — EXTRACT DETAILS
    # =====================================================

    details = extract_details(
        text
    )


    # =====================================================
    # STEP 3 — DOCUMENT VERIFICATION
    # =====================================================

    checks, score, status = verify_document(
        details,
        text
    )


    # =====================================================
    # STEP 4 — IMAGE ANALYSIS
    # =====================================================

    image_info = analyze_image(
        filepath
    )


    # =====================================================
    # STEP 5 — REFERENCE DOCUMENT COMPARISON
    # =====================================================

    reference_path = os.path.join(
        REFERENCE_FOLDER,
        REFERENCE_FILE
    )


    # Check whether reference document exists

    if os.path.exists(reference_path):

        authenticity_result = compare_documents(
            filepath,
            reference_path
        )

    else:

        authenticity_result = {

            "similarity": 0,

            "status": "Reference document not found"
        }


    # =====================================================
    # STEP 6 — DISPLAY RESULT
    # =====================================================

    return render_template(

        "result.html",

        # Uploaded filename
        filename=filename,

        # OCR text
        text=text,

        # Extracted details
        details=details,

        # Verification checks
        checks=checks,

        # Verification score
        score=score,

        # Verification status
        status=status,

        # Image analysis
        image_info=image_info,

        # Authenticity comparison
        authenticity_result=authenticity_result
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )