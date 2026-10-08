from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    send_file
)

import os
import sqlite3

from utils.ocr import extract_text_from_pdf
from utils.verifier import verify_document
from utils.document_classifier import classify_document
from utils.image_analyzer import analyze_image_quality
from utils.authenticity import find_best_reference

from utils.risk_engine import (
    calculate_risk_score,
    generate_risk_explanation
)

from utils.ml_detector import analyze_with_ml
from utils.tampering_detector import analyze_tampering
from utils.academic_validator import analyze_academic_consistency

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER


# =====================================================
# FLASK APP
# =====================================================

app = Flask(__name__)


UPLOAD_FOLDER = "uploads"
REFERENCE_FOLDER = "reference_documents"
REPORT_FOLDER = "reports"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =====================================================
# CREATE FOLDERS
# =====================================================

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REFERENCE_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)


# =====================================================
# DATABASE
# =====================================================

DATABASE = "verification_history.db"


def init_database():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            filename TEXT,

            candidate_name TEXT,

            register_number TEXT,

            verification_score REAL,

            similarity_score REAL,

            ml_anomaly_score REAL,

            overall_score REAL,

            status TEXT,

            image_quality TEXT,

            reference_filename TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    connection.commit()

    connection.close()


init_database()


# =====================================================
# HOME
# =====================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =====================================================
# UPLOAD PAGE
# =====================================================

@app.route("/upload")
def upload():

    return render_template(
        "upload.html"
    )


# =====================================================
# UPLOADED DOCUMENT
# =====================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =====================================================
# REFERENCE DOCUMENT
# =====================================================

@app.route("/references/<filename>")
def reference_file(filename):

    return send_from_directory(
        REFERENCE_FOLDER,
        filename
    )


# =====================================================
# NORMALIZE VERIFICATION RESULT
# =====================================================

def normalize_verification_result(result):

    """
    Supports both dictionary-style and tuple/list-style
    verification results.
    """

    # -------------------------------------------------
    # DICTIONARY RESULT
    # -------------------------------------------------

    if isinstance(result, dict):

        details = result.get(
            "details",
            {}
        )

        if not isinstance(details, dict):
            details = {}

        checks = result.get(
            "checks",
            result.get(
                "verification_checks",
                {}
            )
        )

        if not isinstance(checks, dict):
            checks = {}

        score = result.get(
            "verification_score",
            result.get(
                "overall_score",
                result.get(
                    "score",
                    0
                )
            )
        )

        try:
            score = float(score)
        except:
            score = 0.0

        return {

            "details": details,

            "checks": checks,

            "score": score,

            "status": result.get(
                "status",
                result.get(
                    "verification_status",
                    "UNKNOWN"
                )
            ),

            "suspicious_count": result.get(
                "suspicious_count",
                0
            ),

            "suspicious_indicators": result.get(
                "suspicious_indicators",
                []
            ),

            "explanation": result.get(
                "explanation",
                ""
            )

        }


    # -------------------------------------------------
    # TUPLE / LIST RESULT
    # -------------------------------------------------

    if isinstance(result, (tuple, list)):

        details = (
            result[0]
            if len(result) > 0
            else {}
        )

        score = (
            result[1]
            if len(result) > 1
            else 0
        )

        status = (
            result[2]
            if len(result) > 2
            else "UNKNOWN"
        )

        checks = {}

        if isinstance(details, dict):

            checks = details.get(
                "checks",
                details.get(
                    "verification_checks",
                    {}
                )
            )

        try:
            score = float(score)
        except:
            score = 0.0

        return {

            "details": (
                details
                if isinstance(details, dict)
                else {}
            ),

            "checks": (
                checks
                if isinstance(checks, dict)
                else {}
            ),

            "score": score,

            "status": status,

            "suspicious_count": 0,

            "suspicious_indicators": [],

            "explanation": ""

        }


    # -------------------------------------------------
    # UNKNOWN RESULT
    # -------------------------------------------------

    return {

        "details": {},

        "checks": {},

        "score": 0.0,

        "status": "UNKNOWN",

        "suspicious_count": 0,

        "suspicious_indicators": [],

        "explanation": ""

    }


# =====================================================
# ANALYZE DOCUMENT
# =====================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    # -------------------------------------------------
    # CHECK FILE
    # -------------------------------------------------

    if "document" not in request.files:

        return "No document uploaded", 400


    file = request.files["document"]


    if file.filename == "":

        return "No file selected", 400


    # -------------------------------------------------
    # SAVE FILE
    # -------------------------------------------------

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    file.save(filepath)


    # =================================================
    # OCR
    # =================================================

    try:

        ocr_text = extract_text_from_pdf(
            filepath
        )

    except Exception as e:

        print(
            "OCR error:",
            e
        )

        ocr_text = ""


    # =================================================
    # DOCUMENT CLASSIFICATION
    # =================================================

    try:

        classification = classify_document(
            ocr_text
        )

    except Exception as e:

        print(
            "Classification error:",
            e
        )

        classification = {

            "document_type": "UNKNOWN",

            "confidence": 0,

            "evidence": []

        }


    if not isinstance(
        classification,
        dict
    ):

        classification = {}


    document_type = classification.get(
        "document_type",
        classification.get(
            "type",
            "UNKNOWN"
        )
    )


    document_confidence = classification.get(
        "confidence",
        classification.get(
            "score",
            0
        )
    )


    classification_evidence = classification.get(
        "evidence",
        classification.get(
            "keywords",
            []
        )
    )


    try:

        document_confidence = float(
            document_confidence
        )

    except:

        document_confidence = 0.0


    # =================================================
    # OCR / INFORMATION VERIFICATION
    # =================================================

    try:

        raw_verification = verify_document(
            ocr_text
        )

    except Exception as e:

        print(
            "Verification error:",
            e
        )

        raw_verification = {}


    verification = normalize_verification_result(
        raw_verification
    )


    details = verification["details"]

    verification_checks = verification["checks"]

    verification_score = verification["score"]


    # -------------------------------------------------
    # PRESERVE DIRECT EXTRACTED FIELDS
    # -------------------------------------------------

    if (
        not details
        and isinstance(
            raw_verification,
            dict
        )
    ):

        details = {

            "candidate_name": raw_verification.get(
                "candidate_name"
            ),

            "register_number": raw_verification.get(
                "register_number"
            ),

            "date_of_birth": raw_verification.get(
                "date_of_birth",
                raw_verification.get(
                    "dob"
                )
            )

        }


    # =================================================
    # IMAGE QUALITY
    # =================================================

    try:

        image_info = analyze_image_quality(
            filepath
        )

    except Exception as e:

        print(
            "Image analysis error:",
            e
        )

        image_info = {

            "image_quality": "Unknown",

            "blur_score": 0,

            "width": 0,

            "height": 0,

            "error": str(e)

        }


    if not isinstance(
        image_info,
        dict
    ):

        image_info = {}


    # =================================================
    # REFERENCE COMPARISON
    # =================================================

    try:

        authenticity_info = find_best_reference(
            filepath,
            REFERENCE_FOLDER
        )

    except Exception as e:

        print(
            "Reference comparison error:",
            e
        )

        authenticity_info = None


    if not isinstance(
        authenticity_info,
        dict
    ):

        authenticity_info = {}


    similarity_score = authenticity_info.get(
        "similarity",
        0
    )


    try:

        similarity_score = float(
            similarity_score
        )

    except:

        similarity_score = 0.0


    similarity_score = max(
        0.0,
        min(
            100.0,
            similarity_score
        )
    )


    reference_filename = authenticity_info.get(
        "filename"
    )


    # =================================================
    # ML ANALYSIS
    # =================================================

    try:

        ml_result = analyze_with_ml(
            filepath,
            REFERENCE_FOLDER
        )

    except Exception as e:

        print(
            "ML analysis error:",
            e
        )

        ml_result = {

            "available": False,

            "anomaly_score": 0,

            "status": "NOT AVAILABLE",

            "reference_count": 0,

            "explanation": str(e)

        }


    if not isinstance(
        ml_result,
        dict
    ):

        ml_result = {}


    ml_anomaly_score = ml_result.get(
        "anomaly_score",
        0
    )


    try:

        ml_anomaly_score = float(
            ml_anomaly_score
        )

    except:

        ml_anomaly_score = 0.0


    # Keep anomaly score inside valid range

    ml_anomaly_score = max(
        0.0,
        min(
            100.0,
            ml_anomaly_score
        )
    )


    # =================================================
    # TAMPERING ANALYSIS
    # =================================================

    try:

        tampering_result = analyze_tampering(
            filepath
        )

    except Exception as e:

        print(
            "Tampering analysis error:",
            e
        )

        tampering_result = {

            "status": "NOT AVAILABLE",

            "tampering_score": 0,

            "suspicious_regions": 0,

            "explanation": str(e),

            "indicators": []

        }


    if not isinstance(
        tampering_result,
        dict
    ):

        tampering_result = {}


    # =================================================
    # ACADEMIC CONSISTENCY
    # =================================================

    try:

        academic_result = analyze_academic_consistency(
            ocr_text
        )

    except Exception as e:

        print(
            "Academic consistency error:",
            e
        )

        academic_result = {

            "status": "NOT AVAILABLE",

            "score": 0,

            "suspicious_count": 0,

            "suspicious_indicators": [],

            "explanation": (
                "Academic consistency analysis "
                "could not be completed."
            ),

            "error": str(e)

        }


    if not isinstance(
        academic_result,
        dict
    ):

        academic_result = {}


    # =================================================
    # ACADEMIC SCORE
    # =================================================

    academic_score = academic_result.get(
        "score",
        academic_result.get(
            "overall_score",
            0
        )
    )


    try:

        academic_score = float(
            academic_score
        )

    except:

        academic_score = 0.0


    academic_score = max(
        0.0,
        min(
            100.0,
            academic_score
        )
    )


    academic_status = academic_result.get(
        "status",
        "UNKNOWN"
    )


    academic_indicators = academic_result.get(
        "suspicious_indicators",
        []
    )


    academic_explanation = academic_result.get(
        "explanation",
        ""
    )


    # =================================================
    # RISK SCORE
    # =================================================

    quality_score = (

        100

        if image_info.get(
            "image_quality"
        ) == "Good"

        else 60

        if image_info.get(
            "image_quality"
        ) == "Moderate"

        else 30

        if image_info.get(
            "image_quality"
        ) == "Low"

        else 0

    )


    # -------------------------------------------------
    # CALCULATE RISK SCORE
    # -------------------------------------------------

    try:

        risk_result = calculate_risk_score(

            verification_score=verification_score,

            similarity_score=similarity_score,

            ml_anomaly_score=ml_anomaly_score,

            quality_score=quality_score

        )

    except Exception as e:

        print(
            "Risk score calculation error:",
            e
        )

        risk_result = None


    # -------------------------------------------------
    # HANDLE RISK RESULT
    # -------------------------------------------------

    if isinstance(
        risk_result,
        dict
    ):

        overall_score = risk_result.get(

            "overall_score",

            risk_result.get(
                "score",
                0
            )

        )


        status = risk_result.get(

            "status",

            "NEEDS REVIEW"

        )


    else:

        # -------------------------------------------------
        # FALLBACK CALCULATION
        # -------------------------------------------------

        ml_consistency = (
            100 - ml_anomaly_score
        )


        overall_score = (

            (verification_score * 0.30)

            + (similarity_score * 0.30)

            + (ml_consistency * 0.25)

            + (quality_score * 0.15)

        )


        if overall_score >= 80:

            status = "LOW RISK"

        elif overall_score >= 60:

            status = "NEEDS REVIEW"

        else:

            status = "SUSPICIOUS"


    # -------------------------------------------------
    # MAKE SURE SCORE IS NUMERIC
    # -------------------------------------------------

    try:

        overall_score = float(
            overall_score
        )

    except:

        overall_score = 0.0


    # Keep score between 0 and 100

    overall_score = max(
        0.0,
        min(
            100.0,
            overall_score
        )
    )


    # =================================================
    # RISK EXPLANATION
    # =================================================

    try:

        risk_explanation = generate_risk_explanation(

            verification_score=verification_score,

            similarity_score=similarity_score,

            ml_anomaly_score=ml_anomaly_score,

            image_quality=image_info.get(
                "image_quality",
                "Unknown"
            ),

            status=status

        )

    except Exception as e:

        print(
            "Risk explanation error:",
            e
        )

        risk_explanation = (
            "Automated analysis completed. "
            "Manual verification is recommended."
        )


    # =================================================
    # SAVE HISTORY
    # =================================================

    try:

        connection = sqlite3.connect(
            DATABASE
        )

        cursor = connection.cursor()


        cursor.execute("""
            INSERT INTO verification_history (

                filename,

                candidate_name,

                register_number,

                verification_score,

                similarity_score,

                ml_anomaly_score,

                overall_score,

                status,

                image_quality,

                reference_filename

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            file.filename,

            details.get(
                "candidate_name",
                ""
            ),

            details.get(
                "register_number",
                ""
            ),

            verification_score,

            similarity_score,

            ml_anomaly_score,

            overall_score,

            status,

            image_info.get(
                "image_quality",
                "Unknown"
            ),

            reference_filename

        ))


        connection.commit()

        connection.close()


    except Exception as e:

        print(
            "History database warning:",
            e
        )


    # =================================================
    # PREPARE TEMPLATE VARIABLES
    # =================================================

    candidate_name = details.get(
        "candidate_name",
        ""
    )

    register_number = details.get(
        "register_number",
        ""
    )

    dob = details.get(
        "date_of_birth",
        details.get(
            "dob",
            ""
        )
    )


    image_quality = image_info.get(
        "image_quality",
        "Unknown"
    )

    blur_score = image_info.get(
        "blur_score",
        0
    )

    image_width = image_info.get(
        "width",
        0
    )

    image_height = image_info.get(
        "height",
        0
    )


    # -------------------------------------------------
    # ML TEMPLATE VARIABLES
    # -------------------------------------------------

    ml_prediction = ml_result.get(
        "prediction",
        ml_result.get(
            "status",
            "NOT AVAILABLE"
        )
    )


    ml_reference_count = ml_result.get(
        "reference_count",
        ml_result.get(
            "references",
            0
        )
    )


    # -------------------------------------------------
    # TAMPERING TEMPLATE VARIABLE
    # -------------------------------------------------

    tampering_status = tampering_result.get(
        "status",
        "NOT AVAILABLE"
    )


    # -------------------------------------------------
    # CLASSIFICATION TEMPLATE VARIABLE
    # -------------------------------------------------

    classification_confidence = document_confidence


    # =================================================
    # URLS
    # =================================================

    uploaded_preview_url = (
        "/uploads/"
        + file.filename
    )


    reference_url = None


    if reference_filename:

        reference_url = (
            "/references/"
            + reference_filename
        )


    # =================================================
    # RESULT PAGE
    # =================================================

    return render_template(

        "result.html",

        filename=file.filename,

        ocr_text=ocr_text,

        details=details,

        checks=verification_checks,

        verification_checks=verification_checks,

        verification_score=verification_score,

        verification_status=verification.get(
            "status",
            "UNKNOWN"
        ),

        overall_score=overall_score,

        status=status,

        document_type=document_type,

        document_confidence=document_confidence,

        classification_confidence=classification_confidence,

        classification_evidence=classification_evidence,

        similarity_score=similarity_score,

        authenticity_info=authenticity_info,

        ml_result=ml_result,

        ml_anomaly_score=ml_anomaly_score,

        ml_prediction=ml_prediction,

        ml_reference_count=ml_reference_count,

        tampering_result=tampering_result,

        tampering_status=tampering_status,

        image_info=image_info,

        image_quality=image_quality,

        blur_score=blur_score,

        image_width=image_width,

        image_height=image_height,

        academic_result=academic_result,

        academic_score=academic_score,

        academic_status=academic_status,

        academic_indicators=academic_indicators,

        academic_explanation=academic_explanation,

        risk_explanation=risk_explanation,

        candidate_name=candidate_name,

        register_number=register_number,

        dob=dob,

        reference_filename=reference_filename,

        reference_url=reference_url,

        uploaded_preview_url=uploaded_preview_url

    )


# =====================================================
# HISTORY
# =====================================================

@app.route("/history")
def history():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM verification_history
        ORDER BY id DESC
    """)


    records = cursor.fetchall()

    connection.close()


    return render_template(
        "history.html",
        records=records
    )


# =====================================================
# DOWNLOAD REPORT
# =====================================================

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


    # -------------------------------------------------
    # REPORT FILE NAME
    # -------------------------------------------------

    safe_name = os.path.splitext(
        filename
    )[0]


    report_filename = (
        safe_name
        + "_verification_report.pdf"
    )


    report_path = os.path.join(
        REPORT_FOLDER,
        report_filename
    )


    # =================================================
    # PDF STYLES
    # =================================================

    styles = getSampleStyleSheet()


    title_style = styles["Title"]

    title_style.alignment = TA_CENTER


    heading_style = styles["Heading2"]

    normal_style = styles["BodyText"]


    # =================================================
    # CREATE PDF
    # =================================================

    document = SimpleDocTemplate(

        report_path,

        pagesize=A4,

        rightMargin=40,

        leftMargin=40,

        topMargin=40,

        bottomMargin=40

    )


    elements = []


    # =================================================
    # TITLE
    # =================================================

    elements.append(

        Paragraph(

            "Academic Document Authenticity Validator",

            title_style

        )

    )


    elements.append(
        Spacer(1, 10)
    )


    elements.append(

        Paragraph(

            "Document Verification Report",

            heading_style

        )

    )


    elements.append(
        Spacer(1, 20)
    )


    # =================================================
    # DOCUMENT INFORMATION
    # =================================================

    elements.append(

        Paragraph(

            "Document Information",

            heading_style

        )

    )


    elements.append(
        Spacer(1, 8)
    )


    document_data = [

        [
            "Uploaded File",
            filename
        ],

        [
            "Document Type",
            document_type
        ],

        [
            "Candidate Name",
            candidate_name
        ],

        [
            "Register Number",
            register_number
        ],

        [
            "Date of Birth",
            dob
        ],

        [
            "Reference Document",
            reference
        ]

    ]


    document_table = Table(

        document_data,

        colWidths=[
            160,
            340
        ]

    )


    document_table.setStyle(

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.lightgrey
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )

        ])

    )


    elements.append(
        document_table
    )


    elements.append(
        Spacer(1, 20)
    )


    # =================================================
    # VERIFICATION SUMMARY
    # =================================================

    elements.append(

        Paragraph(

            "Verification Summary",

            heading_style

        )

    )


    elements.append(
        Spacer(1, 8)
    )


    summary_data = [

        [
            "Overall Score",
            str(overall_score) + "%"
        ],

        [
            "Final Status",
            status
        ],

        [
            "OCR Verification",
            str(verification_score) + "%"
        ],

        [
            "Visual Similarity",
            str(similarity) + "%"
        ],

        [
            "ML Anomaly Score",
            str(ml_score)
        ],

        [
            "Image Quality",
            image_quality
        ]

    ]


    summary_table = Table(

        summary_data,

        colWidths=[
            200,
            300
        ]

    )


    summary_table.setStyle(

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.lightgrey
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )

        ])

    )


    elements.append(
        summary_table
    )


    elements.append(
        Spacer(1, 25)
    )


    # =================================================
    # INTERPRETATION
    # =================================================

    elements.append(

        Paragraph(

            "Analysis Interpretation",

            heading_style

        )

    )


    elements.append(
        Spacer(1, 8)
    )


    if status == "LOW RISK":

        interpretation = (

            "The available verification signals "

            "are generally consistent with the "

            "reference evidence."

        )


    elif status == "NEEDS REVIEW":

        interpretation = (

            "The document contains verified "

            "information, but some verification "

            "signals differ from the available "

            "reference evidence. Manual "

            "verification is recommended."

        )


    else:

        interpretation = (

            "Several verification signals show "

            "inconsistencies. Manual verification "

            "using an authoritative institutional "

            "record is recommended."

        )


    elements.append(

        Paragraph(

            interpretation,

            normal_style

        )

    )


    elements.append(
        Spacer(1, 20)
    )


    # =================================================
    # DISCLAIMER
    # =================================================

    elements.append(

        Paragraph(

            "Disclaimer",

            heading_style

        )

    )


    elements.append(
        Spacer(1, 8)
    )


    disclaimer = (

        "This report is generated by an "

        "AI-assisted document analysis prototype. "

        "The system uses OCR extraction, visual "

        "comparison, academic consistency checks, "

        "image quality analysis and anomaly detection. "

        "The generated scores do not independently "

        "prove that a document is genuine or fraudulent. "

        "Final verification should be performed using "

        "authoritative institutional records."

    )


    elements.append(

        Paragraph(

            disclaimer,

            normal_style

        )

    )


    # =================================================
    # BUILD PDF
    # =================================================

    document.build(
        elements
    )


    return send_file(

        report_path,

        as_attachment=True,

        download_name=report_filename

    )


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )