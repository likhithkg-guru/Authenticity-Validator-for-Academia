import re


# ==================================================
# EXTRACT DETAILS
# ==================================================

def extract_details(text):

    details = {
        "candidate_name": "",
        "register_number": "",
        "date_of_birth": ""
    }

    # ------------------------------------------
    # Candidate Name
    # ------------------------------------------

    name_patterns = [

        r"Candidate['’]s\s*Name\s*[:\-]?\s*([A-Za-z ]{3,60})",

        r"Candidate\s*Name\s*[:\-]?\s*([A-Za-z ]{3,60})",

        r"Name\s*[:\-]\s*([A-Za-z ]{3,60})"
    ]

    for pattern in name_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            details["candidate_name"] = (
                match.group(1)
                .strip()
            )

            break


    # ------------------------------------------
    # Register Number
    # ------------------------------------------

    register_patterns = [

        r"Register\s*No\.?\s*[:\-]?\s*([A-Za-z0-9]{6,20})",

        r"Register\s*Number\s*[:\-]?\s*([A-Za-z0-9]{6,20})",

        r"Reg\.?\s*No\.?\s*[:\-]?\s*([A-Za-z0-9]{6,20})",

        r"Reg\s*Number\s*[:\-]?\s*([A-Za-z0-9]{6,20})"
    ]

    for pattern in register_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            details["register_number"] = (
                match.group(1)
                .strip()
            )

            break


    # ------------------------------------------
    # Date of Birth
    # ------------------------------------------

    dob_patterns = [

        r"Date\s*of\s*Birth\s*[:\-]?\s*(\d{2}[-/]\d{2}[-/]\d{4})",

        r"D\.?O\.?B\.?\s*[:\-]?\s*(\d{2}[-/]\d{2}[-/]\d{4})",

        r"Birth\s*Date\s*[:\-]?\s*(\d{2}[-/]\d{2}[-/]\d{4})"
    ]

    for pattern in dob_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            details["date_of_birth"] = (
                match.group(1)
            )

            break


    # ------------------------------------------
    # Fallback DOB detection
    # ------------------------------------------

    if not details["date_of_birth"]:

        match = re.search(
            r"\b\d{2}[-/]\d{2}[-/]\d{4}\b",
            text
        )

        if match:

            details["date_of_birth"] = (
                match.group(0)
            )


    return details


# ==================================================
# VERIFY DOCUMENT
# ==================================================

def verify_document(details, text):

    checks = {}

    score = 0

    total_checks = 4


    # ------------------------------------------
    # Candidate Name
    # ------------------------------------------

    if details.get("candidate_name"):

        checks["Candidate name"] = True

        score += 1

    else:

        checks["Candidate name"] = False


    # ------------------------------------------
    # Register Number
    # ------------------------------------------

    register_number = details.get(
        "register_number",
        ""
    )

    if (
        register_number
        and re.fullmatch(
            r"[A-Za-z0-9]{6,20}",
            register_number
        )
    ):

        checks["Register number"] = True

        score += 1

    else:

        checks["Register number"] = False


    # ------------------------------------------
    # Date of Birth
    # ------------------------------------------

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


    # ------------------------------------------
    # Academic Information
    # ------------------------------------------

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


    # ------------------------------------------
    # SCORE
    # ------------------------------------------

    percentage = int(
        (score / total_checks) * 100
    )


    # ------------------------------------------
    # STATUS
    # ------------------------------------------

    if percentage >= 75:

        status = "LOW RISK"

    elif percentage >= 50:

        status = "NEEDS REVIEW"

    else:

        status = "SUSPICIOUS"


    return checks, percentage, status