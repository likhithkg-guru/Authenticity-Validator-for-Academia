import os
import cv2
import fitz
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# --------------------------------------------------
# Convert PDF first page to grayscale image
# --------------------------------------------------

def pdf_to_image(pdf_path):

    try:
        document = fitz.open(pdf_path)

        if len(document) == 0:
            document.close()
            return None

        page = document[0]

        pix = page.get_pixmap(
            matrix=fitz.Matrix(1.5, 1.5),
            colorspace=fitz.csGRAY
        )

        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        )

        image = image.reshape(
            pix.height,
            pix.width
        )

        document.close()

        return image

    except Exception as e:

        print("PDF image error:", e)

        return None


# --------------------------------------------------
# Extract document features
# --------------------------------------------------

def extract_features(pdf_path):

    image = pdf_to_image(pdf_path)

    if image is None:
        return None

    image = cv2.resize(
        image,
        (800, 1100)
    )

    normalized = image.astype(
        np.float32
    ) / 255.0

    # 1. Brightness
    brightness = np.mean(normalized)

    # 2. Contrast
    contrast = np.std(normalized)

    # 3. Blur / sharpness
    blur_score = cv2.Laplacian(
        image,
        cv2.CV_64F
    ).var()

    blur_score = min(
        blur_score / 1000,
        1.0
    )

    # 4. Edge density
    edges = cv2.Canny(
        image,
        100,
        200
    )

    edge_density = np.mean(
        edges > 0
    )

    # 5. Dark pixel ratio
    dark_pixels = np.mean(
        normalized < 0.5
    )

    # 6. White-space ratio
    white_space = np.mean(
        normalized > 0.9
    )

    # 7. Aspect ratio
    height, width = image.shape

    aspect_ratio = width / height

    # 8. Horizontal structure
    horizontal_projection = np.mean(
        normalized,
        axis=1
    )

    horizontal_variation = np.std(
        horizontal_projection
    )

    # 9. Vertical structure
    vertical_projection = np.mean(
        normalized,
        axis=0
    )

    vertical_variation = np.std(
        vertical_projection
    )

    # 10. Center brightness
    center = normalized[
        height // 4:3 * height // 4,
        width // 4:3 * width // 4
    ]

    center_brightness = np.mean(
        center
    )

    features = np.array([
        brightness,
        contrast,
        blur_score,
        edge_density,
        dark_pixels,
        white_space,
        aspect_ratio,
        horizontal_variation,
        vertical_variation,
        center_brightness
    ])

    return features


# --------------------------------------------------
# Load reference documents
# --------------------------------------------------

def load_reference_features(reference_folder):

    features = []
    filenames = []

    if not os.path.exists(
        reference_folder
    ):
        return np.array([]), []

    reference_files = [
        file
        for file in os.listdir(
            reference_folder
        )
        if file.lower().endswith(".pdf")
    ]

    for filename in reference_files:

        filepath = os.path.join(
            reference_folder,
            filename
        )

        feature_vector = extract_features(
            filepath
        )

        if feature_vector is not None:

            features.append(
                feature_vector
            )

            filenames.append(
                filename
            )

    if not features:

        return np.array([]), []

    return np.array(features), filenames


# --------------------------------------------------
# Isolation Forest analysis
# --------------------------------------------------

def analyze_with_ml(
    uploaded_path,
    reference_folder
):

    # Load reference features
    reference_features, filenames = (
        load_reference_features(
            reference_folder
        )
    )

    # Need at least 3 references
    if len(reference_features) < 3:

        return {
            "available": False,
            "status": "NOT AVAILABLE",
            "anomaly_score": None,
            "prediction": None,
            "reference_count": len(
                reference_features
            ),
            "explanation": (
                "At least 3 reference documents "
                "are required for Isolation Forest analysis."
            )
        }

    # Extract uploaded document features
    uploaded_features = extract_features(
        uploaded_path
    )

    if uploaded_features is None:

        return {
            "available": False,
            "status": "ERROR",
            "anomaly_score": None,
            "prediction": None,
            "reference_count": len(
                reference_features
            ),
            "explanation": (
                "Unable to extract features "
                "from the uploaded document."
            )
        }

    # --------------------------------------------------
    # Scale features
    # --------------------------------------------------

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        reference_features
    )

    uploaded_scaled = scaler.transform(
        uploaded_features.reshape(1, -1)
    )

    # --------------------------------------------------
    # Create Isolation Forest
    # --------------------------------------------------

    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42
    )

    # Train using reference documents
    model.fit(
        X_scaled
    )

    # --------------------------------------------------
    # Predict uploaded document
    # --------------------------------------------------

    prediction = model.predict(
        uploaded_scaled
    )[0]

    # 1  = normal
    # -1 = anomaly

    # --------------------------------------------------
    # Calculate normalized anomaly score
    # --------------------------------------------------

    reference_scores = model.score_samples(
        X_scaled
    )

    uploaded_score = model.score_samples(
        uploaded_scaled
    )[0]

    minimum_score = np.min(
        reference_scores
    )

    maximum_score = np.max(
        reference_scores
    )

    if maximum_score == minimum_score:

        anomaly_score = 0

    else:

        anomaly_score = (
            (
                maximum_score
                - uploaded_score
            )
            /
            (
                maximum_score
                - minimum_score
            )
        ) * 100

    anomaly_score = max(
        0,
        min(
            100,
            anomaly_score
        )
    )

    anomaly_score = round(
        anomaly_score,
        2
    )

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    if prediction == 1:

        status = "NORMAL PATTERN"

        explanation = (
            "The document follows a feature pattern "
            "consistent with the reference dataset."
        )

    else:

        status = "ANOMALOUS PATTERN"

        explanation = (
            "The document shows feature patterns "
            "that differ from the reference dataset "
            "and should be reviewed."
        )

    # --------------------------------------------------
    # Return result
    # --------------------------------------------------

    return {

        "available": True,

        "status": status,

        "anomaly_score": anomaly_score,

        "prediction": int(
            prediction
        ),

        "reference_count": len(
            reference_features
        ),

        "explanation": explanation
    }