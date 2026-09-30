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
from utils.verifier import extract_details, verify_document
from utils.image_analyzer import analyze_image
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
# CREATE REQUIRED FOLDERS
# =====================================================

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

os.makedirs(
    "static/uploads",
    exist_ok=True
)


# =====================================================
# DATABASE
# =====================================================

DATABASE = "verification_history.db"


def init_database():

    connection = sqlite3.connect(
        DATABASE
    )

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
# UPLOADED FILE
# =====================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =====================================================
# REFERENCE FILE
# =====================================================

@app.route("/references/<filename>")
def reference_file(filename):

    return send_from_directory(
        REFERENCE_FOLDER,
        filename
    )


# =====================================================
# ANALYZE DOCUMENT
# =====================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    # =================================================
    # CHECK UPLOAD
    # =================================================

    if "document" not in request.files:

        return "No document uploaded"

    file = request.files["document"]

    if file.filename == "":

        return "No file selected"


    # =================================================
    # SAVE FILE
    # =================================================

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)


    # =================================================
    # OCR
    # =================================================

    text = extract_text_from_pdf(
        filepath
    )


    # =================================================
    # EXTRACT DETAILS
    # =================================================

    details = extract_details(
        text
    )


    # =================================================
    # BASIC VERIFICATION
    # =================================================

    (
        checks,
        verification_score,
        verification_status
    ) = verify_document(
        details,
        text
    )


    # =================================================
    # IMAGE ANALYSIS
    # =================================================

    image_info = analyze_image(
        filepath
    )


    # =================================================
    # REFERENCE COMPARISON
    # =================================================

    authenticity_info = find_best_reference(
        filepath,
        REFERENCE_FOLDER
    )

    similarity_score = None

    if authenticity_info:

        similarity_score = (
            authenticity_info.get(
                "similarity"
            )
        )


    # =================================================
    # MACHINE LEARNING ANALYSIS
    # =================================================

    ml_result = analyze_with_ml(
        filepath,
        REFERENCE_FOLDER
    )


    # =================================================
    # TAMPERING ANALYSIS
    # =================================================

    tampering_result = analyze_tampering(
        filepath
    )


    # =================================================
    # ACADEMIC CONSISTENCY ANALYSIS
    # =================================================

    academic_result = analyze_academic_consistency(
        text
    )


    # =================================================
    # RISK SCORE
    # =================================================

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


    # =================================================
    # RISK EXPLANATION
    # =================================================

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


    # =================================================
    # SCORE COMPONENTS
    # =================================================

    verification_component = (
        verification_score
    )


    if similarity_score is not None:

        similarity_component = (
            similarity_score
        )

    else:

        similarity_component = 0


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


    # =================================================
    # REFERENCE INFORMATION
    # =================================================

    reference_filename = None

    if authenticity_info:

        reference_filename = (
            authenticity_info.get(
                "filename"
            )
        )


    # =================================================
    # SAVE VERIFICATION HISTORY
    # =================================================

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

        risk_result[
            "overall_score"
        ],

        risk_result[
            "status"
        ],

        image_quality,

        reference_filename

    ))


    connection.commit()

    connection.close()


    # =================================================
    # FILE URLS
    # =================================================

    uploaded_url = (
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


        # ---------------------------------------------
        # BASIC DOCUMENT DATA
        # ---------------------------------------------

        filename=file.filename,

        text=text,

        details=details,

        checks=checks,


        # ---------------------------------------------
        # BASIC VERIFICATION
        # ---------------------------------------------

        score=verification_score,

        verification_score=verification_score,

        verification_status=verification_status,


        # ---------------------------------------------
        # FINAL RISK RESULT
        # ---------------------------------------------

        risk_result=risk_result,

        status=risk_result[
            "status"
        ],

        overall_score=risk_result[
            "overall_score"
        ],


        # ---------------------------------------------
        # IMAGE INFORMATION
        # ---------------------------------------------

        image_info=image_info,

        quality_score=risk_result[
            "quality_score"
        ],


        # ---------------------------------------------
        # REFERENCE / AUTHENTICITY
        # ---------------------------------------------

        authenticity_info=authenticity_info,

        similarity_score=similarity_score,

        reference_filename=reference_filename,


        # ---------------------------------------------
        # RISK EXPLANATION
        # ---------------------------------------------

        risk_explanation=risk_explanation,


        # ---------------------------------------------
        # ML
        # ---------------------------------------------

        ml_result=ml_result,


        # ---------------------------------------------
        # TAMPERING
        # ---------------------------------------------

        tampering_result=tampering_result,


        # ---------------------------------------------
        # ACADEMIC CONSISTENCY
        # ---------------------------------------------

        academic_result=academic_result,


        # ---------------------------------------------
        # SCORE COMPONENTS
        # ---------------------------------------------

        verification_component=(
            verification_component
        ),

        similarity_component=(
            similarity_component
        ),

        ml_component=(
            ml_component
        ),

        quality_component=(
            quality_component
        ),


        # ---------------------------------------------
        # URLS
        # ---------------------------------------------

        uploaded_url=uploaded_url,

        reference_url=reference_url
    )


# =====================================================
# HISTORY DASHBOARD
# =====================================================

@app.route("/history")
def history():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = (
        sqlite3.Row
    )

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

@app.route("/download_report/<filename>")
@app.route("/report/<filename>")
def download_report(filename):

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


    # =================================================
    # REPORT FILE NAME
    # =================================================

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

    title_style.alignment = (
        TA_CENTER
    )

    heading_style = (
        styles["Heading2"]
    )

    normal_style = (
        styles["BodyText"]
    )


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

            "Academic Document "
            "Authenticity Validator",

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
            150,
            350
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
            overall_score + "%"
        ],

        [
            "Final Status",
            status
        ],

        [
            "OCR Verification",
            verification_score + "%"
        ],

        [
            "Visual Similarity",
            similarity + "%"
        ],

        [
            "ML Anomaly Score",
            ml_score
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
        "comparison, image quality analysis, "
        "machine-learning pattern analysis, "
        "academic consistency checks and "
        "tampering indicators. "
        "An anomaly score or verification score "
        "does not independently prove that a "
        "document is fraudulent. Final authenticity "
        "decisions should be made using authoritative "
        "institutional records or manual verification."
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
# RUN APPLICATION
# =====================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )