from utils.document_classifier import classify_document


text = """
Example Technical University

B.E. Computer Science and Engineering

Semester 2 Examination

Candidate Name: ROHAN KUMAR
Register Number: DUMMY2026001

Mathematics Marks: 85
Physics Marks: 78
Chemistry Marks: 91

Total Marks: 254
Percentage: 84.67%
"""


result = classify_document(text)


print("\nDOCUMENT CLASSIFICATION")
print("-----------------------")

print(
    "Document Type:",
    result["document_type"]
)

print(
    "Confidence:",
    result["confidence"],
    "%"
)

print(
    "Matched Keywords:",
    result["matched_keywords"]
)

print(
    "\nScores:"
)

for document_type, score in result["scores"].items():

    print(
        document_type,
        ":",
        score
    )