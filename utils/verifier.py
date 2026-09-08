import re


# --------------------------------------------------
# EXTRACT IMPORTANT DETAILS FROM OCR TEXT
# --------------------------------------------------

def extract_details(text):

    details = {
        "candidate_name": "",
        "register_number": "",
        "date_of_birth": ""
    }

    # ---------------- REGISTER NUMBER ----------------

    register_patterns = [
        r"Register\s*No\.?\s*[:\-]?\s*([A-Za-z0-9]{6,20})",
        r"Register\s*Number\s*[:\-]?\s*([A-Za-z0-9]{6,20})",
        r"Reg\s*No\.?\s*[:\-]?\s*([A-Za-z0-9]{6,20})"
    ]

    for pattern in register_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            details["register_number"] = match.group(1)
            break


    # ---------------- DATE OF BIRTH ----------------

    dob_patterns = [
        r"\b\d{2}[-/]\d{2}[-/]\d{4}\b",
        r"\b\d{2}[-/]\d{2}[-/]\d{2}\b"
    ]

    for pattern in dob_patterns:
        match = re.search(pattern, text)

        if match:
            details["date_of_birth"] = match.group(0)
            break


    # ---------------- CANDIDATE NAME ----------------

    name_patterns = [
        r"Candidate'?s?\s*Name\s*[:\-]?\s*([A-Za-z ]{3,50})",
        r"Candidate\s*Name\s*[:\-]?\s*([A-Za-z ]{3,50})"
    ]

    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            details["candidate_name"] = match.group(1).strip()
            break


    return details


# --------------------------------------------------
# VERIFY DOCUMENT
# --------------------------------------------------

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
    register_number = details.get(
        "register_number",
        ""
    )

    if register_number and re.fullmatch(
        r"[A-Za-z0-9]{6,20}",
        register_number
    ):

        checks["Register number"] = True
        score += 1

    else:

        checks["Register number"] = False


    # 3. Date of birth
    dob = details.get(
        "date_of_birth",
        ""
    )

    if re.fullmatch(
        r"\d{2}[-/]\d{2}[-/]\d{4}",
        dob
    ):

        checks["Date of birth"] = True
        score += 1

    else:

        checks["Date of birth"] = False


    # 4. Academic information

    keywords = [
        "marks",
        "examination",
        "semester",
        "university"
    ]

    found_keywords = sum(
        1
        for word in keywords
        if word.lower() in text.lower()
    )

    if found_keywords >= 2:

        checks["Academic information"] = True
        score += 1

    else:

        checks["Academic information"] = False


    # ---------------- SCORE ----------------

    percentage = int(
        (score / total_checks) * 100
    )


    # ---------------- STATUS ----------------

    if percentage >= 75:

        status = "LOW RISK"

    elif percentage >= 50:

        status = "NEEDS REVIEW"

    else:

        status = "SUSPICIOUS"


    return checks, percentage, status