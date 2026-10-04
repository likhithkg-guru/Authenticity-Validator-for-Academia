from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    make_response
)

import os
import sqlite3
from datetime import datetime

from utils.ocr import extract_text_from_pdf
from utils.verifier import verify_document
from utils.image_analyzer import analyze_image_quality
from utils.authenticity import find_best_reference
from utils.risk_engine import calculate_risk_score, generate_risk_explanation
from utils.ml_detector import analyze_with_ml
from utils.tampering_detector import analyze_tampering
from utils.academic_validator import analyze_academic_consistency
from utils.document_classifier import classify_document


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
REFERENCE_FOLDER = os.path.join(BASE_DIR, "reference_documents")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")

DATABASE = os.path.join(BASE_DIR, "verification_history.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REFERENCE_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================================================
# DATABASE
# ============================================================

def init_db():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            candidate_name TEXT,
            register_number TEXT,
            dob TEXT,
            document_type TEXT,
            overall_score REAL,
            status TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# HELPERS
# ============================================================

def normalize_verification_result(result):

    """
    Makes verifier output compatible with the application.

    New verifier returns a dictionary.
    Older versions may return tuple/list.
    """

    if isinstance(result, dict):
        return result

    if isinstance(result, (tuple, list)):

        if len(result) >= 2:

            first = result[0]
            second = result[1]

            if isinstance(first, dict):
                data = first.copy()

                if "score" not in data:
                    data["score"] = second

                if "verification_score" not in data:
                    data["verification_score"] = second

                return data

    return {
        "available": False,
        "status": "INSUFFICIENT INFORMATION",
        "score": 0,
        "verification_score": 0,
        "details": {},
        "checks": {},
        "verification_checks": {},
        "suspicious_count": 0,
        "suspicious_indicators": [],
        "explanation": "Verification module did not return a valid result."
    }


def safe_float(value, default=0.0):

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template("index.html")


# ============================================================
# UPLOAD PAGE
# ============================================================

@app.route("/upload")
def upload():

    return render_template("upload.html")


# ============================================================
# SERVE UPLOADED FILES
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# ============================================================
# SERVE REFERENCE DOCUMENTS
# ============================================================

@app.route("/references/<filename>")
def reference_file(filename):

    return send_from_directory(
        REFERENCE_FOLDER,
        filename
    )


# ============================================================
# ANALYZE DOCUMENT
# ============================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    # --------------------------------------------------------
    # CHECK FILE
    # --------------------------------------------------------

    if "document" not in request.files:

        return redirect(url_for("upload"))

    file = request.files["document"]

    if file.filename == "":

        return redirect(url_for("upload"))

    # --------------------------------------------------------
    # SAVE FILE
    # --------------------------------------------------------

    original_filename = file.filename

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    name, extension = os.path.splitext(original_filename)

    filename = f"{name}_{timestamp}{extension}"

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    file.save(filepath)

    # --------------------------------------------------------
    # OCR
    # --------------------------------------------------------

    try:

        ocr_text = extract_text_from_pdf(filepath)

    except Exception as e:

        ocr_text = ""

        print("OCR ERROR:", e)

    # --------------------------------------------------------
    # DOCUMENT CLASSIFICATION
    # --------------------------------------------------------

    try:

        classification = classify_document(ocr_text)

    except Exception as e:

        print("CLASSIFICATION ERROR:", e)

        classification = {
            "document_type": "UNKNOWN",
            "confidence": 0,
            "evidence": []
        }

    document_type = classification.get(
        "document_type",
        "UNKNOWN"
    )

    document_confidence = safe_float(
        classification.get("confidence", 0)
    )

    classification_evidence = classification.get(
        "evidence",
        []
    )

    # --------------------------------------------------------
    # INFORMATION VERIFICATION
    # --------------------------------------------------------

    try:

        raw_verification = verify_document(
            ocr_text
        )

        verification = normalize_verification_result(
            raw_verification
        )

    except Exception as e:

        print("VERIFICATION ERROR:", e)

        verification = {
            "available": False,
            "status": "INSUFFICIENT INFORMATION",
            "score": 0,
            "verification_score": 0,
            "details": {},
            "checks": {},
            "verification_checks": {},
            "suspicious_count": 0,
            "suspicious_indicators": [],
            "explanation": str(e)
        }

    # --------------------------------------------------------
    # EXTRACTED DETAILS
    # --------------------------------------------------------

    details = verification.get(
        "details",
        {}
    )

    # Safety fallback
    if not isinstance(details, dict):
        details = {}

    candidate_name = details.get(
        "candidate_name",
        verification.get(
            "candidate_name",
            "Not detected"
        )
    )

    register_number = details.get(
        "register_number",
        verification.get(
            "register_number",
            "Not detected"
        )
    )

    dob = details.get(
        "date_of_birth",
        details.get(
            "dob",
            verification.get(
                "date_of_birth",
                "Not detected"
            )
        )
    )

    # --------------------------------------------------------
    # VERIFICATION SCORE
    # --------------------------------------------------------

    verification_score = safe_float(
        verification.get(
            "verification_score",
            verification.get(
                "score",
                0
            )
        )
    )

    # --------------------------------------------------------
    # VERIFICATION CHECKS
    # --------------------------------------------------------

    verification_checks = verification.get(
        "verification_checks",
        verification.get(
            "checks",
            {}
        )
    )

    if not isinstance(verification_checks, dict):

        verification_checks = {}

    # --------------------------------------------------------
    # IMAGE QUALITY
    # --------------------------------------------------------

    try:

        image_info = analyze_image_quality(
            filepath
        )

    except Exception as e:

        print("IMAGE QUALITY ERROR:", e)

        image_info = {
            "image_quality": "Unknown",
            "blur_score": 0,
            "width": 0,
            "height": 0
        }

    # --------------------------------------------------------
    # REFERENCE COMPARISON
    # --------------------------------------------------------

    try:

        reference_result = find_best_reference(
            filepath,
            REFERENCE_FOLDER
        )

    except Exception as e:

        print("REFERENCE ERROR:", e)

        reference_result = {}

    reference_filename = None
    similarity_score = 0.0

    if isinstance(reference_result, dict):

        reference_filename = reference_result.get(
            "reference_filename",
            reference_result.get(
                "filename"
            )
        )

        similarity_score = safe_float(
            reference_result.get(
                "similarity",
                reference_result.get(
                    "similarity_score",
                    0
                )
            )
        )

    elif isinstance(reference_result, (tuple, list)):

        if len(reference_result) >= 2:

            reference_filename = reference_result[0]

            similarity_score = safe_float(
                reference_result[1]
            )

    # --------------------------------------------------------
    # ML ANALYSIS
    # --------------------------------------------------------

    try:

        ml_result = analyze_with_ml(
            filepath,
            REFERENCE_FOLDER
        )

    except Exception as e:

        print("ML ERROR:", e)

        ml_result = {
            "available": False,
            "status": "UNAVAILABLE",
            "anomaly_score": 0,
            "reference_count": 0,
            "explanation": "ML analysis unavailable."
        }

    if not isinstance(ml_result, dict):

        ml_result = {
            "available": False,
            "status": "UNAVAILABLE",
            "anomaly_score": 0,
            "reference_count": 0,
            "explanation": "Invalid ML result."
        }

    ml_anomaly = safe_float(
        ml_result.get(
            "anomaly_score",
            ml_result.get(
                "score",
                0
            )
        )
    )

    # --------------------------------------------------------
    # TAMPERING ANALYSIS
    # --------------------------------------------------------

    try:

        tampering_result = analyze_tampering(
            filepath
        )

    except Exception as e:

        print("TAMPERING ERROR:", e)

        tampering_result = {
            "available": False,
            "status": "UNAVAILABLE",
            "tampering_score": 0,
            "suspicious_regions": 0,
            "total_regions": 0,
            "explanation": "Tampering analysis unavailable."
        }

    # --------------------------------------------------------
    # ACADEMIC CONSISTENCY
    # --------------------------------------------------------

    try:

        academic_result = analyze_academic_consistency(
            ocr_text
        )

    except Exception as e:

        print("ACADEMIC VALIDATION ERROR:", e)

        academic_result = {
            "available": False,
            "status": "UNAVAILABLE",
            "overall_score": 0,
            "suspicious_count": 0,
            "checks": {},
            "suspicious_indicators": [],
            "explanation": "Academic consistency analysis unavailable."
        }

    # --------------------------------------------------------
    # RISK SCORE
    # --------------------------------------------------------

    image_quality = image_info.get(
        "image_quality",
        "Unknown"
    )

    quality_score = 0

    if image_quality == "Good":
        quality_score = 100

    elif image_quality == "Moderate":
        quality_score = 70

    elif image_quality == "Low":
        quality_score = 40

    # --------------------------------------------------------
    # CALCULATE OVERALL SCORE
    # --------------------------------------------------------

    try:

        overall_score = calculate_risk_score(
            verification_score,
            similarity_score,
            ml_anomaly,
            quality_score
        )

    except Exception as e:

        print("RISK SCORE ERROR:", e)

        overall_score = 0

    overall_score = round(
        safe_float(overall_score),
        2
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    if overall_score >= 80:

        status = "LOW RISK"

    elif overall_score >= 60:

        status = "NEEDS REVIEW"

    else:

        status = "SUSPICIOUS"

    # --------------------------------------------------------
    # RISK EXPLANATION
    # --------------------------------------------------------

    try:

        risk_explanation = generate_risk_explanation(
            verification_score,
            similarity_score,
            ml_anomaly,
            image_quality
        )

    except Exception:

        risk_explanation = (
            "Automated analysis completed. "
            "Manual verification is recommended."
        )

    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    try:

        conn = sqlite3.connect(DATABASE)

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO verification_history
            (
                filename,
                candidate_name,
                register_number,
                dob,
                document_type,
                overall_score,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            candidate_name,
            register_number,
            dob,
            document_type,
            overall_score,
            status,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        conn.commit()
        conn.close()

    except Exception as e:

        print("DATABASE ERROR:", e)

    # --------------------------------------------------------
    # PREVIEW URL
    # --------------------------------------------------------

    uploaded_preview_url = url_for(
        "uploaded_file",
        filename=filename
    )

    # --------------------------------------------------------
    # RESULT PAGE
    # --------------------------------------------------------

    return render_template(
        "result.html",

        overall_score=overall_score,

        status=status,

        document_type=document_type,

        document_confidence=document_confidence,

        classification_evidence=classification_evidence,

        verification_score=verification_score,

        similarity_score=similarity_score,

        ml_result=ml_result,

        image_info=image_info,

        details=details,

        filename=filename,

        verification_checks=verification_checks,

        academic_result=academic_result,

        tampering_result=tampering_result,

        risk_explanation=risk_explanation,

        ocr_text=ocr_text,

        reference_filename=reference_filename,

        uploaded_preview_url=uploaded_preview_url
    )


# ============================================================
# HISTORY
# ============================================================

@app.route("/history")
def history():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM verification_history
        ORDER BY id DESC
    """)

    records = cursor.fetchall()

    conn.close()

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
        "document.pdf"
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

    document_type = request.args.get(
        "document_type",
        "Unknown"
    )

    try:

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm

        response = make_response()

        response.headers["Content-Type"] = "application/pdf"

        response.headers[
            "Content-Disposition"
        ] = (
            f'attachment; filename="verification_report.pdf"'
        )

        c = canvas.Canvas(
            response,
            pagesize=A4
        )

        width, height = A4

        y = height - 30 * mm

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        c.setFont(
            "Helvetica-Bold",
            18
        )

        c.drawString(
            20 * mm,
            y,
            "Academic Document Verification Report"
        )

        y -= 15 * mm

        c.setFont(
            "Helvetica",
            11
        )

        # ----------------------------------------------------
        # DETAILS
        # ----------------------------------------------------

        report_data = [

            ("Document", filename),

            ("Document Type", document_type),

            ("Candidate Name", candidate_name),

            ("Register Number", register_number),

            ("Date of Birth", dob),

            ("Overall Score", f"{overall_score}%"),

            ("Status", status),

            ("OCR Verification", f"{verification_score}%"),

            ("Visual Similarity", f"{similarity}%"),

            ("ML Pattern Deviation", f"{ml_score}%"),

            ("Image Quality", image_quality),

            ("Reference", reference),
        ]

        for label, value in report_data:

            c.setFont(
                "Helvetica-Bold",
                10
            )

            c.drawString(
                20 * mm,
                y,
                label + ":"
            )

            c.setFont(
                "Helvetica",
                10
            )

            c.drawString(
                65 * mm,
                y,
                str(value)
            )

            y -= 8 * mm

            if y < 25 * mm:

                c.showPage()

                y = height - 25 * mm

                c.setFont(
                    "Helvetica",
                    10
                )

        # ----------------------------------------------------
        # DISCLAIMER
        # ----------------------------------------------------

        y -= 5 * mm

        c.setFont(
            "Helvetica-Bold",
            11
        )

        c.drawString(
            20 * mm,
            y,
            "Disclaimer"
        )

        y -= 8 * mm

        c.setFont(
            "Helvetica",
            9
        )

        disclaimer = (
            "This report is an automated screening result. "
            "It does not independently prove that a document "
            "is genuine or fraudulent. Final verification "
            "should be performed through the appropriate "
            "educational institution or authorized system."
        )

        # Wrap text
        words = disclaimer.split()

        line = ""

        for word in words:

            test_line = line + " " + word

            if len(test_line) > 90:

                c.drawString(
                    20 * mm,
                    y,
                    line.strip()
                )

                y -= 5 * mm

                line = word

            else:

                line = test_line

        if line:

            c.drawString(
                20 * mm,
                y,
                line.strip()
            )

        c.save()

        return response

    except Exception as e:

        return f"Could not generate report: {e}", 500


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )