# ============================================================
# RISK ENGINE
# Academic Document Authenticity Validator
# ============================================================


def safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


# ============================================================
# CALCULATE OVERALL RISK / AUTHENTICITY SCORE
# ============================================================

def calculate_risk_score(
    verification_score,
    similarity_score,
    ml_anomaly_score,
    quality_score
):
    """
    Calculate the overall document verification score.

    Higher score = stronger evidence of consistency.

    Components:

    OCR / Information Verification   30%
    Visual Similarity                30%
    ML Pattern Consistency           25%
    Image Quality                    15%

    IMPORTANT:
    ML anomaly is converted into consistency:

        ML consistency = 100 - anomaly

    Example:

        anomaly = 95
        consistency = 5
    """

    verification_score = safe_float(
        verification_score
    )

    similarity_score = safe_float(
        similarity_score
    )

    ml_anomaly_score = safe_float(
        ml_anomaly_score
    )

    quality_score = safe_float(
        quality_score
    )

    # Keep all values within 0-100
    verification_score = max(
        0,
        min(100, verification_score)
    )

    similarity_score = max(
        0,
        min(100, similarity_score)
    )

    ml_anomaly_score = max(
        0,
        min(100, ml_anomaly_score)
    )

    quality_score = max(
        0,
        min(100, quality_score)
    )

    # Convert anomaly to consistency
    ml_consistency = 100 - ml_anomaly_score

    # --------------------------------------------------------
    # WEIGHTED SCORE
    # --------------------------------------------------------

    overall_score = (
        (verification_score * 0.30)
        +
        (similarity_score * 0.30)
        +
        (ml_consistency * 0.25)
        +
        (quality_score * 0.15)
    )

    return round(
        overall_score,
        2
    )


# ============================================================
# STATUS
# ============================================================

def get_risk_status(score):

    score = safe_float(score)

    if score >= 80:
        return "LOW RISK"

    elif score >= 60:
        return "NEEDS REVIEW"

    else:
        return "SUSPICIOUS"


# ============================================================
# GENERATE EXPLANATION
# ============================================================

def generate_risk_explanation(
    verification_score,
    similarity_score,
    ml_anomaly_score,
    image_quality
):
    """
    Generate a human-readable explanation.

    The wording is deliberately careful:
    anomaly detection is NOT treated as proof of fraud.
    """

    verification_score = safe_float(
        verification_score
    )

    similarity_score = safe_float(
        similarity_score
    )

    ml_anomaly_score = safe_float(
        ml_anomaly_score
    )

    messages = []

    # --------------------------------------------------------
    # OCR / INFORMATION
    # --------------------------------------------------------

    if verification_score >= 80:

        messages.append(
            "Required academic information was detected consistently."
        )

    elif verification_score >= 50:

        messages.append(
            "Some important academic information was detected, "
            "but additional verification is recommended."
        )

    else:

        messages.append(
            "Important academic information could not be "
            "reliably verified."
        )

    # --------------------------------------------------------
    # VISUAL SIMILARITY
    # --------------------------------------------------------

    if similarity_score >= 90:

        messages.append(
            "The document shows high visual similarity "
            "to the available reference documents."
        )

    elif similarity_score >= 70:

        messages.append(
            "The document shows moderate visual similarity "
            "to the available reference documents."
        )

    else:

        messages.append(
            "The document differs noticeably from the "
            "available reference documents."
        )

    # --------------------------------------------------------
    # ML ANALYSIS
    # --------------------------------------------------------

    if ml_anomaly_score >= 60:

        messages.append(
            "The ML analysis detected noticeable visual or "
            "structural deviation from the reference dataset."
        )

    elif ml_anomaly_score >= 40:

        messages.append(
            "The ML analysis detected moderate visual or "
            "structural deviation from the reference dataset."
        )

    else:

        messages.append(
            "The ML analysis found the document broadly "
            "consistent with the reference dataset."
        )

    # --------------------------------------------------------
    # IMAGE QUALITY
    # --------------------------------------------------------

    if image_quality == "Good":

        messages.append(
            "Image quality is good."
        )

    elif image_quality == "Moderate":

        messages.append(
            "Image quality is moderate."
        )

    elif image_quality == "Low":

        messages.append(
            "Low image quality may affect automated analysis."
        )

    return " ".join(messages)