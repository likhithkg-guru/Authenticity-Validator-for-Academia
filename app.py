import os
import sqlite3
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    send_file
)

from werkzeug.utils import secure_filename

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from utils.ocr import extract_text_from_pdf
from utils.verifier import extract_details, verify_document
from utils.image_analyzer import analyze_image_quality
from utils.authenticity import find_best_reference
from utils.risk_engine import (
    calculate_risk_score,
    generate_risk_explanation
)
from utils.ml_detector import analyze_with_ml
from utils.tampering_detector import analyze_tampering
from utils.academic_validator import analyze_academic_consistency
from utils.document_classifier import classify_document


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

REFERENCE_FOLDER = os.path.join(
    BASE_DIR,
    "reference_documents"
)

REPORT_FOLDER = os.path.join(
    BASE_DIR,
    "reports"
)

DATABASE = os.path.join(
    BASE_DIR,
    "verification_history.db"
)

ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["REFERENCE_FOLDER"] = REFERENCE_FOLDER
app.config["REPORT_FOLDER"] = REPORT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


# ============================================================
# CREATE FOLDERS
# ============================================================

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    REFERENCE_FOLDER,
    exist_ok=True
)

os.makedirs(
    REPORT_FOLDER,
    exist_ok=True
)


# ============================================================
# DATABASE
# ============================================================

def init_database():

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            document_type TEXT,
            candidate_name TEXT,
            register_number TEXT,
            dob TEXT,
            overall_score REAL,
            status TEXT,
            verification_score REAL,
            similarity_score REAL,
            ml_anomaly_score REAL,
            image_quality TEXT,
            reference_filename TEXT,
            created_at TEXT
        )
        """
    )

    connection.commit()
    connection.close()


init_database()


# ============================================================
# HELPER
# ============================================================

def allowed_file(filename):

    return (
        filename
        and "."
        in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


def safe_float(value, default=0.0):

    try:

        if value is None:
            return float(default)

        if isinstance(value, str):

            value = value.strip()

            if value.endswith("%"):
                value = value[:-1]

            if value == "":
                return float(default)

        return float(value)

    except (
        TypeError,
        ValueError
    ):

        return float(default)


# ============================================================
# NORMALIZE VERIFICATION RESULT
# ============================================================

def normalize_verification_result(result):

    """
    Handles both possible formats from verifier.py.

    Dictionary example:
        {
            "score": 80,
            "status": "LOW RISK",
            "checks": {}
        }

    Tuple example:
        (
            80,
            "LOW RISK",
            {}
        )
    """

    # --------------------------------------------------------
    # DICTIONARY
    # --------------------------------------------------------

    if isinstance(
        result,
        dict
    ):

        score = result.get(
            "score",
            result.get(
                "verification_score",
                0
            )
        )

        status = result.get(
            "status",
            "UNKNOWN"
        )

        checks = result.get(
            "checks",
            {}
        )

        return {
            "score": safe_float(score),
            "status": status,
            "checks": checks
        }

    # --------------------------------------------------------
    # TUPLE / LIST
    # --------------------------------------------------------

    if isinstance(
        result,
        (tuple, list)
    ):

        score = (
            result[0]
            if len(result) > 0
            else 0
        )

        status = (
            result[1]
            if len(result) > 1
            else "UNKNOWN"
        )

        checks = (
            result[2]
            if len(result) > 2
            else {}
        )

        # Sometimes the second value can itself be
        # a dictionary containing status/checks.

        if isinstance(
            status,
            dict
        ):

            status_dict = status

            actual_status = status_dict.get(
                "status",
                "UNKNOWN"
            )

            actual_checks = status_dict.get(
                "checks",
                checks
            )

            status = actual_status
            checks = actual_checks

        return {
            "score": safe_float(score),
            "status": str(status),
            "checks": checks
        }

    # --------------------------------------------------------
    # UNKNOWN FORMAT
    # --------------------------------------------------------

    return {
        "score": 0,
        "status": "UNKNOWN",
        "checks": {}
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# UPLOAD PAGE
# ============================================================

@app.route("/upload")
def upload():

    return render_template(
        "upload.html"
    )


# ============================================================
# SERVE UPLOADED FILE
# ============================================================

@app.route(
    "/uploads/<filename>"
)
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# SERVE REFERENCE FILE
# ============================================================

@app.route(
    "/references/<filename>"
)
def reference_file(filename):

    return send_from_directory(
        app.config["REFERENCE_FOLDER"],
        filename
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    # ========================================================
    # FILE CHECK
    # ========================================================

    if "document" not in request.files:

        return (
            "No document uploaded.",
            400
        )

    file = request.files["document"]

    if file.filename == "":

        return (
            "No document selected.",
            400
        )

    if not allowed_file(
        file.filename
    ):

        return (
            "Only PDF files are allowed.",
            400
        )

    # ========================================================
    # SAVE FILE
    # ========================================================

    original_filename = secure_filename(
        file.filename
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    name, extension = os.path.splitext(
        original_filename
    )

    filename = (
        f"{name}_{timestamp}{extension}"
    )

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    # ========================================================
    # OCR
    # ========================================================

    try:

        text = extract_text_from_pdf(
            filepath
        )

    except Exception as error:

        print(
            "OCR ERROR:",
            error
        )

        text = ""

    # ========================================================
    # DOCUMENT CLASSIFICATION
    # ========================================================

    try:

        document_result = classify_document(
            text
        )

    except Exception as error:

        print(
            "DOCUMENT CLASSIFIER ERROR:",
            error
        )

        document_result = {
            "document_type": "UNKNOWN",
            "confidence": 0,
            "scores": {},
            "matched_keywords": []
        }

    document_type = document_result.get(
        "document_type",
        "UNKNOWN"
    )

    document_confidence = safe_float(
        document_result.get(
            "confidence",
            0
        )
    )

    # ========================================================
    # EXTRACT DETAILS
    # ========================================================

    try:

        details = extract_details(
            text
        )

    except Exception as error:

        print(
            "DETAIL EXTRACTION ERROR:",
            error
        )

        details = {
            "candidate_name": "Not detected",
            "register_number": "Not detected",
            "date_of_birth": "Not detected"
        }

    candidate_name = details.get(
        "candidate_name",
        "Not detected"
    )

    register_number = details.get(
        "register_number",
        "Not detected"
    )

    dob = details.get(
        "date_of_birth",
        details.get(
            "dob",
            "Not detected"
        )
    )

    # ========================================================
    # BASIC VERIFICATION
    # ========================================================

    try:

        raw_verification = verify_document(
            details,
            text
        )

        verification = normalize_verification_result(
            raw_verification
        )

    except Exception as error:

        print(
            "VERIFICATION ERROR:",
            error
        )

        verification = {
            "score": 0,
            "status": "SUSPICIOUS",
            "checks": {}
        }

    verification_score = safe_float(
        verification.get(
            "score",
            0
        )
    )

    verification_status = verification.get(
        "status",
        "UNKNOWN"
    )

    verification_checks = verification.get(
        "checks",
        {}
    )

    # ========================================================
    # IMAGE QUALITY
    # ========================================================

    try:

        image_info = analyze_image_quality(
            filepath
        )

    except Exception as error:

        print(
            "IMAGE ANALYSIS ERROR:",
            error
        )

        image_info = {
            "image_quality": "Unknown",
            "blur_score": 0,
            "width": 0,
            "height": 0
        }

    image_quality = image_info.get(
        "image_quality",
        "Unknown"
    )

    # ========================================================
    # REFERENCE COMPARISON
    # ========================================================

    try:

        reference_result = find_best_reference(
            filepath,
            app.config["REFERENCE_FOLDER"]
        )

        # Expected:
        # filename, similarity, status

        if isinstance(
            reference_result,
            (tuple, list)
        ):

            reference_filename = (
                reference_result[0]
                if len(reference_result) > 0
                else None
            )

            similarity_score = (
                reference_result[1]
                if len(reference_result) > 1
                else 0
            )

            similarity_status = (
                reference_result[2]
                if len(reference_result) > 2
                else "UNAVAILABLE"
            )

        elif isinstance(
            reference_result,
            dict
        ):

            reference_filename = reference_result.get(
                "filename",
                reference_result.get(
                    "reference_filename"
                )
            )

            similarity_score = reference_result.get(
                "similarity",
                reference_result.get(
                    "similarity_score",
                    0
                )
            )

            similarity_status = reference_result.get(
                "status",
                "UNAVAILABLE"
            )

        else:

            reference_filename = None
            similarity_score = 0
            similarity_status = "UNAVAILABLE"

    except Exception as error:

        print(
            "REFERENCE ERROR:",
            error
        )

        reference_filename = None
        similarity_score = 0
        similarity_status = "UNAVAILABLE"

    similarity_score = safe_float(
        similarity_score
    )

    # ========================================================
    # ML ANALYSIS
    # ========================================================

    try:

        ml_result = analyze_with_ml(
            filepath,
            app.config["REFERENCE_FOLDER"]
        )

    except Exception as error:

        print(
            "ML ERROR:",
            error
        )

        ml_result = {
            "available": False,
            "anomaly_score": 0,
            "prediction": 0,
            "status": "UNAVAILABLE",
            "reference_count": 0,
            "explanation": (
                "ML analysis could not be completed."
            )
        }

    ml_anomaly_score = safe_float(
        ml_result.get(
            "anomaly_score",
            0
        )
    )

    # ========================================================
    # TAMPERING ANALYSIS
    # ========================================================

    try:

        tampering_result = analyze_tampering(
            filepath
        )

    except Exception as error:

        print(
            "TAMPERING ERROR:",
            error
        )

        tampering_result = {
            "available": False,
            "status": "UNAVAILABLE",
            "tampering_score": 0,
            "suspicious_regions": 0,
            "total_regions": 0,
            "texture_mean": 0,
            "texture_std": 0,
            "edge_density": 0,
            "indicators": [],
            "explanation": (
                "Tampering analysis could not be completed."
            )
        }

    # ========================================================
    # ACADEMIC CONSISTENCY
    # ========================================================

    try:

        academic_result = analyze_academic_consistency(
            text
        )

    except Exception as error:

        print(
            "ACADEMIC VALIDATION ERROR:",
            error
        )

        academic_result = {
            "available": False,
            "status": "UNAVAILABLE",
            "overall_score": 0,
            "suspicious_count": 0,
            "checks": {},
            "suspicious_indicators": [],
            "explanation": (
                "Academic consistency analysis "
                "could not be completed."
            )
        }

    # ========================================================
    # RISK SCORE
    # ========================================================

    try:

        risk_result = calculate_risk_score(
            verification_score=verification_score,
            similarity_score=similarity_score,
            image_quality=image_quality,
            ml_anomaly_score=ml_anomaly_score
        )

    except Exception as error:

        print(
            "RISK ENGINE ERROR:",
            error
        )

        risk_result = {
            "overall_score": 0,
            "status": "SUSPICIOUS",
            "verification_score": verification_score,
            "similarity_score": similarity_score,
            "image_quality_score": 0,
            "ml_anomaly_score": ml_anomaly_score,
            "ml_consistency_score": (
                100 - ml_anomaly_score
            ),
            "components": {},
            "weights": {}
        }

    overall_score = safe_float(
        risk_result.get(
            "overall_score",
            0
        )
    )

    status = risk_result.get(
        "status",
        "SUSPICIOUS"
    )

    # ========================================================
    # RISK EXPLANATION
    # ========================================================

    try:

        risk_explanation = generate_risk_explanation(
            verification_score=verification_score,
            similarity_score=similarity_score,
            image_quality=image_quality,
            ml_anomaly_score=ml_anomaly_score
        )

    except Exception as error:

        print(
            "RISK EXPLANATION ERROR:",
            error
        )

        risk_explanation = (
            "Risk explanation could not be generated."
        )

    # ========================================================
    # SCORE COMPONENTS
    # ========================================================

    score_components = {

        "Verification":
            verification_score,

        "Reference Similarity":
            similarity_score,

        "ML Consistency":
            round(
                100 - ml_anomaly_score,
                2
            ),

        "Image Quality":
            safe_float(
                risk_result.get(
                    "image_quality_score",
                    0
                )
            )
    }

    # ========================================================
    # DATABASE HISTORY
    # ========================================================

    try:

        connection = sqlite3.connect(
            DATABASE
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO verification_history (
                filename,
                document_type,
                candidate_name,
                register_number,
                dob,
                overall_score,
                status,
                verification_score,
                similarity_score,
                ml_anomaly_score,
                image_quality,
                reference_filename,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                document_type,
                candidate_name,
                register_number,
                dob,
                overall_score,
                status,
                verification_score,
                similarity_score,
                ml_anomaly_score,
                image_quality,
                reference_filename
                if reference_filename
                else "Not available",
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        connection.commit()
        connection.close()

    except Exception as error:

        print(
            "DATABASE ERROR:",
            error
        )

    # ========================================================
    # RESULT PAGE
    # ========================================================

    return render_template(
        "result.html",

        filename=filename,

        # OCR
        ocr_text=text,

        # Document classification
        document_result=document_result,
        document_type=document_type,
        document_confidence=document_confidence,

        # Details
        details=details,
        candidate_name=candidate_name,
        register_number=register_number,
        dob=dob,

        # Verification
        verification=verification,
        verification_score=verification_score,
        verification_status=verification_status,
        verification_checks=verification_checks,

        # Image
        image_info=image_info,
        image_quality=image_quality,

        # Reference
        reference_filename=reference_filename,
        similarity_score=similarity_score,
        similarity_status=similarity_status,

        # ML
        ml_result=ml_result,
        ml_anomaly_score=ml_anomaly_score,

        # Tampering
        tampering_result=tampering_result,

        # Academic
        academic_result=academic_result,

        # Risk
        risk_result=risk_result,
        overall_score=overall_score,
        status=status,
        risk_explanation=risk_explanation,

        # Score components
        score_components=score_components
    )


# ============================================================
# HISTORY
# ============================================================

@app.route("/history")
def history():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM verification_history
        ORDER BY id DESC
        """
    )

    records = cursor.fetchall()

    connection.close()

    return render_template(
        "history.html",
        records=records
    )


# ============================================================
# DOWNLOAD REPORT
# ============================================================

@app.route("/download-report")
def download_report():

    filename = request.args.get(
        "filename",
        "document"
    )

    candidate_name = request.args.get(
        "candidate_name",
        "Not detected"
    )

    register_number = request.args.get(
        "register_number",
        "Not detected"
    )

    dob = request.args.get(
        "dob",
        "Not detected"
    )

    document_type = request.args.get(
        "document_type",
        "Not detected"
    )

    overall_score = request.args.get(
        "overall_score",
        "0"
    )

    status = request.args.get(
        "status",
        "UNKNOWN"
    )

    verification_score = request.args.get(
        "verification_score",
        "0"
    )

    similarity = request.args.get(
        "similarity",
        "0"
    )

    ml_score = request.args.get(
        "ml_score",
        "0"
    )

    image_quality = request.args.get(
        "image_quality",
        "Unknown"
    )

    reference = request.args.get(
        "reference",
        "Not available"
    )

    # ========================================================
    # REPORT NAME
    # ========================================================

    report_name = (
        os.path.splitext(
            secure_filename(filename)
        )[0]
        + "_verification_report.pdf"
    )

    report_path = os.path.join(
        app.config["REPORT_FOLDER"],
        report_name
    )

    # ========================================================
    # CREATE PDF
    # ========================================================

    pdf = canvas.Canvas(
        report_path,
        pagesize=A4
    )

    width, height = A4

    y = height - 60

    # ========================================================
    # TITLE
    # ========================================================

    pdf.setFont(
        "Helvetica-Bold",
        20
    )

    pdf.drawString(
        50,
        y,
        "Academic Document Verification Report"
    )

    y -= 35

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        50,
        y,
        "Authenticity Validator for Academia"
    )

    y -= 35

    # ========================================================
    # DOCUMENT INFORMATION
    # ========================================================

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        y,
        "Document Information"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
        10
    )

    document_information = [

        (
            "File Name",
            filename
        ),

        (
            "Candidate Name",
            candidate_name
        ),

        (
            "Register Number",
            register_number
        ),

        (
            "Date of Birth",
            dob
        ),

        (
            "Document Type",
            document_type
        ),

        (
            "Reference Document",
            reference
        )
    ]

    for label, value in document_information:

        pdf.drawString(
            60,
            y,
            f"{label}: {value}"
        )

        y -= 18

    # ========================================================
    # RESULTS
    # ========================================================

    y -= 15

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        y,
        "Verification Results"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
        10
    )

    verification_results = [

        (
            "Overall Score",
            f"{overall_score}%"
        ),

        (
            "Final Status",
            status
        ),

        (
            "Verification Score",
            f"{verification_score}%"
        ),

        (
            "Reference Similarity",
            f"{similarity}%"
        ),

        (
            "ML Anomaly Score",
            f"{ml_score}%"
        ),

        (
            "Image Quality",
            image_quality
        )
    ]

    for label, value in verification_results:

        pdf.drawString(
            60,
            y,
            f"{label}: {value}"
        )

        y -= 18

    # ========================================================
    # DISCLAIMER
    # ========================================================

    y -= 20

    pdf.setFont(
        "Helvetica-Bold",
        11
    )

    pdf.drawString(
        50,
        y,
        "Important Note"
    )

    y -= 20

    pdf.setFont(
        "Helvetica",
        8
    )

    disclaimer_lines = [

        "This system provides automated screening based on OCR,",

        "document structure, visual similarity, image quality,",

        "academic consistency and reference-based pattern analysis.",

        "",

        "An anomaly or suspicious result does not by itself prove",

        "that a document is fake or altered. Manual verification",

        "by the relevant educational institution is recommended."
    ]

    for line in disclaimer_lines:

        pdf.drawString(
            60,
            y,
            line
        )

        y -= 13

    # ========================================================
    # GENERATED DATE
    # ========================================================

    y -= 15

    pdf.setFont(
        "Helvetica",
        8
    )

    pdf.drawString(
        50,
        y,
        "Generated: "
        + datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    pdf.save()

    return send_file(
        report_path,
        as_attachment=True,
        download_name=report_name,
        mimetype="application/pdf"
    )


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return (
        "File is too large. Maximum allowed size is 20 MB.",
        413
    )


@app.errorhandler(404)
def page_not_found(error):

    return (
        "Page not found.",
        404
    )


@app.errorhandler(500)
def internal_server_error(error):

    return (
        "An internal server error occurred.",
        500
    )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("AUTHENTICITY VALIDATOR FOR ACADEMIA")
    print("=" * 60)

    print(
        "Project folder:",
        BASE_DIR
    )

    print(
        "Upload folder:",
        UPLOAD_FOLDER
    )

    print(
        "Reference folder:",
        REFERENCE_FOLDER
    )

    print(
        "Database:",
        DATABASE
    )

    print(
        "Server: http://127.0.0.1:5000"
    )

    print("=" * 60)

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )