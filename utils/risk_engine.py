def calculate_risk_score(
    verification_score,
    similarity_score,
    image_quality
):
    """
    Calculate an overall document verification score.

    Weights:
    OCR Verification   = 40%
    Visual Similarity  = 40%
    Image Quality      = 20%
    """

    # Convert image quality into a numerical score
    if image_quality == "Good":
        quality_score = 100
    elif image_quality == "Moderate":
        quality_score = 60
    elif image_quality == "Low":
        quality_score = 30
    else:
        quality_score = 0

    # If no reference document exists
    if similarity_score is None:
        overall_score = (
            verification_score * 0.67
            + quality_score * 0.33
        )
    else:
        overall_score = (
            verification_score * 0.40
            + similarity_score * 0.40
            + quality_score * 0.20
        )

    overall_score = round(overall_score, 2)

    # Determine final status
    if overall_score >= 80:
        status = "LOW RISK"

    elif overall_score >= 60:
        status = "NEEDS REVIEW"

    else:
        status = "SUSPICIOUS"

    return {
        "overall_score": overall_score,
        "quality_score": quality_score,
        "status": status
    }


def generate_risk_explanation(
    verification_score,
    similarity_score,
    image_quality,
    status
):
    reasons = []

    # OCR explanation
    if verification_score >= 75:
        reasons.append(
            "Most required academic information was successfully detected."
        )
    else:
        reasons.append(
            "Some required academic information could not be verified."
        )

    # Visual similarity explanation
    if similarity_score is None:
        reasons.append(
            "No reference document was available for visual comparison."
        )

    elif similarity_score >= 90:
        reasons.append(
            "The document shows high visual similarity with the reference."
        )

    elif similarity_score >= 70:
        reasons.append(
            "The document shows moderate visual similarity with the reference."
        )

    else:
        reasons.append(
            "The document shows low visual similarity with the reference."
        )

    # Image quality explanation
    if image_quality == "Good":
        reasons.append(
            "Document image quality is good enough for analysis."
        )

    elif image_quality == "Moderate":
        reasons.append(
            "Moderate image quality may affect OCR accuracy."
        )

    else:
        reasons.append(
            "Low image quality may reduce verification reliability."
        )

    # Final explanation
    if status == "LOW RISK":
        summary = (
            "The available verification signals are generally consistent."
        )

    elif status == "NEEDS REVIEW":
        summary = (
            "Some verification signals are acceptable, "
            "but manual review is recommended."
        )

    else:
        summary = (
            "The available verification signals show significant "
            "inconsistencies and the document should be reviewed manually."
        )

    return {
        "summary": summary,
        "reasons": reasons
    }