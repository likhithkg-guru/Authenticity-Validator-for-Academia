import re


# ============================================================
# BASIC CLEANING
# ============================================================

def clean_value(value):
    if not value:
        return ""

    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" :;-|")

    return value.strip()


def normalize_ocr_text(text):
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = text.replace("’", "'")
    text = re.sub(r"[ \t]+", " ", text)

    return text


# ============================================================
# CANDIDATE NAME
# ============================================================

def looks_like_name(value):
    if not value:
        return False

    value = clean_value(value)

    # Reject obvious OCR sentence fragments
    bad_phrases = [
        "has passed",
        "passed",
        "examination",
        "certificate",
        "register",
        "medium",
        "candidate type",
        "marks obtained",
        "marks",
    ]

    lower_value = value.lower()

    for phrase in bad_phrases:
        if phrase in lower_value:
            return False

    # Remove common OCR junk
    value = re.sub(r"[^A-Za-z .'-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    words = value.split()

    # A proper candidate name normally has at least 2 words
    if len(words) < 2:
        return False

    # Avoid very long sentences
    if len(words) > 8:
        return False

    # Most characters should be alphabetic
    letters = sum(c.isalpha() for c in value)

    if letters < 5:
        return False

    return True


def extract_candidate_name(text):
    text = normalize_ocr_text(text)

    # --------------------------------------------------------
    # 1. EXACT LABELS FIRST
    # --------------------------------------------------------

    exact_patterns = [
        r"Candidate['’]s\s+Name\s*[:\-]\s*(.+)",
        r"Candidate\s+Name\s*[:\-]\s*(.+)",
        r"Name\s+of\s+Candidate\s*[:\-]\s*(.+)",
        r"Student['’]s\s+Name\s*[:\-]\s*(.+)",
        r"Student\s+Name\s*[:\-]\s*(.+)",
    ]

    # Search line-by-line first
    for line in text.splitlines():

        line = clean_value(line)

        for pattern in exact_patterns:

            match = re.search(pattern, line, re.IGNORECASE)

            if match:
                value = match.group(1)

                # Stop before the next field
                value = re.split(
                    r"\b(?:Father['’]s|Mother['’]s|Mothers|Fathers|"
                    r"Register|Registration|Reg\.?|Date\s+of\s+Birth|"
                    r"DOB|Medium|Candidate\s+Type|Roll\s+No|USN)\b",
                    value,
                    flags=re.IGNORECASE
                )[0]

                value = clean_value(value)

                if looks_like_name(value):
                    return value

    # --------------------------------------------------------
    # 2. HANDLE OCR WHERE LABEL AND VALUE ARE ON DIFFERENT LINES
    # --------------------------------------------------------

    lines = text.splitlines()

    for i, line in enumerate(lines):

        line_clean = clean_value(line)

        if re.search(
            r"Candidate['’]s\s+Name|Candidate\s+Name|"
            r"Name\s+of\s+Candidate|Student['’]s\s+Name|Student\s+Name",
            line_clean,
            re.IGNORECASE
        ):

            # Check next line
            if i + 1 < len(lines):

                next_line = clean_value(lines[i + 1])

                if looks_like_name(next_line):
                    return next_line

    # --------------------------------------------------------
    # 3. FALLBACK
    # --------------------------------------------------------

    # Only use generic "Name:" if exact candidate label wasn't found
    fallback_patterns = [
        r"\bName\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{2,60})"
    ]

    for pattern in fallback_patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            value = clean_value(match.group(1))

            value = re.split(
                r"\b(?:Father['’]s|Mother['’]s|Register|"
                r"Date\s+of\s+Birth|DOB|Medium)\b",
                value,
                flags=re.IGNORECASE
            )[0]

            value = clean_value(value)

            if looks_like_name(value):
                return value

    return "Not detected"


# ============================================================
# REGISTER NUMBER
# ============================================================

def looks_like_register_number(value):
    if not value:
        return False

    value = clean_value(value)

    # Register numbers are usually alphanumeric
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\/\-_]{4,19}", value):
        return False

    # Reject obvious words
    bad_words = [
        "medium",
        "english",
        "marks",
        "candidate",
        "name",
        "number",
        "register",
    ]

    if value.lower() in bad_words:
        return False

    return True


def extract_register_number(text):
    text = normalize_ocr_text(text)

    # Create a single-line version for OCR where spaces/newlines
    # appear between parts of the label.
    single_line = re.sub(r"\s+", " ", text)

    # --------------------------------------------------------
    # 1. EXACT REGISTER LABELS FIRST
    # --------------------------------------------------------

    exact_patterns = [

        r"Register\s*No\.?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"Register\s*Number\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"Registration\s*No\.?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"Registration\s*Number\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"USN\s*(?:No\.?)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"Roll\s*(?:No\.?|Number)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"Enrollment\s*(?:No\.?|Number)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"Student\s*ID\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",

        r"Seat\s*(?:No\.?|Number)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",
    ]

    for pattern in exact_patterns:

        match = re.search(
            pattern,
            single_line,
            re.IGNORECASE
        )

        if match:

            value = clean_value(match.group(1))

            if looks_like_register_number(value):
                return value

    # --------------------------------------------------------
    # 2. LINE-BY-LINE SEARCH
    # --------------------------------------------------------

    for line in text.splitlines():

        line = clean_value(line)

        match = re.search(
            r"(?:Register|Registration|Reg\.?|USN|Roll|Enrollment|Seat)"
            r"\s*(?:No\.?|Number|ID)?"
            r"\s*[:\-]\s*"
            r"([A-Za-z0-9][A-Za-z0-9\/\-_]{4,19})",
            line,
            re.IGNORECASE
        )

        if match:

            value = clean_value(match.group(1))

            if looks_like_register_number(value):
                return value

    # --------------------------------------------------------
    # 3. OCR FALLBACK:
    # REGISTER ... NUMBER
    # --------------------------------------------------------

    nearby_pattern = re.search(
        r"(?:Register|Registration|Reg\.?|Roll|USN)"
        r".{0,40}?"
        r"\b(\d{8,15})\b",
        single_line,
        re.IGNORECASE
    )

    if nearby_pattern:

        value = nearby_pattern.group(1)

        if looks_like_register_number(value):
            return value

    # --------------------------------------------------------
    # 4. LAST FALLBACK: LONG NUMERIC VALUE
    # --------------------------------------------------------

    numbers = re.findall(
        r"\b\d{8,15}\b",
        single_line
    )

    if numbers:

        # Prefer numbers that look like IDs
        for number in numbers:

            # Avoid common marks/years
            if len(number) >= 8:
                return number

    return "Not detected"


# ============================================================
# DATE OF BIRTH
# ============================================================

def extract_date_of_birth(text):
    text = normalize_ocr_text(text)

    single_line = re.sub(r"\s+", " ", text)

    # --------------------------------------------------------
    # 1. DATE OF BIRTH LABEL
    # --------------------------------------------------------

    patterns = [

        r"Date\s+of\s+Birth\s*[:\-]?\s*"
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",

        r"DOB\s*[:\-]?\s*"
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",

        r"Birth\s+Date\s*[:\-]?\s*"
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            single_line,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    # --------------------------------------------------------
    # 2. GENERAL DATE FALLBACK
    # --------------------------------------------------------

    dates = re.findall(
        r"\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}\b",
        single_line
    )

    if dates:
        return dates[0]

    return "Not detected"


# ============================================================
# ACADEMIC INFORMATION DETECTION
# ============================================================

def has_academic_information(text):
    text_lower = text.lower()

    groups = {

        "marks": [
            "marks",
            "marks obtained",
            "maximum marks",
            "subject",
            "scholastic",
        ],

        "institution": [
            "university",
            "board",
            "college",
            "school",
            "institute",
        ],

        "course": [
            "course",
            "degree",
            "b.e",
            "btech",
            "b.tech",
            "m.e",
            "mtech",
            "diploma",
            "class",
            "semester",
        ],

        "result": [
            "percentage",
            "result",
            "grade",
            "pass",
            "passed",
            "division",
        ],
    }

    detected = {}

    for group, keywords in groups.items():

        detected[group] = any(
            keyword in text_lower
            for keyword in keywords
        )

    return detected


# ============================================================
# DOCUMENT IDENTIFIER
# ============================================================

def detect_document_identifier(text):
    text_lower = text.lower()

    identifiers = [
        "certificate",
        "register",
        "registration",
        "usn",
        "roll no",
        "enrollment",
        "serial no",
        "serial number",
        "document no",
        "marks card",
        "marksheet",
    ]

    return any(
        item in text_lower
        for item in identifiers
    )


# ============================================================
# EXTRACT ALL DETAILS
# ============================================================

def extract_details(text):
    text = normalize_ocr_text(text)

    candidate_name = extract_candidate_name(text)
    register_number = extract_register_number(text)
    date_of_birth = extract_date_of_birth(text)

    academic_info = has_academic_information(text)

    return {
        "candidate_name": candidate_name,
        "register_number": register_number,
        "date_of_birth": date_of_birth,

        # Compatibility with older templates/code
        "dob": date_of_birth,

        "academic_information": academic_info,

        "document_identifier": detect_document_identifier(text),
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_candidate_name(name):
    return (
        name
        and name != "Not detected"
        and looks_like_name(name)
    )


def validate_register_number(register_number):
    return (
        register_number
        and register_number != "Not detected"
        and looks_like_register_number(register_number)
    )


def validate_date_of_birth(dob):
    if not dob or dob == "Not detected":
        return False

    return bool(
        re.fullmatch(
            r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}",
            dob
        )
    )


# ============================================================
# MAIN VERIFICATION
# ============================================================

def verify_document(text, reference_details=None):
    """
    Verify extracted academic document information.

    Returns a dictionary so app.py can directly use:
        verification.get(...)
    """

    text = normalize_ocr_text(text)

    details = extract_details(text)

    checks = {}

    # --------------------------------------------------------
    # NAME CHECK
    # --------------------------------------------------------

    name_valid = validate_candidate_name(
        details["candidate_name"]
    )

    checks["candidate_name"] = {
        "status": "PASS" if name_valid else "FAIL",
        "value": details["candidate_name"],
        "message": (
            "Candidate name detected correctly."
            if name_valid
            else "Candidate name could not be reliably detected."
        )
    }

    # --------------------------------------------------------
    # REGISTER CHECK
    # --------------------------------------------------------

    register_valid = validate_register_number(
        details["register_number"]
    )

    checks["register_number"] = {
        "status": "PASS" if register_valid else "FAIL",
        "value": details["register_number"],
        "message": (
            "Register/identification number detected."
            if register_valid
            else "Register/identification number could not be reliably detected."
        )
    }

    # --------------------------------------------------------
    # DOB CHECK
    # --------------------------------------------------------

    dob_valid = validate_date_of_birth(
        details["date_of_birth"]
    )

    checks["date_of_birth"] = {
        "status": "PASS" if dob_valid else "FAIL",
        "value": details["date_of_birth"],
        "message": (
            "Date of birth detected."
            if dob_valid
            else "Date of birth could not be reliably detected."
        )
    }

    # --------------------------------------------------------
    # ACADEMIC INFORMATION CHECK
    # --------------------------------------------------------

    academic_info = details["academic_information"]

    academic_groups_detected = sum(
        1 for value in academic_info.values()
        if value
    )

    academic_valid = academic_groups_detected >= 2

    checks["academic_information"] = {
        "status": "PASS" if academic_valid else "REVIEW",
        "value": f"{academic_groups_detected}/4 groups detected",
        "message": (
            "Academic information detected."
            if academic_valid
            else "Limited academic information detected."
        )
    }

    # --------------------------------------------------------
    # DOCUMENT IDENTIFIER
    # --------------------------------------------------------

    identifier_valid = details["document_identifier"]

    checks["document_identifier"] = {
        "status": "PASS" if identifier_valid else "REVIEW",
        "value": (
            "Detected"
            if identifier_valid
            else "Not detected"
        ),
        "message": (
            "Document identifier information detected."
            if identifier_valid
            else "No clear document identifier detected."
        )
    }

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = 0.0

    if name_valid:
        score += 25

    if register_valid:
        score += 25

    if dob_valid:
        score += 20

    if academic_valid:
        score += 20

    if identifier_valid:
        score += 10

    score = round(score, 2)

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if score >= 80:
        status = "INFORMATION VERIFIED"

    elif score >= 50:
        status = "NEEDS REVIEW"

    else:
        status = "INSUFFICIENT INFORMATION"

    # --------------------------------------------------------
    # SUSPICIOUS INDICATORS
    # --------------------------------------------------------

    suspicious_indicators = []

    if not name_valid:
        suspicious_indicators.append({
            "check": "candidate_name",
            "status": "NEEDS REVIEW",
            "message": "Candidate name was not reliably extracted."
        })

    if not register_valid:
        suspicious_indicators.append({
            "check": "register_number",
            "status": "NEEDS REVIEW",
            "message": "Register number was not reliably extracted."
        })

    if not dob_valid:
        suspicious_indicators.append({
            "check": "date_of_birth",
            "status": "NEEDS REVIEW",
            "message": "Date of birth was not reliably extracted."
        })

    if not academic_valid:
        suspicious_indicators.append({
            "check": "academic_information",
            "status": "NEEDS REVIEW",
            "message": "Insufficient academic information detected."
        })

    # --------------------------------------------------------
    # EXPLANATION
    # --------------------------------------------------------

    if score >= 80:

        explanation = (
            "The document contains the expected academic "
            "information and identifiable fields."
        )

    elif score >= 50:

        explanation = (
            "Some important document information was detected, "
            "but manual review is recommended."
        )

    else:

        explanation = (
            "Important document information could not be "
            "reliably extracted. Manual verification is recommended."
        )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {
        "available": True,

        "status": status,

        "score": score,
        "verification_score": score,
        "overall_score": score,

        "details": details,

        "candidate_name": details["candidate_name"],
        "register_number": details["register_number"],
        "date_of_birth": details["date_of_birth"],

        "checks": checks,
        "verification_checks": checks,

        "suspicious_count": len(suspicious_indicators),

        "suspicious_indicators": suspicious_indicators,

        "explanation": explanation,
    }