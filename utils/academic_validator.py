import re


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_numbers(text):
    if not text:
        return []

    return [float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", text)]


def detect_academic_groups(text):
    text_lower = text.lower()

    groups = {
        "marks_table": False,
        "subjects": False,
        "institution": False,
        "result": False
    }

    marks_keywords = [
        "marks obtained",
        "max. marks",
        "max marks",
        "min. marks",
        "min marks",
        "total",
        "grade"
    ]

    marks_hits = sum(
        1 for keyword in marks_keywords
        if keyword in text_lower
    )

    if marks_hits >= 2:
        groups["marks_table"] = True

    subject_keywords = [
        "subject",
        "subjects",
        "first language",
        "second language",
        "third language",
        "mathematics",
        "science",
        "social science",
        "social studies",
        "english",
        "kannada",
        "hindi"
    ]

    subject_hits = sum(
        1 for keyword in subject_keywords
        if keyword in text_lower
    )

    if subject_hits >= 2:
        groups["subjects"] = True

    institution_keywords = [
        "university",
        "board",
        "school",
        "college",
        "institution",
        "education",
        "government of karnataka",
        "examination and assessment board"
    ]

    if any(keyword in text_lower for keyword in institution_keywords):
        groups["institution"] = True

    result_keywords = [
        "passed",
        "pass",
        "result",
        "percentage",
        "grade",
        "division",
        "total"
    ]

    result_hits = sum(
        1 for keyword in result_keywords
        if keyword in text_lower
    )

    if result_hits >= 2:
        groups["result"] = True

    return groups


def detect_subject_marks(text):
    text_lower = text.lower()

    subject_keywords = [
        "first language",
        "second language",
        "third language",
        "mathematics",
        "science",
        "social science",
        "social studies",
        "english",
        "kannada",
        "hindi"
    ]

    found_subjects = []

    for subject in subject_keywords:
        if subject in text_lower:
            found_subjects.append(subject)

    return {
        "detected": len(found_subjects) >= 2,
        "subjects": found_subjects
    }


def validate_marks(text):
    text_lower = text.lower()

    table_keywords = [
        "marks obtained",
        "max. marks",
        "max marks",
        "min. marks",
        "min marks",
        "marks",
        "total",
        "grade"
    ]

    keyword_hits = sum(
        1 for keyword in table_keywords
        if keyword in text_lower
    )

    numbers = extract_numbers(text)

    detected = keyword_hits >= 2 and len(numbers) >= 5

    return {
        "detected": detected,
        "keyword_hits": keyword_hits,
        "number_count": len(numbers)
    }


def validate_percentage(text):
    patterns = [
        r"\b\d{1,3}(?:\.\d+)?\s*%",
        r"percentage\s*[:\-]?\s*\d{1,3}(?:\.\d+)?",
        r"percent\s*[:\-]?\s*\d{1,3}(?:\.\d+)?"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return {
                "status": "PASS",
                "message": f"Explicit percentage detected: {match.group(0)}"
            }

    return {
        "status": "NOT_APPLICABLE",
        "message": "Percentage is not explicitly printed on this document."
    }


def validate_dates(text):
    patterns = [
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"
    ]

    dates = []

    for pattern in patterns:
        dates.extend(re.findall(pattern, text))

    if dates:
        return {
            "status": "PASS",
            "message": f"{len(dates)} date value(s) detected."
        }

    return {
        "status": "REVIEW",
        "message": "No clearly extractable date detected."
    }


def validate_register_number(text):
    """
    Register number validation.

    OCR sometimes inserts spaces around punctuation.
    Karnataka SSLC OCR can also contain noisy text around
    the register-number label, so the matching is tolerant.
    """

    patterns = [
        r"register\s*(?:no|number)\s*[:.\-]?\s*([A-Z0-9]{6,20})",
        r"registration\s*(?:no|number)\s*[:.\-]?\s*([A-Z0-9]{6,20})",
        r"roll\s*(?:no|number)\s*[:.\-]?\s*([A-Z0-9]{6,20})",
        r"\bUSN\s*[:.\-]?\s*([A-Z0-9]{6,20})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return {
                "status": "PASS",
                "message": "Register/identification number detected.",
                "value": match.group(1)
            }

    # Fallback specifically for Karnataka-style OCR
    fallback = re.search(
        r"Register\s*No\.?\s*[:\-]?\s*(\d{8,15})",
        text,
        re.IGNORECASE
    )

    if fallback:

        return {
            "status": "PASS",
            "message": "Register/identification number detected.",
            "value": fallback.group(1)
        }

    return {
        "status": "REVIEW",
        "message": "Register/identification number could not be reliably extracted."
    }


def check_numeric_consistency(text):
    """
    OCR often destroys table columns.

    Therefore this function checks whether marks information
    exists but does NOT treat imperfect table extraction as fraud.
    """

    marks_result = validate_marks(text)

    if not marks_result["detected"]:

        return {
            "status": "REVIEW",
            "message": "Marks information could not be reliably extracted."
        }

    text_lower = text.lower()

    if "total" in text_lower:

        return {
            "status": "REVIEW",
            "message": (
                "Marks and total fields were detected, "
                "but OCR table alignment should be reviewed."
            )
        }

    return {
        "status": "REVIEW",
        "message": (
            "Marks were detected, but a clearly extractable "
            "total was not found."
        )
    }


def validate_required_information(text):

    groups = detect_academic_groups(text)

    detected = sum(
        1 for value in groups.values()
        if value
    )

    total = len(groups)

    score = (detected / total) * 100

    if detected == total:
        status = "CONSISTENT"

    elif detected >= 3:
        status = "NEEDS REVIEW"

    else:
        status = "INCOMPLETE"

    return {
        "status": status,
        "score": round(score, 1),
        "groups": groups,
        "detected_groups": detected,
        "total_groups": total
    }


def analyze_academic_consistency(text):

    text = clean_text(text)

    if not text:

        return {
            "status": "INCOMPLETE",
            "score": 0.0,
            "suspicious_count": 1,
            "suspicious_indicators": [
                {
                    "check": "ocr",
                    "status": "FAIL",
                    "message": "No academic text could be extracted."
                }
            ],
            "explanation": (
                "Academic consistency could not be evaluated "
                "because OCR returned no usable text."
            )
        }

    required = validate_required_information(text)

    subject_result = detect_subject_marks(text)

    marks_result = validate_marks(text)

    percentage_result = validate_percentage(text)

    date_result = validate_dates(text)

    register_result = validate_register_number(text)

    numeric_result = check_numeric_consistency(text)

    indicators = []

    # -------------------------------------------------
    # Required information
    # -------------------------------------------------

    if required["detected_groups"] < required["total_groups"]:

        indicators.append({
            "check": "required_information",
            "status": "NEEDS REVIEW",
            "message": (
                f"{required['detected_groups']}/"
                f"{required['total_groups']} academic "
                f"information groups detected."
            )
        })

    # -------------------------------------------------
    # Subjects
    # -------------------------------------------------

    if not subject_result["detected"]:

        indicators.append({
            "check": "subjects",
            "status": "NEEDS REVIEW",
            "message": (
                "Subject-level information could not "
                "be reliably detected."
            )
        })

    # -------------------------------------------------
    # Marks table
    # -------------------------------------------------

    if not marks_result["detected"]:

        indicators.append({
            "check": "marks_table",
            "status": "NEEDS REVIEW",
            "message": (
                "Marks-table information could not "
                "be reliably extracted."
            )
        })

    # -------------------------------------------------
    # IMPORTANT:
    # Missing percentage is NOT suspicious
    # -------------------------------------------------

    # Do NOT add percentage to indicators.

    # -------------------------------------------------
    # Date
    # -------------------------------------------------

    if date_result["status"] != "PASS":

        indicators.append({
            "check": "date",
            "status": "NEEDS REVIEW",
            "message": date_result["message"]
        })

    # -------------------------------------------------
    # Register number
    # -------------------------------------------------

    if register_result["status"] != "PASS":

        indicators.append({
            "check": "register_number",
            "status": "NEEDS REVIEW",
            "message": register_result["message"]
        })

    # -------------------------------------------------
    # Numeric consistency
    # -------------------------------------------------

    # OCR table alignment is uncertain.
    # This is a review note, NOT a fraud indicator.

    numeric_review = numeric_result["status"] == "REVIEW"

    # -------------------------------------------------
    # SCORE
    # -------------------------------------------------

    # Start with the required academic information score.

    score = required["score"]

    # Subject information
    if subject_result["detected"]:
        score += 2.5

    # Marks table
    if marks_result["detected"]:
        score += 2.5

    # Register number
    if register_result["status"] == "PASS":
        score += 2.5

    # Date
    if date_result["status"] == "PASS":
        score += 2.5

    score = min(score, 100.0)

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------

    if (
        required["detected_groups"] >= 3
        and subject_result["detected"]
        and marks_result["detected"]
    ):

        status = "CONSISTENT"

    elif required["detected_groups"] >= 3:

        status = "NEEDS REVIEW"

    else:

        status = "INCOMPLETE"

    # -------------------------------------------------
    # EXPLANATION
    # -------------------------------------------------

    if status == "CONSISTENT":

        explanation = (
            "Required academic information, subject details "
            "and marks-table information were detected consistently. "
            "Some table relationships may still require manual review "
            "because OCR can alter table alignment."
        )

    elif status == "NEEDS REVIEW":

        explanation = (
            "Academic information was detected, but some fields "
            "or numeric/table relationships require additional review. "
            "OCR table extraction can affect automated consistency checks."
        )

    else:

        explanation = (
            "Important academic information could not be reliably "
            "extracted. Manual verification is recommended."
        )

    return {
        "status": status,
        "score": round(score, 1),

        "suspicious_count": len(indicators),

        "suspicious_indicators": indicators,

        "explanation": explanation,

        "required_information": required,

        "subjects": subject_result,

        "marks": marks_result,

        "percentage": percentage_result,

        "dates": date_result,

        "register_number": register_result,

        "numeric_consistency": numeric_result
    }