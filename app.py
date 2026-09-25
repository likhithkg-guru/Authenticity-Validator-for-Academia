from flask import Flask, render_template, request, send_from_directory
import os

from utils.ocr import extract_text_from_pdf
from utils.verifier import extract_details, verify_document
from utils.image_analyzer import analyze_image
from utils.authenticity import find_best_reference

from utils.risk_engine import (
    calculate_risk_score,
    generate_risk_explanation
)

from utils.ml_detector import analyze_with_ml


app = Flask(__name__)


# =========================================================
# FOLDERS
# =========================================================

UPLOAD_FOLDER = "uploads"
REFERENCE_FOLDER = "reference_documents"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Create required folders
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REFERENCE_FOLDER, exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# UPLOAD PAGE
# =========================================================

@app.route("/upload")
def upload():

    return render_template("upload.html")


# =========================================================
# SERVE UPLOADED PDF
# =========================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =========================================================
# SERVE REFERENCE PDF
# =========================================================

@app.route("/references/<filename>")
def reference_file(filename):

    return send_from_directory(
        REFERENCE_FOLDER,
        filename
    )


# =========================================================
# ANALYZE DOCUMENT
# =========================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    # -----------------------------------------------------
    # Check file
    # -----------------------------------------------------

    if "document" not in request.files:

        return "No document uploaded"


    file = request.files["document"]


    if file.filename == "":

        return "No file selected"


    # -----------------------------------------------------
    # Save uploaded document
    # -----------------------------------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # =====================================================
    # 1. OCR
    # =====================================================

    text = extract_text_from_pdf(
        filepath
    )


    # =====================================================
    # 2. EXTRACT INFORMATION
    # =====================================================

    details = extract_details(
        text
    )


    # =====================================================
    # 3. BASIC VERIFICATION
    # =====================================================

    checks, verification_score, verification_status = (
        verify_document(
            details,
            text
        )
    )


    # =====================================================
    # 4. IMAGE QUALITY
    # =====================================================

    image_info = analyze_image(
        filepath
    )


    # =====================================================
    # 5. REFERENCE DOCUMENT COMPARISON
    # =====================================================

    authenticity_info = find_best_reference(
        filepath,
        REFERENCE_FOLDER
    )


    similarity_score = None


    if authenticity_info:

        similarity_score = authenticity_info.get(
            "similarity"
        )


    # =====================================================
    # 6. MACHINE LEARNING ANALYSIS
    # =====================================================

    ml_result = analyze_with_ml(
        filepath,
        REFERENCE_FOLDER
    )


    # =====================================================
    # 7. OVERALL RISK SCORE
    # =====================================================

    risk_result = calculate_risk_score(

        verification_score=verification_score,

        similarity_score=similarity_score,

        image_quality=image_info.get(
            "image_quality",
            "Unknown"
        ),

        ml_anomaly_score=ml_result.get(
            "anomaly_score"
        )
    )


    # =====================================================
    # 8. RISK EXPLANATION
    # =====================================================

    risk_explanation = generate_risk_explanation(

        verification_score=verification_score,

        similarity_score=similarity_score,

        image_quality=image_info.get(
            "image_quality",
            "Unknown"
        ),

        status=risk_result["status"],

        ml_anomaly_score=ml_result.get(
            "anomaly_score"
        )
    )


    # =====================================================
    # 9. SCORE BREAKDOWN FOR HTML
    # =====================================================

    # OCR score
    verification_component = verification_score


    # Visual similarity
    if similarity_score is not None:

        similarity_component = similarity_score

    else:

        similarity_component = 0


    # ML consistency
    ml_anomaly_score = ml_result.get(
        "anomaly_score"
    )


    if ml_anomaly_score is not None:

        ml_component = max(
            0,
            100 - ml_anomaly_score
        )

    else:

        ml_component = 0


    # Image quality
    image_quality = image_info.get(
        "image_quality",
        "Unknown"
    )


    if image_quality == "Good":

        quality_component = 100

    elif image_quality == "Moderate":

        quality_component = 60

    elif image_quality == "Low":

        quality_component = 30

    else:

        quality_component = 0


    # =====================================================
    # 10. PDF PREVIEW URLs
    # =====================================================

    uploaded_url = (
        "/uploads/"
        + file.filename
    )


    reference_url = None

    reference_filename = None


    if authenticity_info:

        reference_filename = (
            authenticity_info.get(
                "filename"
            )
        )


        if reference_filename:

            reference_url = (
                "/references/"
                + reference_filename
            )


    # =====================================================
    # 11. RENDER RESULT PAGE
    # =====================================================

    return render_template(

        "result.html",

        # -----------------------------------------------
        # Basic
        # -----------------------------------------------

        filename=file.filename,

        text=text,

        # -----------------------------------------------
        # Extracted information
        # -----------------------------------------------

        details=details,

        # -----------------------------------------------
        # Verification
        # -----------------------------------------------

        checks=checks,

        score=verification_score,

        verification_status=verification_status,

        # -----------------------------------------------
        # Overall result
        # -----------------------------------------------

        status=risk_result["status"],

        overall_score=risk_result[
            "overall_score"
        ],

        # -----------------------------------------------
        # Image
        # -----------------------------------------------

        image_info=image_info,

        # -----------------------------------------------
        # Reference comparison
        # -----------------------------------------------

        authenticity_info=authenticity_info,

        # -----------------------------------------------
        # Risk
        # -----------------------------------------------

        quality_score=risk_result[
            "quality_score"
        ],

        risk_explanation=risk_explanation,

        # -----------------------------------------------
        # Machine Learning
        # -----------------------------------------------

        ml_result=ml_result,

        # -----------------------------------------------
        # Score breakdown
        # -----------------------------------------------

        verification_component=verification_component,

        similarity_component=similarity_component,

        ml_component=ml_component,

        quality_component=quality_component,

        # -----------------------------------------------
        # PDF preview
        # -----------------------------------------------

        uploaded_url=uploaded_url,

        reference_url=reference_url,

        reference_filename=reference_filename
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )