from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os


TEST_FOLDER = "test_documents"

os.makedirs(TEST_FOLDER, exist_ok=True)


# --------------------------------------------------
# Similar-looking test document
# --------------------------------------------------

def create_similar_document():

    path = os.path.join(
        TEST_FOLDER,
        "similar_document.pdf"
    )

    pdf = canvas.Canvas(
        path,
        pagesize=A4
    )

    width, height = A4

    y = height - 70

    pdf.setFont(
        "Helvetica-Bold",
        18
    )

    pdf.drawCentredString(
        width / 2,
        y,
        "EXAMPLE TECHNICAL UNIVERSITY"
    )

    y -= 35

    pdf.setFont(
        "Helvetica-Bold",
        14
    )

    pdf.drawCentredString(
        width / 2,
        y,
        "ACADEMIC MARKS RECORD"
    )

    y -= 60

    pdf.setFont(
        "Helvetica",
        11
    )

    fields = [
        ("Candidate Name", "KARTHIK RAO"),
        ("Register Number", "TEST2026010"),
        ("Date of Birth", "14/04/2007"),
        ("Course", "B.E."),
        ("Branch", "Computer Science and Engineering"),
        ("University", "Example Technical University"),
        ("Semester", "Semester 2")
    ]

    for label, value in fields:

        pdf.drawString(
            70,
            y,
            f"{label}: {value}"
        )

        y -= 28

    y -= 15

    pdf.setFont(
        "Helvetica-Bold",
        11
    )

    pdf.drawString(
        70,
        y,
        "Subject"
    )

    pdf.drawString(
        350,
        y,
        "Marks"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
        11
    )

    subjects = [
        ("Python Programming", "88"),
        ("Mathematics", "84"),
        ("Data Structures", "86")
    ]

    for subject, marks in subjects:

        pdf.drawString(
            70,
            y,
            subject
        )

        pdf.drawString(
            350,
            y,
            marks
        )

        y -= 25

    y -= 35

    pdf.setFont(
        "Helvetica-Oblique",
        9
    )

    pdf.drawString(
        70,
        y,
        "Synthetic document for software testing only."
    )

    pdf.save()

    print(
        "Created:",
        path
    )


# --------------------------------------------------
# Visually different test document
# --------------------------------------------------

def create_different_document():

    path = os.path.join(
        TEST_FOLDER,
        "different_document.pdf"
    )

    pdf = canvas.Canvas(
        path,
        pagesize=A4
    )

    width, height = A4

    # Very different layout

    pdf.setFont(
        "Courier-Bold",
        24
    )

    pdf.drawString(
        40,
        height - 50,
        "STUDENT RECORD"
    )

    pdf.setFont(
        "Courier",
        12
    )

    y = height - 110

    lines = [
        "----------------------------------------",
        "NAME       : UNKNOWN TEST STUDENT",
        "ID         : DIFFERENT999",
        "PROGRAM    : SOFTWARE TECHNOLOGY",
        "SESSION    : 2026",
        "----------------------------------------",
        "",
        "RESULT SUMMARY",
        "",
        "SUBJECT             SCORE",
        "----------------------------------------",
        "NETWORK SECURITY       42",
        "DATABASE SYSTEMS       38",
        "OPERATING SYSTEMS      41",
        "----------------------------------------",
        "",
        "DOCUMENT TYPE: TEST FORMAT",
        "",
        "This is a synthetic document created",
        "to test anomaly detection.",
    ]

    for line in lines:

        pdf.drawString(
            50,
            y,
            line
        )

        y -= 25

    pdf.save()

    print(
        "Created:",
        path
    )


create_similar_document()
create_different_document()

print("\nTest documents created successfully.")