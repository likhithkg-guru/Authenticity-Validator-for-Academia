from flask import Flask, render_template, request
import os

from utils.ocr import extract_text_from_pdf
from utils.verifier import extract_details, verify_document
from utils.image_analyzer import analyze_image
from utils.authenticity import find_best_reference


app = Flask(__name__)


# ==================================================
# CONFIGURATION
# ==================================================

UPLOAD_FOLDER = "uploads"

REFERENCE_FOLDER = "reference_documents"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    REFERENCE_FOLDER,
    exist_ok=True
)


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==================================================
# UPLOAD
# ==================================================

@app.route("/upload")
def upload():

    return render_template(
        "upload.html"
    )


# ==================================================
# ANALYZE
# ==================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    # ----------------------------------------------
    # Check uploaded file
    # ----------------------------------------------

    if "document" not in request.files:

        return "No document uploaded"


    file = request.files["document"]


    if file.filename == "":

        return "No file selected"


    # ----------------------------------------------
    # Save document
    # ----------------------------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # ----------------------------------------------
    # OCR
    # ----------------------------------------------

    text = extract_text_from_pdf(
        filepath
    )


    # ----------------------------------------------
    # Extract details
    # ----------------------------------------------

    details = extract_details(
        text
    )


    # ----------------------------------------------
    # Verification
    # ----------------------------------------------

    checks, score, verification_status = verify_document(
        details,
        text
    )


    # ----------------------------------------------
    # Image analysis
    # ----------------------------------------------

    image_info = analyze_image(
        filepath
    )


    # ----------------------------------------------
    # MULTIPLE REFERENCE MATCHING
    # ----------------------------------------------

    authenticity_info = find_best_reference(
        filepath,
        REFERENCE_FOLDER
    )


    # ----------------------------------------------
    # FINAL STATUS
    # ----------------------------------------------

    final_status = verification_status


    if authenticity_info:

        similarity = authenticity_info[
            "similarity"
        ]


        if (
            similarity >= 90
            and score >= 75
        ):

            final_status = "LOW RISK"


        elif (
            similarity >= 70
            and score >= 50
        ):

            final_status = "NEEDS REVIEW"


        else:

            final_status = "SUSPICIOUS"


    # ----------------------------------------------
    # RESULT
    # ----------------------------------------------

    return render_template(

        "result.html",

        filename=file.filename,

        text=text,

        details=details,

        checks=checks,

        score=score,

        status=final_status,

        image_info=image_info,

        authenticity_info=authenticity_info
    )


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )