from flask import (
    Flask,
    render_template,
    request,
    send_from_directory
)

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
# SERVE UPLOADED DOCUMENT
# =========================================================

@app.route("/uploaded/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# =========================================================
# SERVE REFERENCE DOCUMENT
# =========================================================

@app.route("/reference/<filename>")
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
    # 1. Check upload
    # -----------------------------------------------------

    if "document" not in request.files:
        return "No document uploaded"

    file = request.files["document"]

    if file.filename == "":
        return "No file selected"


    # -----------------------------------------------------
    # 2. Save document
    # -----------------------------------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # -----------------------------------------------------
    # 3. OCR
    # -----------------------------------------------------

    text = extract_text_from_pdf(filepath)


    # -----------------------------------------------------
    # 4. Extract details
    # -----------------------------------------------------

    details = extract_details(text)


    # -----------------------------------------------------
    # 5. Verification
    # -----------------------------------------------------

    checks, verification_score, verification_status = (
        verify_document(
            details,
            text
        )
    )


    # -----------------------------------------------------
    # 6. Image quality
    # -----------------------------------------------------

    image_info = analyze_image(filepath)


    # -----------------------------------------------------
    # 7. Reference comparison
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
    # 8. Machine learning
    # -----------------------------------------------------

    ml_result = analyze_with_ml(
        filepath,
        REFERENCE_FOLDER
    )


    # -----------------------------------------------------
    # 9. Overall risk
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
    # 10. Risk explanation
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
    # SCORE BREAKDOWN
    # =====================================================

    verification_component = verification_score


    if similarity_score is not None:
        similarity_component = similarity_score
    else:
        similarity_component = 0


    if ml_result.get("anomaly_score") is not None:

        ml_component = (
            100 -
            ml_result.get("anomaly_score")
        )

    else:

        ml_component = 0


    ml_component = max(
        0,
        min(
            100,
            ml_component
        )
    )


    quality_component = risk_result[
        "quality_score"
    ]


    # =====================================================
    # REFERENCE URL
    # =====================================================

    reference_filename = None
    reference_url = None

    if authenticity_info:

        reference_filename = authenticity_info.get(
            "filename"
        )

        if reference_filename:

            reference_url = (
                "/reference/" +
                reference_filename
            )


    # =====================================================
    # UPLOADED DOCUMENT URL
    # =====================================================

    uploaded_url = (
        "/uploaded/" +
        file.filename
    )


    # =====================================================
    # RESULT PAGE
    # =====================================================

    return render_template(

        "result.html",

        # Basic
        filename=file.filename,
        uploaded_url=uploaded_url,

        # OCR
        text=text,

        # Extracted details
        details=details,

        # Verification
        checks=checks,
        score=verification_score,
        verification_status=verification_status,

        # Overall
        status=risk_result["status"],
        overall_score=risk_result["overall_score"],
        quality_score=risk_result["quality_score"],

        # Score components
        verification_component=verification_component,
        similarity_component=similarity_component,
        ml_component=ml_component,
        quality_component=quality_component,

        # Image
        image_info=image_info,

        # Reference
        authenticity_info=authenticity_info,
        reference_filename=reference_filename,
        reference_url=reference_url,

        # ML
        ml_result=ml_result,

        # Explanation
        risk_explanation=risk_explanation
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)