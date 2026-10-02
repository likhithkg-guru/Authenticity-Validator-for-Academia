# ============================================================
# RISK ENGINE
# ============================================================


def safe_float(value, default=0.0):
    """
    Safely convert a value into float.
    Prevents errors when values arrive as strings.
    """

    try:

        if value is None:
            return float(default)

        if isinstance(value, str):

            value = value.strip()

            if value.endswith("%"):
                value = value[:-1]

            if value == "":
                return float(default)

        return float(value)

    except (
        TypeError,
        ValueError
    ):

        return float(default)


# ============================================================
# CALCULATE RISK SCORE
# ============================================================

def calculate_risk_score(
    verification_score,
    similarity_score,
    image_quality,
    ml_anomaly_score=None
):

    # --------------------------------------------------------
    # Convert everything to numbers
    # --------------------------------------------------------

    verification_score = safe_float(
        verification_score
    )

    similarity_score = safe_float(
        similarity_score
    )

    ml_anomaly_score = safe_float(
        ml_anomaly_score
    )

    # --------------------------------------------------------
    # Image quality
    # --------------------------------------------------------

    if isinstance(
        image_quality,
        (int, float)
    ):

        quality_score = safe_float(
            image_quality
        )

    else:

        quality_text = str(
            image_quality
        ).lower().strip()

        if quality_text == "good":

            quality_score = 100

        elif quality_text == "moderate":

            quality_score = 70

        elif quality_text == "low":

            quality_score = 40

        else:

            quality_score = 50

    # --------------------------------------------------------
    # Keep values between 0 and 100
    # --------------------------------------------------------

    verification_score = max(
        0,
        min(
            100,
            verification_score
        )
    )

    similarity_score = max(
        0,
        min(
            100,
            similarity_score
        )
    )

    quality_score = max(
        0,
        min(
            100,
            quality_score
        )
    )

    ml_anomaly_score = max(
        0,
        min(
            100,
            ml_anomaly_score
        )
    )

    # ========================================================
    # COMPONENTS
    # ========================================================

    components = {

        "verification": verification_score,

        "similarity": similarity_score,

        "quality": quality_score
    }

    weights = {

        "verification": 0.30,

        "similarity": 0.30,

        "quality": 0.15
    }

    # --------------------------------------------------------
    # ML component
    #
    # Anomaly score is BAD when high.
    # Therefore:
    #
    # ML consistency = 100 - anomaly score
    # --------------------------------------------------------

    if ml_anomaly_score is not None:

        components["ml"] = (
            100 - ml_anomaly_score
        )

        weights["ml"] = 0.25

    # ========================================================
    # NORMALIZE WEIGHTS
    # ========================================================

    total_weight = sum(
        weights.values()
    )

    if total_weight == 0:

        overall_score = 0

    else:

        overall_score = sum(

            safe_float(
                components[name]
            )
            *
            safe_float(
                weight
            )

            for name, weight
            in weights.items()

        ) / total_weight

    overall_score = round(
        max(
            0,
            min(
                100,
                overall_score
            )
        ),
        2
    )

    # ========================================================
    # STATUS
    # ========================================================

    if overall_score >= 80:

        status = "LOW RISK"

    elif overall_score >= 60:

        status = "NEEDS REVIEW"

    else:

        status = "SUSPICIOUS"

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "overall_score":
            overall_score,

        "status":
            status,

        "verification_score":
            verification_score,

        "similarity_score":
            similarity_score,

        "image_quality_score":
            quality_score,

        "ml_anomaly_score":
            ml_anomaly_score,

        "ml_consistency_score":
            round(
                100 - ml_anomaly_score,
                2
            ),

        "components":
            components,

        "weights":
            weights
    }


# ============================================================
# RISK EXPLANATION
# ============================================================

def generate_risk_explanation(
    verification_score,
    similarity_score,
    image_quality,
    ml_anomaly_score=None
):

    verification_score = safe_float(
        verification_score
    )

    similarity_score = safe_float(
        similarity_score
    )

    ml_anomaly_score = safe_float(
        ml_anomaly_score
    )

    reasons = []

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    if verification_score >= 80:

        reasons.append(
            "Required academic information "
            "was detected consistently."
        )

    elif verification_score >= 50:

        reasons.append(
            "Some required academic information "
            "requires review."
        )

    else:

        reasons.append(
            "Important academic information "
            "could not be verified."
        )

    # --------------------------------------------------------
    # Similarity
    # --------------------------------------------------------

    if similarity_score >= 90:

        reasons.append(
            "The document has strong visual "
            "similarity with the reference."
        )

    elif similarity_score >= 70:

        reasons.append(
            "The document has moderate visual "
            "similarity with the reference."
        )

    else:

        reasons.append(
            "The document differs noticeably "
            "from the available reference documents."
        )

    # --------------------------------------------------------
    # Image quality
    # --------------------------------------------------------

    quality_text = str(
        image_quality
    ).lower()

    if quality_text == "good":

        reasons.append(
            "Image quality is good."
        )

    elif quality_text == "moderate":

        reasons.append(
            "Image quality is moderate."
        )

    elif quality_text == "low":

        reasons.append(
            "Low image quality may affect analysis."
        )

    # --------------------------------------------------------
    # ML
    # --------------------------------------------------------

    if ml_anomaly_score >= 60:

        reasons.append(
            "The ML analysis detected noticeable "
            "visual or structural deviation from "
            "the reference dataset."
        )

    elif ml_anomaly_score >= 40:

        reasons.append(
            "The ML analysis detected some "
            "visual or structural deviation."
        )

    else:

        reasons.append(
            "The ML analysis found patterns broadly "
            "consistent with the reference dataset."
        )

    # --------------------------------------------------------
    # Final explanation
    # --------------------------------------------------------

    return " ".join(
        reasons
    )