from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os


REFERENCE_FOLDER = "reference_documents"

os.makedirs(REFERENCE_FOLDER, exist_ok=True)


documents = [
    {
        "name": "ANANYA SHARMA",
        "reg": "DUMMY2026002",
        "dob": "21/03/2007",
        "branch": "Computer Science and Engineering",
        "semester": "Semester 2",
        "marks": ["Python Programming", "85", "Mathematics", "88"]
    },
    {
        "name": "ARJUN REDDY",
        "reg": "DUMMY2026003",
        "dob": "12/11/2007",
        "branch": "Information Science and Engineering",
        "semester": "Semester 2",
        "marks": ["Data Structures", "82", "Mathematics", "91"]
    },
    {
        "name": "PRIYA NAIR",
        "reg": "DUMMY2026004",
        "dob": "05/06/2007",
        "branch": "Artificial Intelligence and Machine Learning",
        "semester": "Semester 2",
        "marks": ["Python Programming", "90", "Mathematics", "86"]
    },
    {
        "name": "RAHUL KUMAR",
        "reg": "DUMMY2026005",
        "dob": "18/01/2007",
        "branch": "Computer Science and Engineering",
        "semester": "Semester 2",
        "marks": ["Programming in C", "87", "Physics", "84"]
    },
    {
        "name": "MEERA SHETTY",
        "reg": "DUMMY2026006",
        "dob": "29/09/2007",
        "branch": "Electronics and Communication Engineering",
        "semester": "Semester 2",
        "marks": ["Digital Electronics", "89", "Mathematics", "83"]
    },
    {
        "name": "VIKAS PATEL",
        "reg": "DUMMY2026007",
        "dob": "07/02/2007",
        "branch": "Computer Science and Engineering",
        "semester": "Semester 2",
        "marks": ["Data Structures", "86", "Physics", "81"]
    }
]


def create_pdf(data, filename):

    filepath = os.path.join(
        REFERENCE_FOLDER,
        filename
    )

    pdf = canvas.Canvas(
        filepath,
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
        ("Candidate Name", data["name"]),
        ("Register Number", data["reg"]),
        ("Date of Birth", data["dob"]),
        ("Course", "B.E."),
        ("Branch", data["branch"]),
        ("University", "Example Technical University"),
        ("Semester", data["semester"])
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

    for subject, marks in zip(
        data["marks"][::2],
        data["marks"][1::2]
    ):

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
        f"Created: {filepath}"
    )


for index, document in enumerate(
    documents,
    start=2
):

    create_pdf(
        document,
        f"genuine_sample_{index}.pdf"
    )


print("\nAll synthetic reference documents created.")