from flask import Flask, render_template, request
import os

from utils.ocr import extract_text_from_pdf
from utils.verifier import extract_details, verify_document
from utils.image_analyzer import analyze_image
from utils.authenticity import find_best_reference


app = Flask(__name__)


# ==========================================
# FOLDERS
# ==========================================

UPLOAD_FOLDER = "uploads"
REFERENCE_FOLDER = "reference_documents"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REFERENCE_FOLDER, exist_ok=True)


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return render_template("index.html")


# ==========================================
# UPLOAD PAGE
# ==========================================

@app.route("/upload")
def upload():

    return render_template("upload.html")


# ==========================================
# ANALYZE DOCUMENT
# ==========================================

@app.route("/analyze", methods=["POST"])
def analyze():

    # --------------------------------------
    # CHECK FILE
    # --------------------------------------

    if "document" not in request.files:

        return "No document uploaded"


    file = request.files["document"]


    if file.filename == "":

        return "No file selected"


    # --------------------------------------
    # SAVE FILE
    # --------------------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # ======================================
    # 1. OCR ANALYSIS
    # ======================================

    text = extract_text_from_pdf(filepath)


    # ======================================
    # 2. EXTRACT DETAILS
    # ======================================

    details = extract_details(text)


    # ======================================
    # 3. DOCUMENT VERIFICATION
    # ======================================

    checks, verification_score, verification_status = verify_document(
        details,
        text
    )


    # ======================================
    # 4. IMAGE ANALYSIS
    # ======================================

    image_info = analyze_image(filepath)


    # ======================================
    # 5. REFERENCE COMPARISON
    # ======================================

    authenticity_info = find_best_reference(
        filepath,
        REFERENCE_FOLDER
    )


    # ======================================
    # 6. IMAGE QUALITY SCORE
    # ======================================

    sharpness = image_info.get(
        "blur_score",
        0
    )


    if sharpness >= 100:

        image_quality_score = 100

    elif sharpness >= 40:

        image_quality_score = 70

    else:

        image_quality_score = 40


    # ======================================
    # 7. VISUAL SIMILARITY SCORE
    # ======================================

    if authenticity_info:

        similarity_score = authenticity_info.get(
            "similarity",
            0
        )

    else:

        similarity_score = 0


    # ======================================
    # 8. MULTI-SIGNAL SCORE
    # ======================================

    overall_score = (

        (verification_score * 0.40)

        +

        (similarity_score * 0.40)

        +

        (image_quality_score * 0.20)

    )


    overall_score = round(
        overall_score,
        2
    )


    # ======================================
    # 9. FINAL STATUS
    # ======================================

    if overall_score >= 90:

        final_status = "LOW RISK"


    elif overall_score >= 70:

        final_status = "NEEDS REVIEW"


    else:

        final_status = "SUSPICIOUS"


    # ======================================
    # 10. RENDER RESULT
    # ======================================

    return render_template(

        "result.html",

        filename=file.filename,

        text=text,

        details=details,

        checks=checks,

        score=verification_score,

        status=final_status,

        image_info=image_info,

        authenticity_info=authenticity_info,

        image_quality_score=image_quality_score,

        similarity_score=similarity_score,

        overall_score=overall_score

    )


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )