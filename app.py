from flask import Flask, render_template, request
import os

# Import project modules
from utils.ocr import extract_text_from_pdf
from utils.verifier import extract_details, verify_document
from utils.image_analyzer import analyze_image
from utils.authenticity import find_best_reference
from utils.risk_engine import (
    calculate_risk_score,
    generate_risk_explanation
)

app = Flask(__name__)

# --------------------------------------------------
# FOLDERS
# --------------------------------------------------

UPLOAD_FOLDER = "uploads"
REFERENCE_FOLDER = "reference_documents"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REFERENCE_FOLDER, exist_ok=True)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# UPLOAD PAGE
# --------------------------------------------------

@app.route("/upload")
def upload():
    return render_template("upload.html")


# --------------------------------------------------
# DOCUMENT ANALYSIS
# --------------------------------------------------

@app.route("/analyze", methods=["POST"])
def analyze():

    # Check whether a document was uploaded
    if "document" not in request.files:
        return "No document uploaded"

    file = request.files["document"]

    # Check whether a file was selected
    if file.filename == "":
        return "No file selected"

    # --------------------------------------------------
    # SAVE UPLOADED FILE
    # --------------------------------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)

    # --------------------------------------------------
    # OCR TEXT EXTRACTION
    # --------------------------------------------------

    text = extract_text_from_pdf(filepath)

    # --------------------------------------------------
    # EXTRACT IMPORTANT DETAILS
    # --------------------------------------------------

    details = extract_details(text)

    # --------------------------------------------------
    # DOCUMENT VERIFICATION
    # --------------------------------------------------

    checks, verification_score, verification_status = verify_document(
        details,
        text
    )

    # --------------------------------------------------
    # IMAGE QUALITY ANALYSIS
    # --------------------------------------------------

    image_info = analyze_image(filepath)

    # --------------------------------------------------
    # REFERENCE DOCUMENT COMPARISON
    # --------------------------------------------------

    authenticity_info = find_best_reference(
        filepath,
        REFERENCE_FOLDER
    )

    # Get visual similarity score
    similarity_score = None

    if authenticity_info:
        similarity_score = authenticity_info.get("similarity")

    # --------------------------------------------------
    # MULTI-SIGNAL RISK ANALYSIS
    # --------------------------------------------------

    risk_result = calculate_risk_score(
        verification_score=verification_score,
        similarity_score=similarity_score,
        image_quality=image_info.get("image_quality", "Unknown")
    )

    # --------------------------------------------------
    # EXPLAINABLE RESULT
    # --------------------------------------------------

    risk_explanation = generate_risk_explanation(
        verification_score=verification_score,
        similarity_score=similarity_score,
        image_quality=image_info.get("image_quality", "Unknown"),
        status=risk_result["status"]
    )

    # --------------------------------------------------
    # SEND ALL RESULTS TO RESULT PAGE
    # --------------------------------------------------

    return render_template(
        "result.html",

        # Uploaded document
        filename=file.filename,

        # OCR
        text=text,

        # Extracted details
        details=details,

        # Verification checks
        checks=checks,

        # Original verification score
        score=verification_score,

        # Original verification status
        verification_status=verification_status,

        # Final risk status
        status=risk_result["status"],

        # Image analysis
        image_info=image_info,

        # Reference comparison
        authenticity_info=authenticity_info,

        # Multi-signal scores
        overall_score=risk_result["overall_score"],
        quality_score=risk_result["quality_score"],

        # Explanation
        risk_explanation=risk_explanation
    )


# --------------------------------------------------
# RUN FLASK APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)