import os
import cv2
import numpy as np
import fitz


# ============================================================
# PDF -> IMAGE
# ============================================================

def pdf_to_image(pdf_path):

    try:

        document = fitz.open(pdf_path)

        if len(document) == 0:
            document.close()
            return None

        page = document[0]

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
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
            cv2.COLOR_RGB2BGR
        )

        document.close()

        return image

    except Exception:

        return None


# ============================================================
# PREPARE IMAGE
# ============================================================

def prepare_image(image):

    return cv2.resize(
        image,
        (800, 1100)
    )


# ============================================================
# EXTRACT VISUAL + LAYOUT FEATURES
# ============================================================

def extract_features(image):

    image = prepare_image(image)

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # --------------------------------------------------------
    # Basic image statistics
    # --------------------------------------------------------

    brightness = np.mean(gray)

    contrast = np.std(gray)

    sharpness = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()


    # --------------------------------------------------------
    # Edge information
    # --------------------------------------------------------

    edges = cv2.Canny(
        gray,
        100,
        200
    )

    edge_density = (
        np.mean(edges > 0)
        * 100
    )


    # --------------------------------------------------------
    # Dark / white pixel ratios
    # --------------------------------------------------------

    dark_ratio = (
        np.mean(gray < 80)
        * 100
    )

    white_ratio = (
        np.mean(gray > 220)
        * 100
    )


    # --------------------------------------------------------
    # Aspect ratio
    # --------------------------------------------------------

    height, width = gray.shape

    aspect_ratio = (
        width / height
    )


    features = [

        brightness,
        contrast,
        sharpness,
        edge_density,
        dark_ratio,
        white_ratio,
        aspect_ratio

    ]


    # ========================================================
    # HORIZONTAL REGIONS
    # ========================================================

    horizontal_regions = 10

    for i in range(
        horizontal_regions
    ):

        start = int(
            i * height /
            horizontal_regions
        )

        end = int(
            (i + 1) * height /
            horizontal_regions
        )

        region = gray[
            start:end,
            :
        ]

        region_edges = edges[
            start:end,
            :
        ]


        region_mean = np.mean(
            region
        )

        region_dark = (
            np.mean(region < 80)
            * 100
        )

        region_edge = (
            np.mean(region_edges > 0)
            * 100
        )


        features.extend([

            region_mean,
            region_dark,
            region_edge

        ])


    # ========================================================
    # VERTICAL REGIONS
    # ========================================================

    vertical_regions = 10

    for i in range(
        vertical_regions
    ):

        start = int(
            i * width /
            vertical_regions
        )

        end = int(
            (i + 1) * width /
            vertical_regions
        )

        region = gray[
            :,
            start:end
        ]

        region_edges = edges[
            :,
            start:end
        ]


        region_mean = np.mean(
            region
        )

        region_dark = (
            np.mean(region < 80)
            * 100
        )

        region_edge = (
            np.mean(region_edges > 0)
            * 100
        )


        features.extend([

            region_mean,
            region_dark,
            region_edge

        ])


    # ========================================================
    # PROJECTION FEATURES
    # ========================================================

    horizontal_projection = (
        np.mean(
            gray < 150,
            axis=1
        )
    )

    vertical_projection = (
        np.mean(
            gray < 150,
            axis=0
        )
    )


    features.extend([

        np.mean(
            horizontal_projection
        ),

        np.std(
            horizontal_projection
        ),

        np.mean(
            vertical_projection
        ),

        np.std(
            vertical_projection
        )

    ])


    # ========================================================
    # CENTER REGION
    # ========================================================

    center_y1 = int(
        height * 0.25
    )

    center_y2 = int(
        height * 0.75
    )

    center_x1 = int(
        width * 0.25
    )

    center_x2 = int(
        width * 0.75
    )


    center = gray[
        center_y1:center_y2,
        center_x1:center_x2
    ]


    features.extend([

        np.mean(center),

        np.mean(
            center < 80
        ) * 100

    ])


    return np.array(
        features,
        dtype=np.float64
    )


# ============================================================
# COLLECT REFERENCE FEATURES
# ============================================================

def collect_reference_features(
    reference_folder
):

    reference_features = []


    if not os.path.exists(
        reference_folder
    ):

        return np.array([])


    reference_files = [

        file

        for file in os.listdir(
            reference_folder
        )

        if file.lower().endswith(
            ".pdf"
        )

    ]


    for filename in reference_files:

        path = os.path.join(
            reference_folder,
            filename
        )


        image = pdf_to_image(
            path
        )


        if image is None:

            continue


        try:

            features = extract_features(
                image
            )

            reference_features.append(
                features
            )

        except Exception:

            continue


    if not reference_features:

        return np.array([])


    return np.array(
        reference_features,
        dtype=np.float64
    )


# ============================================================
# CALCULATE STATISTICAL DEVIATION
# ============================================================

def calculate_deviation_score(
    document_features,
    reference_features
):

    if (
        reference_features.size == 0
    ):

        return 50.0


    # --------------------------------------------------------
    # Calculate mean and standard deviation
    # --------------------------------------------------------

    reference_mean = np.mean(
        reference_features,
        axis=0
    )


    reference_std = np.std(
        reference_features,
        axis=0
    )


    # --------------------------------------------------------
    # Prevent division by zero
    # --------------------------------------------------------

    reference_std = np.where(
        reference_std < 1e-6,
        1.0,
        reference_std
    )


    # --------------------------------------------------------
    # Calculate absolute Z-score
    # --------------------------------------------------------

    z_scores = np.abs(

        (
            document_features
            - reference_mean
        )
        /
        reference_std

    )


    # --------------------------------------------------------
    # Average deviation
    # --------------------------------------------------------

    average_deviation = np.mean(
        z_scores
    )


    # --------------------------------------------------------
    # Convert deviation to 0-100
    # --------------------------------------------------------

    score = (

        average_deviation
        /
        (average_deviation + 1)

    ) * 100


    score = float(
        np.clip(
            score,
            0,
            100
        )
    )


    return round(
        score,
        2
    )


# ============================================================
# CALCULATE SIMILARITY TO REFERENCE DISTRIBUTION
# ============================================================

def calculate_reference_similarity(
    document_features,
    reference_features
):

    if reference_features.size == 0:

        return 0.0


    reference_mean = np.mean(
        reference_features,
        axis=0
    )


    reference_std = np.std(
        reference_features,
        axis=0
    )


    reference_std = np.where(
        reference_std < 1e-6,
        1.0,
        reference_std
    )


    z_scores = np.abs(

        (
            document_features
            - reference_mean
        )
        /
        reference_std

    )


    average_z = np.mean(
        z_scores
    )


    # Convert deviation into similarity

    similarity = (

        100
        /
        (
            1
            +
            average_z
        )

    )


    return round(
        float(
            np.clip(
                similarity,
                0,
                100
            )
        ),
        2
    )


# ============================================================
# MAIN ML ANALYSIS
# ============================================================

def analyze_with_ml(
    uploaded_path,
    reference_folder
):

    result = {

        "available": False,

        "anomaly_score": None,

        "prediction": None,

        "status": "ML ANALYSIS UNAVAILABLE",

        "reference_count": 0,

        "explanation":
            "ML analysis could not be performed."

    }


    # ========================================================
    # READ UPLOADED DOCUMENT
    # ========================================================

    uploaded_image = pdf_to_image(
        uploaded_path
    )


    if uploaded_image is None:

        result["explanation"] = (
            "Unable to read the uploaded document."
        )

        return result


    # ========================================================
    # EXTRACT UPLOADED FEATURES
    # ========================================================

    try:

        document_features = (
            extract_features(
                uploaded_image
            )
        )

    except Exception as error:

        result["explanation"] = (
            "Unable to extract visual "
            "and layout features."
        )

        return result


    # ========================================================
    # GET REFERENCE FEATURES
    # ========================================================

    reference_features = (
        collect_reference_features(
            reference_folder
        )
    )


    if reference_features.size == 0:

        result["explanation"] = (
            "No valid reference documents "
            "were available for ML analysis."
        )

        return result


    reference_count = (
        len(reference_features)
    )


    # ========================================================
    # CALCULATE DEVIATION
    # ========================================================

    deviation_score = (
        calculate_deviation_score(

            document_features,

            reference_features

        )
    )


    # ========================================================
    # CALCULATE SIMILARITY
    # ========================================================

    reference_similarity = (
        calculate_reference_similarity(

            document_features,

            reference_features

        )
    )


    # ========================================================
    # FINAL ANOMALY SCORE
    # ========================================================

    # Higher score = greater deviation

    anomaly_score = deviation_score


    # ========================================================
    # DETERMINE STATUS
    # ========================================================

    if anomaly_score >= 60:

        status = (
            "ANOMALOUS PATTERN"
        )

        explanation = (

            "The document shows noticeable "
            "visual and layout deviation "
            "from the reference dataset. "
            "Manual review is recommended."
        )


    elif anomaly_score >= 40:

        status = (
            "REVIEW RECOMMENDED"
        )

        explanation = (

            "The document shows some "
            "visual and layout deviation "
            "from the reference dataset. "
            "Further review is recommended."
        )


    else:

        status = (
            "NORMAL PATTERN"
        )

        explanation = (

            "The document's visual and "
            "layout features are broadly "
            "consistent with the reference "
            "dataset."
        )


    # ========================================================
    # PREDICTION
    # ========================================================

    # 1 = pattern is accepted as normal
    # -1 = strong anomaly

    if anomaly_score >= 60:

        prediction = -1

    else:

        prediction = 1


    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        "available": True,

        "anomaly_score": anomaly_score,

        "prediction": prediction,

        "status": status,

        "reference_count": reference_count,

        "reference_similarity":
            reference_similarity,

        "explanation": explanation

    }


    return result