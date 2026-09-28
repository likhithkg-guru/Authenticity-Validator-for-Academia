import re
from datetime import datetime


# --------------------------------------------------
# NUMBER EXTRACTION
# --------------------------------------------------

def extract_numbers(text):
    """
    Extract academic numbers from OCR text.
    """

    numbers = []

    for match in re.findall(r"\b\d{1,3}(?:\.\d+)?\b", text):
        try:
            value = float(match)

            # Ignore obvious years
            if 1900 <= value <= 2100:
                continue

            numbers.append(value)

        except ValueError:
            pass

    return numbers


# --------------------------------------------------
# MARKS VALIDATION
# --------------------------------------------------

def validate_marks(text):
    """
    Detect marks from the document and check
    whether they fall within a reasonable range.
    """

    marks = []

    patterns = [
        r"(?:marks|score)\s*[:\-]?\s*(\d{1,3})",
        r"(?:obtained)\s*[:\-]?\s*(\d{1,3})",
        r"(?:total marks)\s*[:\-]?\s*(\d{1,3})"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for value in matches:
            try:
                mark = int(value)

                if 0 <= mark <= 100:
                    marks.append(mark)

            except ValueError:
                pass

    if not marks:
        return {
            "status": "NOT AVAILABLE",
            "score": 70,
            "message": "No clear subject-wise marks were detected."
        }

    invalid = [
        mark for mark in marks
        if mark < 0 or mark > 100
    ]

    if invalid:
        return {
            "status": "SUSPICIOUS",
            "score": 20,
            "message": "One or more detected marks are outside the expected range."
        }

    return {
        "status": "CONSISTENT",
        "score": 100,
        "message": f"{len(marks)} mark values were within the expected range."
    }


# --------------------------------------------------
# PERCENTAGE VALIDATION
# --------------------------------------------------

def validate_percentage(text):
    """
    Check percentage values for obvious invalid values.
    """

    matches = re.findall(
        r"(?:percentage|percent|%)\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if not matches:
        # Also check values immediately before %
        matches = re.findall(
            r"(\d{1,3}(?:\.\d+)?)\s*%",
            text
        )

    if not matches:
        return {
            "status": "NOT AVAILABLE",
            "score": 70,
            "message": "No percentage value was clearly detected."
        }

    percentages = []

    for value in matches:
        try:
            percentages.append(float(value))
        except ValueError:
            pass

    invalid = [
        value for value in percentages
        if value < 0 or value > 100
    ]

    if invalid:
        return {
            "status": "SUSPICIOUS",
            "score": 20,
            "message": "A percentage value outside 0–100 was detected."
        }

    return {
        "status": "CONSISTENT",
        "score": 100,
        "message": "Detected percentage values are within a valid range."
    }


# --------------------------------------------------
# DATE VALIDATION
# --------------------------------------------------

def validate_dates(text):
    """
    Validate dates in DD/MM/YYYY or DD-MM-YYYY format.
    """

    dates = re.findall(
        r"\b\d{2}[-/]\d{2}[-/]\d{4}\b",
        text
    )

    if not dates:
        return {
            "status": "NOT AVAILABLE",
            "score": 70,
            "message": "No academic date was detected."
        }

    invalid_dates = []

    for date_string in dates:

        for date_format in ("%d/%m/%Y", "%d-%m-%Y"):

            try:
                datetime.strptime(date_string, date_format)
                break

            except ValueError:
                continue

        else:
            invalid_dates.append(date_string)

    if invalid_dates:
        return {
            "status": "SUSPICIOUS",
            "score": 20,
            "message": "One or more detected dates are invalid."
        }

    return {
        "status": "VALID",
        "score": 100,
        "message": f"{len(dates)} date value(s) passed validation."
    }


# --------------------------------------------------
# REQUIRED ACADEMIC INFORMATION
# --------------------------------------------------

def validate_required_information(text):
    """
    Check whether important academic keywords exist.
    """

    text_lower = text.lower()

    required_groups = {
        "University": [
            "university",
            "institution"
        ],

        "Examination": [
            "examination",
            "exam"
        ],

        "Semester": [
            "semester",
            "sem"
        ],

        "Marks": [
            "marks",
            "score",
            "grade"
        ]
    }

    found = 0
    missing = []

    for field, keywords in required_groups.items():

        if any(keyword in text_lower for keyword in keywords):
            found += 1
        else:
            missing.append(field)

    percentage = int(
        (found / len(required_groups)) * 100
    )

    if percentage >= 75:

        status = "CONSISTENT"

    elif percentage >= 50:

        status = "NEEDS REVIEW"

    else:

        status = "SUSPICIOUS"

    return {
        "status": status,
        "score": percentage,
        "found": found,
        "total": len(required_groups),
        "missing": missing,
        "message": f"{found}/{len(required_groups)} academic information groups detected."
    }


# --------------------------------------------------
# REGISTER NUMBER VALIDATION
# --------------------------------------------------

def validate_register_number(register_number):
    """
    Validate the extracted register number format.
    """

    if not register_number:

        return {
            "status": "NOT AVAILABLE",
            "score": 60,
            "message": "Register number could not be detected."
        }

    if re.fullmatch(
        r"[A-Za-z0-9]{6,20}",
        register_number
    ):

        return {
            "status": "VALID",
            "score": 100,
            "message": "Register number format is valid."
        }

    return {
        "status": "SUSPICIOUS",
        "score": 25,
        "message": "Register number format is unusual."
    }


# --------------------------------------------------
# MAIN ACADEMIC ANALYSIS
# --------------------------------------------------

def analyze_academic_consistency(
    text,
    details=None
):

    if details is None:
        details = {}

    marks_result = validate_marks(text)

    percentage_result = validate_percentage(text)

    date_result = validate_dates(text)

    required_result = validate_required_information(text)

    register_result = validate_register_number(
        details.get("register_number", "")
    )

    results = {
        "marks": marks_result,
        "percentage": percentage_result,
        "dates": date_result,
        "required_information": required_result,
        "register_number": register_result
    }

    scores = [
        marks_result["score"],
        percentage_result["score"],
        date_result["score"],
        required_result["score"],
        register_result["score"]
    ]

    overall_score = round(
        sum(scores) / len(scores),
        2
    )

    suspicious_indicators = []

    for name, result in results.items():

        if result["status"] in [
            "SUSPICIOUS",
            "NEEDS REVIEW"
        ]:

            suspicious_indicators.append({
                "check": name,
                "status": result["status"],
                "message": result["message"]
            })

    if overall_score >= 80:

        status = "CONSISTENT"

    elif overall_score >= 60:

        status = "NEEDS REVIEW"

    else:

        status = "SUSPICIOUS"

    return {
        "available": True,
        "status": status,
        "overall_score": overall_score,
        "suspicious_count": len(
            suspicious_indicators
        ),
        "checks": results,
        "suspicious_indicators": suspicious_indicators,
        "explanation": (
            "Academic information was checked for "
            "basic consistency, valid ranges, dates, "
            "required fields and register-number format."
        )
    }