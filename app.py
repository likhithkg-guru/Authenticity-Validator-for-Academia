from flask import Flask, render_template, request
import os

from utils.ocr import extract_text_from_pdf
from utils.image_analyzer import analyze_image
from utils.verifier import extract_details, verify_document


app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- UPLOAD PAGE ----------------

@app.route("/upload")
def upload():
    return render_template("upload.html")


# ---------------- ANALYZE DOCUMENT ----------------

@app.route("/analyze", methods=["POST"])
def analyze():

    # Check whether file exists
    if "document" not in request.files:
        return "No document uploaded"

    file = request.files["document"]

    # Check whether a file was selected
    if file.filename == "":
        return "No file selected"

    # Save uploaded file
    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # ---------------- IMAGE ANALYSIS ----------------

    image_result = analyze_image(filepath)


    # ---------------- OCR ----------------

    # Extract text from PDF
    text = extract_text_from_pdf(filepath)


    # ---------------- EXTRACT DETAILS ----------------

    details = extract_details(text)


    # ---------------- VERIFY DOCUMENT ----------------

    checks, score, status = verify_document(
        details,
        text
    )


    # ---------------- RESULT PAGE ----------------

    return render_template(
        "result.html",

        # File information
        filename=file.filename,

        # Verification information
        checks=checks,
        score=score,
        status=status,

        # Image analysis information
        image_quality=image_result["image_quality"],
        blur_score=image_result["blur_score"],
        width=image_result["width"],
        height=image_result["height"]
    )


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    app.run(debug=True)