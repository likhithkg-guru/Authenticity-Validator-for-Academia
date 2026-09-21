import os
import cv2
import fitz
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------
# Convert PDF first page into grayscale image
# ---------------------------------------------------------
def pdf_to_gray(pdf_path):

    try:
        document = fitz.open(pdf_path)

        if len(document) == 0:
            document.close()
            return None

        page = document[0]

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            colorspace=fitz.csRGB
        )

        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        )

        image = image.reshape(
            pix.height,
            pix.width,
            3
        )

        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2GRAY
        )

        document.close()

        return image

    except Exception:
        return None


# ---------------------------------------------------------
# Extract visual and layout features
# ---------------------------------------------------------
def extract_features(pdf_path):

    image = pdf_to_gray(pdf_path)

    if image is None:
        return None

    image = cv2.resize(
        image,
        (800, 1100)
    )

    features = []

    # Global brightness
    features.append(
        np.mean(image)
    )

    # Contrast
    features.append(
        np.std(image)
    )

    # Sharpness
    blur_score = cv2.Laplacian(
        image,
        cv2.CV_64F
    ).var()

    features.append(
        blur_score
    )

    # Edge density
    edges = cv2.Canny(
        image,
        100,
        200
    )

    features.append(
        np.mean(edges > 0)
    )

    # Dark pixel ratio
    features.append(
        np.mean(image < 100)
    )

    # White pixel ratio
    features.append(
        np.mean(image > 240)
    )

    # Aspect ratio
    height, width = image.shape

    features.append(
        width / height
    )

    # -----------------------------------------------------
    # Horizontal layout regions
    # -----------------------------------------------------

    horizontal_regions = np.array_split(
        image,
        10,
        axis=0
    )

    for region in horizontal_regions:

        features.append(
            np.mean(region)
        )

        features.append(
            np.mean(region < 100)
        )

        region_edges = cv2.Canny(
            region,
            100,
            200
        )

        features.append(
            np.mean(region_edges > 0)
        )

    # -----------------------------------------------------
    # Vertical layout regions
    # -----------------------------------------------------

    vertical_regions = np.array_split(
        image,
        10,
        axis=1
    )

    for region in vertical_regions:

        features.append(
            np.mean(region)
        )

        features.append(
            np.mean(region < 100)
        )

        region_edges = cv2.Canny(
            region,
            100,
            200
        )

        features.append(
            np.mean(region_edges > 0)
        )

    # -----------------------------------------------------
    # Horizontal projection
    # -----------------------------------------------------

    horizontal_projection = np.mean(
        image < 180,
        axis=1
    )

    features.append(
        np.mean(horizontal_projection)
    )

    features.append(
        np.std(horizontal_projection)
    )

    # -----------------------------------------------------
    # Vertical projection
    # -----------------------------------------------------

    vertical_projection = np.mean(
        image < 180,
        axis=0
    )

    features.append(
        np.mean(vertical_projection)
    )

    features.append(
        np.std(vertical_projection)
    )

    # -----------------------------------------------------
    # Center region
    # -----------------------------------------------------

    center = image[
        275:825,
        200:600
    ]

    features.append(
        np.mean(center)
    )

    features.append(
        np.mean(center < 100)
    )

    return np.array(
        features,
        dtype=np.float64
    )


# ---------------------------------------------------------
# Calculate statistical distance from reference documents
# ---------------------------------------------------------
def calculate_reference_deviation(
    reference_features,
    uploaded_features
):

    # Calculate mean and standard deviation
    mean = np.mean(
        reference_features,
        axis=0
    )

    std = np.std(
        reference_features,
        axis=0
    )

    # Prevent division by zero
    std[std < 1e-6] = 1e-6

    # Z-score for each feature
    z_scores = np.abs(
        (uploaded_features - mean) / std
    )

    # Average deviation
    deviation = np.mean(
        z_scores
    )

    # Convert to 0-100 scale
    deviation_score = (
        deviation / (deviation + 1)
    ) * 100

    return round(
        float(deviation_score),
        2
    )


# ---------------------------------------------------------
# Main ML analysis
# ---------------------------------------------------------
def analyze_with_ml(
    uploaded_path,
    reference_folder
):

    result = {
        "available": False,
        "anomaly_score": 0,
        "prediction": 0,
        "status": "ML UNAVAILABLE",
        "reference_count": 0,
        "explanation": ""
    }

    # Check uploaded document
    if not os.path.exists(
        uploaded_path
    ):

        result["explanation"] = (
            "Uploaded document could not be found."
        )

        return result

    # Check reference folder
    if not os.path.exists(
        reference_folder
    ):

        result["explanation"] = (
            "Reference document folder was not found."
        )

        return result

    # -----------------------------------------------------
    # Find reference PDFs
    # -----------------------------------------------------

    reference_files = [
        file
        for file in os.listdir(reference_folder)
        if file.lower().endswith(".pdf")
    ]

    result["reference_count"] = len(
        reference_files
    )

    if len(reference_files) < 5:

        result["explanation"] = (
            "At least 5 reference documents "
            "are recommended for anomaly analysis."
        )

        return result

    # -----------------------------------------------------
    # Extract uploaded features
    # -----------------------------------------------------

    uploaded_features = extract_features(
        uploaded_path
    )

    if uploaded_features is None:

        result["explanation"] = (
            "Unable to extract visual features "
            "from the uploaded document."
        )

        return result

    # -----------------------------------------------------
    # Extract reference features
    # -----------------------------------------------------

    reference_features = []

    for filename in reference_files:

        filepath = os.path.join(
            reference_folder,
            filename
        )

        features = extract_features(
            filepath
        )

        if features is not None:

            reference_features.append(
                features
            )

    if len(reference_features) < 5:

        result["explanation"] = (
            "Not enough valid reference documents "
            "could be analyzed."
        )

        return result

    reference_features = np.array(
        reference_features
    )

    # -----------------------------------------------------
    # Scale features
    # -----------------------------------------------------

    scaler = StandardScaler()

    scaled_reference = scaler.fit_transform(
        reference_features
    )

    scaled_uploaded = scaler.transform(
        uploaded_features.reshape(1, -1)
    )

    # -----------------------------------------------------
    # Isolation Forest
    # -----------------------------------------------------

    model = IsolationForest(
        n_estimators=500,
        max_samples="auto",
        contamination="auto",
        random_state=42
    )

    model.fit(
        scaled_reference
    )

    prediction = model.predict(
        scaled_uploaded
    )[0]

    decision_score = model.decision_function(
        scaled_uploaded
    )[0]

    # Convert Isolation Forest score
    isolation_score = 50 - (
        decision_score * 100
    )

    isolation_score = np.clip(
        isolation_score,
        0,
        100
    )

    # -----------------------------------------------------
    # Statistical deviation
    # -----------------------------------------------------

    deviation_score = calculate_reference_deviation(
        reference_features,
        uploaded_features
    )

    # -----------------------------------------------------
    # Combine both signals
    # -----------------------------------------------------

    combined_score = (
        isolation_score * 0.40
        +
        deviation_score * 0.60
    )

    combined_score = np.clip(
        combined_score,
        0,
        100
    )

    combined_score = round(
        float(combined_score),
        2
    )

    # -----------------------------------------------------
    # Determine anomaly status
    # -----------------------------------------------------

    if combined_score >= 60:

        status = "ANOMALOUS PATTERN"

        explanation = (
            "The document shows noticeable visual "
            "and layout deviation from the reference "
            "dataset. Manual review is recommended."
        )

    elif combined_score >= 40:

        status = "REVIEW RECOMMENDED"

        explanation = (
            "The document shows some deviation "
            "from the reference dataset. "
            "Additional verification is recommended."
        )

    else:

        status = "NORMAL PATTERN"

        explanation = (
            "The document's visual and layout "
            "features are broadly consistent with "
            "the reference dataset."
        )

    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    result.update({

        "available": True,

        "anomaly_score": combined_score,

        "prediction": int(
            prediction
        ),

        "status": status,

        "explanation": explanation
    })

    return result