from flask import Flask, render_template, request
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
# HOME PAGE
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
# ANALYZE DOCUMENT
# =========================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    # -----------------------------------------------------
    # 1. Check whether file was uploaded
    # -----------------------------------------------------

    if "document" not in request.files:
        return "No document uploaded"

    file = request.files["document"]

    if file.filename == "":
        return "No file selected"


    # -----------------------------------------------------
    # 2. Save uploaded document
    # -----------------------------------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # -----------------------------------------------------
    # 3. OCR TEXT EXTRACTION
    # -----------------------------------------------------

    text = extract_text_from_pdf(filepath)


    # -----------------------------------------------------
    # 4. EXTRACT IMPORTANT DETAILS
    # -----------------------------------------------------

    details = extract_details(text)


    # -----------------------------------------------------
    # 5. BASIC DOCUMENT VERIFICATION
    # -----------------------------------------------------

    checks, verification_score, verification_status = verify_document(
        details,
        text
    )


    # -----------------------------------------------------
    # 6. IMAGE QUALITY ANALYSIS
    # -----------------------------------------------------

    image_info = analyze_image(filepath)


    # -----------------------------------------------------
    # 7. REFERENCE DOCUMENT COMPARISON
    # -----------------------------------------------------

    authenticity_info = find_best_reference(
        filepath,
        REFERENCE_FOLDER
    )

    similarity_score = None

    if authenticity_info:
        similarity_score = authenticity_info.get(
            "similarity"
        )


    # -----------------------------------------------------
    # 8. MACHINE LEARNING ANALYSIS
    # -----------------------------------------------------

    ml_result = analyze_with_ml(
        filepath,
        REFERENCE_FOLDER
    )


    # -----------------------------------------------------
    # 9. OVERALL RISK SCORE
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 10. RISK EXPLANATION
    # -----------------------------------------------------

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
    # 11. SCORE BREAKDOWN
    # =====================================================

    # OCR verification component
    verification_component = verification_score


    # Visual similarity component
    if similarity_score is not None:
        similarity_component = similarity_score
    else:
        similarity_component = 0


    # ML component
    #
    # ML anomaly score:
    # 0   = very little deviation
    # 100 = high deviation
    #
    # Therefore we convert it into a positive
    # consistency score.
    
    if ml_result.get("anomaly_score") is not None:

        ml_component = (
            100 - ml_result.get("anomaly_score")
        )

    else:

        ml_component = 0


    # Make sure ML component stays between 0 and 100
    ml_component = max(
        0,
        min(
            100,
            ml_component
        )
    )


    # Image quality component
    quality_component = risk_result["quality_score"]


    # =====================================================
    # 12. SEND EVERYTHING TO RESULT PAGE
    # =====================================================

    return render_template(

        "result.html",

        # -------------------------------------------------
        # Basic information
        # -------------------------------------------------

        filename=file.filename,

        text=text,


        # -------------------------------------------------
        # Extracted information
        # -------------------------------------------------

        details=details,


        # -------------------------------------------------
        # Verification
        # -------------------------------------------------

        checks=checks,

        score=verification_score,

        verification_status=verification_status,


        # -------------------------------------------------
        # Overall risk
        # -------------------------------------------------

        status=risk_result["status"],

        overall_score=risk_result["overall_score"],

        quality_score=risk_result["quality_score"],


        # -------------------------------------------------
        # Image analysis
        # -------------------------------------------------

        image_info=image_info,


        # -------------------------------------------------
        # Reference comparison
        # -------------------------------------------------

        authenticity_info=authenticity_info,


        # -------------------------------------------------
        # ML analysis
        # -------------------------------------------------

        ml_result=ml_result,


        # -------------------------------------------------
        # Score breakdown
        # -------------------------------------------------

        verification_component=verification_component,

        similarity_component=similarity_component,

        ml_component=ml_component,

        quality_component=quality_component,


        # -------------------------------------------------
        # Explanation
        # -------------------------------------------------

        risk_explanation=risk_explanation
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)