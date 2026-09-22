def calculate_risk_score(
    verification_score,
    similarity_score,
    image_quality,
    ml_anomaly_score=None
):
    """
    Calculate overall document verification score.

    Weights:
    OCR Verification   = 30%
    Visual Similarity  = 30%
    ML Analysis        = 25%
    Image Quality      = 15%

    Important:
    ML anomaly score represents deviation from the
    reference dataset. It does not independently prove
    that a document is fraudulent.
    """

    # -----------------------------------------
    # Image quality score
    # -----------------------------------------

    if image_quality == "Good":
        quality_score = 100

    elif image_quality == "Moderate":
        quality_score = 60

    elif image_quality == "Low":
        quality_score = 30

    else:
        quality_score = 0


    # -----------------------------------------
    # Visual similarity score
    # -----------------------------------------

    if similarity_score is None:
        similarity_component = None
    else:
        similarity_component = similarity_score


    # -----------------------------------------
    # ML score
    #
    # ML anomaly score:
    # 0   = normal pattern
    # 100 = highly anomalous pattern
    #
    # Convert it into a positive verification score.
    # -----------------------------------------

    if ml_anomaly_score is None:
        ml_component = None
    else:
        ml_component = max(
            0,
            100 - ml_anomaly_score
        )


    # -----------------------------------------
    # Calculate overall score
    # -----------------------------------------

    components = []
    weights = []

    # OCR
    components.append(
        verification_score
    )
    weights.append(0.30)


    # Visual similarity
    if similarity_component is not None:

        components.append(
            similarity_component
        )

        weights.append(0.30)


    # ML
    if ml_component is not None:

        components.append(
            ml_component
        )

        weights.append(0.25)


    # Image quality
    components.append(
        quality_score
    )

    weights.append(0.15)


    # -----------------------------------------
    # Normalize weights if some component
    # is unavailable
    # -----------------------------------------

    total_weight = sum(weights)

    overall_score = sum(
        component * weight
        for component, weight
        in zip(components, weights)
    )

    overall_score = (
        overall_score / total_weight
    )


    overall_score = round(
        overall_score,
        2
    )


    # -----------------------------------------
    # Risk status
    # -----------------------------------------

    if overall_score >= 80:

        status = "LOW RISK"

    elif overall_score >= 60:

        status = "NEEDS REVIEW"

    else:

        status = "SUSPICIOUS"


    return {
        "overall_score": overall_score,
        "quality_score": quality_score,
        "status": status,
        "ml_score": ml_anomaly_score
    }


def generate_risk_explanation(
    verification_score,
    similarity_score,
    image_quality,
    status,
    ml_anomaly_score=None
):

    reasons = []


    # -----------------------------------------
    # OCR verification
    # -----------------------------------------

    if verification_score >= 75:

        reasons.append(
            "Most required academic information "
            "was successfully detected."
        )

    else:

        reasons.append(
            "Some required academic information "
            "could not be verified."
        )


    # -----------------------------------------
    # Visual similarity
    # -----------------------------------------

    if similarity_score is None:

        reasons.append(
            "No reference document was available "
            "for visual comparison."
        )

    elif similarity_score >= 90:

        reasons.append(
            "The document shows high visual "
            "similarity with the reference."
        )

    elif similarity_score >= 70:

        reasons.append(
            "The document shows moderate visual "
            "similarity with the reference."
        )

    else:

        reasons.append(
            "The document shows low visual "
            "similarity with the reference."
        )


    # -----------------------------------------
    # ML anomaly analysis
    # -----------------------------------------

    if ml_anomaly_score is None:

        reasons.append(
            "ML anomaly analysis was unavailable."
        )

    elif ml_anomaly_score >= 60:

        reasons.append(
            "The ML model detected noticeable "
            "visual and layout deviation from "
            "the reference dataset."
        )

    elif ml_anomaly_score >= 40:

        reasons.append(
            "The ML model detected some deviation "
            "from the reference dataset."
        )

    else:

        reasons.append(
            "The ML model found the document's "
            "visual and layout pattern broadly "
            "consistent with the references."
        )


    # -----------------------------------------
    # Image quality
    # -----------------------------------------

    if image_quality == "Good":

        reasons.append(
            "Document image quality is good enough "
            "for analysis."
        )

    elif image_quality == "Moderate":

        reasons.append(
            "Moderate image quality may affect "
            "OCR accuracy."
        )

    else:

        reasons.append(
            "Low image quality may reduce "
            "verification reliability."
        )


    # -----------------------------------------
    # Overall summary
    # -----------------------------------------

    if status == "LOW RISK":

        summary = (
            "The available verification signals "
            "are generally consistent."
        )

    elif status == "NEEDS REVIEW":

        summary = (
            "Some verification signals are acceptable, "
            "but manual review is recommended."
        )

    else:

        summary = (
            "The available verification signals show "
            "significant inconsistencies and the "
            "document should be reviewed manually."
        )


    return {
        "summary": summary,
        "reasons": reasons
    }