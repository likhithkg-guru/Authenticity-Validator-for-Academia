import re


def normalize_text(text):
    if not text:
        return ""

    text = text.lower()

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_any(text, words):
    return any(word in text for word in words)


def count_matches(text, words):
    return sum(
        1 for word in words
        if word in text
    )


def classify_document(text):

    text = normalize_text(text)

    if not text:
        return {
            "document_type": "UNKNOWN",
            "confidence": 0,
            "scores": {},
            "matched_keywords": []
        }

    scores = {}
    matched = {}

    # =========================================================
    # MARKSHEET
    # =========================================================

    marks_score = 0
    marks_matches = []

    marks_keywords = [
        "marks",
        "mark",
        "marks obtained",
        "total marks",
        "percentage",
        "subject",
        "grade",
        "semester examination",
        "internal marks",
        "external marks"
    ]

    for keyword in marks_keywords:

        if keyword in text:

            marks_matches.append(keyword)

            if keyword in [
                "marks",
                "marks obtained",
                "total marks",
                "percentage"
            ]:
                marks_score += 2

            else:
                marks_score += 1

    # Strong combination: marks + percentage
    if (
        contains_any(
            text,
            ["marks", "marks obtained", "total marks"]
        )
        and
        "percentage" in text
    ):

        marks_score += 5

    # Subject + marks
    if (
        "subject" in text
        and contains_any(
            text,
            ["marks", "total marks", "marks obtained"]
        )
    ):

        marks_score += 4

    # Semester + marks
    if (
        "semester" in text
        and contains_any(
            text,
            ["marks", "grade", "percentage"]
        )
    ):

        marks_score += 4

    # Detect multiple mark-like numbers
    number_pattern = r"\b(?:[0-9]{1,3})\b"

    numbers = re.findall(
        number_pattern,
        text
    )

    if len(numbers) >= 3:

        marks_score += 3
        marks_matches.append(
            "multiple numerical values"
        )

    scores["MARKSHEET"] = marks_score
    matched["MARKSHEET"] = marks_matches

    # =========================================================
    # DEGREE CERTIFICATE
    # =========================================================

    degree_score = 0
    degree_matches = []

    degree_keywords = [
        "degree certificate",
        "has been awarded",
        "bachelor of",
        "master of",
        "bachelor",
        "master",
        "degree",
        "conferred",
        "graduation"
    ]

    for keyword in degree_keywords:

        if keyword in text:

            degree_matches.append(keyword)
            degree_score += 2

    if (
        "has been awarded" in text
        and contains_any(
            text,
            ["bachelor", "master", "degree"]
        )
    ):

        degree_score += 5

    scores["DEGREE_CERTIFICATE"] = degree_score
    matched["DEGREE_CERTIFICATE"] = degree_matches

    # =========================================================
    # PROVISIONAL CERTIFICATE
    # =========================================================

    provisional_score = 0
    provisional_matches = []

    provisional_keywords = [
        "provisional certificate",
        "provisional",
        "provisionally",
        "completion of the requirements"
    ]

    for keyword in provisional_keywords:

        if keyword in text:

            provisional_matches.append(keyword)
            provisional_score += 3

    scores["PROVISIONAL_CERTIFICATE"] = provisional_score
    matched["PROVISIONAL_CERTIFICATE"] = provisional_matches

    # =========================================================
    # TRANSCRIPT
    # =========================================================

    transcript_score = 0
    transcript_matches = []

    transcript_keywords = [
        "transcript",
        "academic transcript",
        "semester",
        "credits",
        "grade",
        "cgpa",
        "course"
    ]

    for keyword in transcript_keywords:

        if keyword in text:

            transcript_matches.append(keyword)
            transcript_score += 2

    if (
        "transcript" in text
        and "semester" in text
    ):

        transcript_score += 5

    scores["TRANSCRIPT"] = transcript_score
    matched["TRANSCRIPT"] = transcript_matches

    # =========================================================
    # DIPLOMA
    # =========================================================

    diploma_score = 0
    diploma_matches = []

    diploma_keywords = [
        "diploma certificate",
        "diploma",
        "polytechnic",
        "diploma in"
    ]

    for keyword in diploma_keywords:

        if keyword in text:

            diploma_matches.append(keyword)
            diploma_score += 3

    scores["DIPLOMA_CERTIFICATE"] = diploma_score
    matched["DIPLOMA_CERTIFICATE"] = diploma_matches

    # =========================================================
    # BONAFIDE
    # =========================================================

    bonafide_score = 0
    bonafide_matches = []

    bonafide_keywords = [
        "bonafide certificate",
        "bonafide",
        "bonafide student",
        "is a student of"
    ]

    for keyword in bonafide_keywords:

        if keyword in text:

            bonafide_matches.append(keyword)
            bonafide_score += 3

    scores["BONAFIDE_CERTIFICATE"] = bonafide_score
    matched["BONAFIDE_CERTIFICATE"] = bonafide_matches

    # =========================================================
    # TRANSFER CERTIFICATE
    # =========================================================

    transfer_score = 0
    transfer_matches = []

    transfer_keywords = [
        "transfer certificate",
        "transferred",
        "left the institution"
    ]

    for keyword in transfer_keywords:

        if keyword in text:

            transfer_matches.append(keyword)
            transfer_score += 4

    scores["TRANSFER_CERTIFICATE"] = transfer_score
    matched["TRANSFER_CERTIFICATE"] = transfer_matches

    # =========================================================
    # MIGRATION CERTIFICATE
    # =========================================================

    migration_score = 0
    migration_matches = []

    migration_keywords = [
        "migration certificate",
        "migration",
        "migrated"
    ]

    for keyword in migration_keywords:

        if keyword in text:

            migration_matches.append(keyword)
            migration_score += 4

    scores["MIGRATION_CERTIFICATE"] = migration_score
    matched["MIGRATION_CERTIFICATE"] = migration_matches

    # =========================================================
    # ACHIEVEMENT CERTIFICATE
    # =========================================================

    achievement_score = 0
    achievement_matches = []

    achievement_keywords = [
        "achievement certificate",
        "certificate of achievement",
        "participation certificate",
        "successfully participated",
        "award"
    ]

    for keyword in achievement_keywords:

        if keyword in text:

            achievement_matches.append(keyword)
            achievement_score += 3

    scores["ACHIEVEMENT_CERTIFICATE"] = achievement_score
    matched["ACHIEVEMENT_CERTIFICATE"] = achievement_matches

    # =========================================================
    # SCHOOL MARKSHEET
    # =========================================================

    school_score = 0
    school_matches = []

    school_keywords = [
        "sslc",
        "10th standard",
        "12th standard",
        "class x",
        "class xii",
        "secondary school",
        "higher secondary",
        "pu examination"
    ]

    for keyword in school_keywords:

        if keyword in text:

            school_matches.append(keyword)
            school_score += 4

    if (
        school_score > 0
        and marks_score > 0
    ):

        school_score += 6

    scores["SCHOOL_MARKSHEET"] = school_score
    matched["SCHOOL_MARKSHEET"] = school_matches

    # =========================================================
    # FIND BEST TYPE
    # =========================================================

    best_type = max(
        scores,
        key=scores.get
    )

    best_score = scores[best_type]

    # =========================================================
    # CONFIDENCE
    # =========================================================

    if best_score == 0:

        return {
            "document_type": "UNKNOWN",
            "confidence": 0,
            "scores": scores,
            "matched_keywords": []
        }

    # Confidence is based on strength of evidence,
    # not number of possible keywords.

    confidence = min(
        95,
        35 + (best_score * 6)
    )

    # If there is a clear second-best category,
    # reduce confidence slightly.
    sorted_scores = sorted(
        scores.values(),
        reverse=True
    )

    if len(sorted_scores) >= 2:

        second_score = sorted_scores[1]

        if (
            second_score > 0
            and best_score - second_score <= 2
        ):

            confidence -= 10

    confidence = max(
        0,
        round(confidence, 2)
    )

    # =========================================================
    # UNKNOWN
    # =========================================================

    if best_score < 4:

        best_type = "UNKNOWN"
        confidence = 0

    return {
        "document_type": best_type,
        "confidence": confidence,
        "scores": scores,
        "matched_keywords": matched.get(
            best_type,
            []
        )
    }