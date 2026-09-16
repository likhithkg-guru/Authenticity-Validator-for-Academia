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

UPLOAD_FOLDER = "uploads"
REFERENCE_FOLDER = "reference_documents"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REFERENCE_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload")
def upload():
    return render_template("upload.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    # -----------------------------
    # 1. Check uploaded document
    # -----------------------------

    if "document" not in request.files:
        return "No document uploaded"

    file = request.files["document"]

    if file.filename == "":
        return "No file selected"

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # -----------------------------
    # 2. OCR
    # -----------------------------

    text = extract_text_from_pdf(filepath)

    details = extract_details(text)


    # -----------------------------
    # 3. Basic verification
    # -----------------------------

    checks, verification_score, verification_status = verify_document(
        details,
        text
    )


    # -----------------------------
    # 4. Image analysis
    # -----------------------------

    image_info = analyze_image(filepath)


    # -----------------------------
    # 5. Reference comparison
    # -----------------------------

    authenticity_info = find_best_reference(
        filepath,
        REFERENCE_FOLDER
    )

    similarity_score = None

    if authenticity_info:
        similarity_score = authenticity_info.get("similarity")


    # -----------------------------
    # 6. ML anomaly detection
    # -----------------------------

    ml_result = analyze_with_ml(
        filepath,
        REFERENCE_FOLDER
    )


    # -----------------------------
    # 7. Overall risk score
    # -----------------------------

    risk_result = calculate_risk_score(
        verification_score=verification_score,
        similarity_score=similarity_score,
        image_quality=image_info.get(
            "image_quality",
            "Unknown"
        )
    )


    # -----------------------------
    # 8. Explainable result
    # -----------------------------

    risk_explanation = generate_risk_explanation(
        verification_score=verification_score,
        similarity_score=similarity_score,
        image_quality=image_info.get(
            "image_quality",
            "Unknown"
        ),
        status=risk_result["status"]
    )


    # -----------------------------
    # 9. Send everything to dashboard
    # -----------------------------

    return render_template(
        "result.html",

        filename=file.filename,

        text=text,

        details=details,

        checks=checks,

        score=verification_score,

        verification_status=verification_status,

        status=risk_result["status"],

        image_info=image_info,

        authenticity_info=authenticity_info,

        overall_score=risk_result["overall_score"],

        quality_score=risk_result["quality_score"],

        risk_explanation=risk_explanation,

        # ML information
        ml_result=ml_result
    )


if __name__ == "__main__":
    app.run(debug=True)