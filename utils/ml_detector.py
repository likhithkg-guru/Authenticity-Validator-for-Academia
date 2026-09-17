import os
import cv2
import fitz
import numpy as np


def pdf_to_feature_vector(pdf_path):
    """
    Convert the first page of a PDF into a numerical
    feature vector using image characteristics.
    """

    try:
        document = fitz.open(pdf_path)

        if len(document) == 0:
            document.close()
            return None

        page = document[0]

        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))

        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        )

        channels = pix.n

        image = image.reshape(
            pix.height,
            pix.width,
            channels
        )

        if channels == 4:
            image = cv2.cvtColor(
                image,
                cv2.COLOR_RGBA2GRAY
            )
        else:
            image = cv2.cvtColor(
                image,
                cv2.COLOR_RGB2GRAY
            )

        document.close()

        # Standard size
        image = cv2.resize(
            image,
            (64, 64)
        )

        # Normalize
        image = image.astype(np.float32) / 255.0

        return image.flatten()

    except Exception as e:

        print("Feature extraction error:", e)

        return None


def load_reference_features(reference_folder):

    features = []

    if not os.path.exists(reference_folder):
        return features

    files = [
        file
        for file in os.listdir(reference_folder)
        if file.lower().endswith(".pdf")
    ]

    for filename in files:

        filepath = os.path.join(
            reference_folder,
            filename
        )

        feature = pdf_to_feature_vector(filepath)

        if feature is not None:
            features.append(feature)

    return features


def calculate_anomaly_score(
    uploaded_feature,
    reference_features
):
    """
    Calculate how different the uploaded document is
    from the reference document patterns.

    This uses normalized image distance.
    """

    distances = []

    for reference in reference_features:

        distance = np.mean(
            np.abs(
                uploaded_feature - reference
            )
        )

        distances.append(distance)

    if not distances:
        return None

    # Use the closest reference pattern
    minimum_distance = min(distances)

    # Convert distance to similarity-style score
    score = 100 - (
        minimum_distance * 100
    )

    score = max(
        0,
        min(
            100,
            round(score, 2)
        )
    )

    return score


def analyze_with_ml(
    uploaded_path,
    reference_folder
):
    """
    Prototype ML-style anomaly analysis.
    """

    reference_features = load_reference_features(
        reference_folder
    )

    # Need reference documents
    if len(reference_features) < 3:

        return {
            "available": False,
            "status": "NOT AVAILABLE",
            "anomaly_score": None,
            "explanation": (
                "At least 3 valid reference documents "
                "are required for anomaly analysis."
            )
        }

    uploaded_feature = pdf_to_feature_vector(
        uploaded_path
    )

    if uploaded_feature is None:

        return {
            "available": False,
            "status": "ERROR",
            "anomaly_score": None,
            "explanation": (
                "Unable to extract document features."
            )
        }

    similarity_score = calculate_anomaly_score(
        uploaded_feature,
        reference_features
    )

    if similarity_score is None:

        return {
            "available": False,
            "status": "ERROR",
            "anomaly_score": None,
            "explanation": (
                "Unable to calculate document anomaly."
            )
        }

    # Convert similarity into anomaly score
    anomaly_score = round(
        100 - similarity_score,
        2
    )

    if anomaly_score <= 25:

        status = "NORMAL PATTERN"

        explanation = (
            "The document follows visual patterns "
            "similar to the available reference documents."
        )

    elif anomaly_score <= 50:

        status = "MODERATE ANOMALY"

        explanation = (
            "The document shows some visual differences "
            "from the available reference documents."
        )

    else:

        status = "ANOMALOUS PATTERN"

        explanation = (
            "The document differs noticeably from "
            "the visual patterns in the reference set."
        )

    return {
        "available": True,
        "status": status,
        "anomaly_score": anomaly_score,
        "explanation": explanation
    }