from utils.academic_validator import analyze_academic_consistency


sample_text = """
Candidate Name: ROHAN KUMAR
Register No: DUMMY2026001
Date of Birth: 15/08/2007

Example Technical University

B.E. Computer Science and Engineering

Semester 2 Examination

Mathematics Marks: 85
Physics Marks: 78
Chemistry Marks: 91

Percentage: 84.67%
"""


details = {
    "candidate_name": "ROHAN KUMAR",
    "register_number": "DUMMY2026001",
    "date_of_birth": "15/08/2007"
}


result = analyze_academic_consistency(
    sample_text,
    details
)


print("\n================================")
print("ACADEMIC CONSISTENCY TEST")
print("================================")

print("Status:", result["status"])
print("Overall Score:", result["overall_score"])
print(
    "Suspicious Indicators:",
    result["suspicious_count"]
)

print("\nCHECKS:")

for name, check in result["checks"].items():

    print(
        name,
        "->",
        check["status"],
        "|",
        check["message"]
    )

print("\n================================")
print("TEST COMPLETE")
print("================================")