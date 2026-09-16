import os
import cv2
import fitz
import numpy as np
from sklearn.ensemble import IsolationForest


def pdf_to_feature_vector(pdf_path):
    """
    Convert the first page of a PDF into a numerical feature vector.
    """

    try:
        document = fitz.open(pdf_path)

        if len(document) == 0:
            document.close()
            return None

        page = document[0]

        # Render PDF page as image
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

        # Resize every document to the same size
        image = cv2.resize(
            image,
            (64, 64)
        )

        # Normalize pixel values
        image = image.astype(np.float32) / 255.0

        # Convert image into one-dimensional vector
        feature_vector = image.flatten()

        return feature_vector

    except Exception as e:
        print("ML feature extraction error:", e)
        return None


def train_anomaly_model(reference_folder):
    """
    Train Isolation Forest using reference documents.
    """

    if not os.path.exists(reference_folder):
        return None, "Reference folder not found"

    reference_files = [
        file for file in os.listdir(reference_folder)
        if file.lower().endswith(".pdf")
    ]

    # Need multiple samples for meaningful training
    if len(reference_files) < 3:
        return None, "Insufficient reference documents"

    features = []

    for filename in reference_files:

        filepath = os.path.join(
            reference_folder,
            filename
        )

        feature_vector = pdf_to_feature_vector(filepath)

        if feature_vector is not None:
            features.append(feature_vector)

    if len(features) < 3:
        return None, "Insufficient valid reference documents"

    X = np.array(features)

    # Isolation Forest
    model = IsolationForest(
        n_estimators=100,
        contamination="auto",
        random_state=42
    )

    model.fit(X)

    return model, None


def analyze_with_ml(uploaded_path, reference_folder):
    """
    Analyze uploaded document using Isolation Forest.
    """

    model, error = train_anomaly_model(reference_folder)

    if error:
        return {
            "available": False,
            "status": "NOT AVAILABLE",
            "anomaly_score": None,
            "explanation": error
        }

    uploaded_features = pdf_to_feature_vector(uploaded_path)

    if uploaded_features is None:
        return {
            "available": False,
            "status": "ERROR",
            "anomaly_score": None,
            "explanation": "Unable to extract ML features from document."
        }

    X_test = np.array([uploaded_features])

    # Prediction:
    # 1  = normal
    # -1 = anomaly
    prediction = model.predict(X_test)[0]

    # Decision function
    raw_score = model.decision_function(X_test)[0]

    # Convert into a simple 0–100 score
    anomaly_score = max(
        0,
        min(
            100,
            round(50 + (raw_score * 100), 2)
        )
    )

    if prediction == 1:
        status = "NORMAL PATTERN"
    else:
        status = "ANOMALOUS PATTERN"

    if prediction == 1:
        explanation = (
            "The document follows visual patterns similar to "
            "the available reference documents."
        )
    else:
        explanation = (
            "The document differs noticeably from the visual "
            "patterns learned from the reference documents."
        )

    return {
        "available": True,
        "status": status,
        "anomaly_score": anomaly_score,
        "explanation": explanation
    }