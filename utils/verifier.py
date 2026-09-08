import re


def verify_document(details, text):

    checks = {}
    score = 0
    total_checks = 4

    # 1. Candidate name
    if details.get("candidate_name"):
        checks["Candidate name"] = True
        score += 1
    else:
        checks["Candidate name"] = False

    # 2. Register number
    register_number = details.get("register_number", "")

    if register_number and re.fullmatch(r"[A-Za-z0-9]{6,20}", register_number):
        checks["Register number"] = True
        score += 1
    else:
        checks["Register number"] = False

    # 3. Date of birth
    dob = details.get("date_of_birth", "")

    if re.fullmatch(r"\d{2}[-/]\d{2}[-/]\d{4}", dob):
        checks["Date of birth"] = True
        score += 1
    else:
        checks["Date of birth"] = False

    # 4. Basic academic keywords
    keywords = [
        "marks",
        "examination",
        "semester",
        "university"
    ]

    found_keywords = sum(
        1 for word in keywords
        if word.lower() in text.lower()
    )

    if found_keywords >= 2:
        checks["Academic information"] = True
        score += 1
    else:
        checks["Academic information"] = False

    percentage = int((score / total_checks) * 100)

    if percentage >= 75:
        status = "LOW RISK"
    elif percentage >= 50:
        status = "NEEDS REVIEW"
    else:
        status = "SUSPICIOUS"

    return checks, percentage, status