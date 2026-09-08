from flask import Flask, render_template, request
import os

from utils.ocr import extract_text_from_pdf, extract_details
from utils.verifier import verify_document

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload")
def upload():
    return render_template("upload.html")


@app.route("/analyze", methods=["POST"])
def analyze():

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

    # Extract text from PDF
    text = extract_text_from_pdf(filepath)

    # Extract important details
    details = extract_details(text)
    checks, score, status = verify_document(details, text)
    return render_template(
        "result.html",
        filename=file.filename,
        details=details,
        extracted_text=text,
        checks = checks,
        score = score,
        status = status
    )


if __name__ == "__main__":
    app.run(debug=True)