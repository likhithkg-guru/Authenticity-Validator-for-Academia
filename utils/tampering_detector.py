import cv2
import fitz
import numpy as np


# ============================================================
# PDF → IMAGE
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
# NORMALIZE IMAGE
# ============================================================

def prepare_image(image):

    return cv2.resize(
        image,
        (900, 1200)
    )


# ============================================================
# LOCAL TEXTURE ANALYSIS
# ============================================================

def calculate_texture_anomaly(gray):

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    texture = cv2.absdiff(
        gray,
        blurred
    )

    mean_texture = np.mean(texture)

    std_texture = np.std(texture)

    return mean_texture, std_texture


# ============================================================
# EDGE ANALYSIS
# ============================================================

def calculate_edge_density(gray):

    edges = cv2.Canny(
        gray,
        50,
        150
    )

    edge_density = (
        np.count_nonzero(edges)
        / edges.size
    )

    return edge_density


# ============================================================
# REGION ANALYSIS
# ============================================================

def analyze_regions(gray):

    height, width = gray.shape

    rows = 6
    cols = 4

    region_features = []

    region_height = height // rows
    region_width = width // cols

    for row in range(rows):

        for col in range(cols):

            y1 = row * region_height
            y2 = (
                (row + 1) * region_height
                if row < rows - 1
                else height
            )

            x1 = col * region_width
            x2 = (
                (col + 1) * region_width
                if col < cols - 1
                else width
            )

            region = gray[
                y1:y2,
                x1:x2
            ]

            if region.size == 0:
                continue

            mean_value = np.mean(region)

            std_value = np.std(region)

            edges = cv2.Canny(
                region,
                50,
                150
            )

            edge_density = (
                np.count_nonzero(edges)
                / edges.size
            )

            region_features.append({
                "row": row,
                "column": col,
                "mean": mean_value,
                "std": std_value,
                "edge_density": edge_density
            })

    return region_features


# ============================================================
# FIND SUSPICIOUS REGIONS
# ============================================================

def find_suspicious_regions(region_features):

    if not region_features:

        return []

    means = np.array([
        region["mean"]
        for region in region_features
    ])

    stds = np.array([
        region["std"]
        for region in region_features
    ])

    edge_values = np.array([
        region["edge_density"]
        for region in region_features
    ])

    mean_center = np.mean(means)
    mean_std = np.mean(stds)
    mean_edges = np.mean(edge_values)

    mean_std_deviation = np.std(means)
    std_deviation = np.std(stds)
    edge_deviation = np.std(edge_values)

    suspicious = []

    for region in region_features:

        score = 0

        # ----------------------------------------
        # Brightness inconsistency
        # ----------------------------------------

        if mean_std_deviation > 0:

            brightness_difference = abs(
                region["mean"] - mean_center
            )

            if brightness_difference > (
                2 * mean_std_deviation
            ):

                score += 1

        # ----------------------------------------
        # Texture inconsistency
        # ----------------------------------------

        if std_deviation > 0:

            texture_difference = abs(
                region["std"] - mean_std
            )

            if texture_difference > (
                2 * std_deviation
            ):

                score += 1

        # ----------------------------------------
        # Edge inconsistency
        # ----------------------------------------

        if edge_deviation > 0:

            edge_difference = abs(
                region["edge_density"] - mean_edges
            )

            if edge_difference > (
                2 * edge_deviation
            ):

                score += 1

        if score >= 2:

            suspicious.append({
                "row": region["row"],
                "column": region["column"],
                "score": score
            })

    return suspicious


# ============================================================
# MAIN TAMPERING ANALYSIS
# ============================================================

def analyze_tampering(pdf_path):

    image = pdf_to_image(
        pdf_path
    )

    if image is None:

        return {
            "available": False,
            "status": "UNABLE TO ANALYZE",
            "tampering_score": 0,
            "suspicious_regions": 0,
            "indicators": [],
            "explanation": (
                "The document image could not "
                "be analyzed."
            )
        }

    image = prepare_image(
        image
    )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # ----------------------------------------
    # Global analysis
    # ----------------------------------------

    texture_mean, texture_std = (
        calculate_texture_anomaly(
            gray
        )
    )

    edge_density = (
        calculate_edge_density(
            gray
        )
    )

    # ----------------------------------------
    # Regional analysis
    # ----------------------------------------

    regions = analyze_regions(
        gray
    )

    suspicious_regions = (
        find_suspicious_regions(
            regions
        )
    )

    suspicious_count = len(
        suspicious_regions
    )

    total_regions = max(
        len(regions),
        1
    )

    regional_ratio = (
        suspicious_count
        / total_regions
    )

    # ----------------------------------------
    # Build tampering score
    # ----------------------------------------

    score = regional_ratio * 100

    # Slight adjustment for unusual
    # global texture/edge characteristics

    if texture_std > 35:

        score += 10

    if edge_density > 0.20:

        score += 10

    score = min(
        100,
        score
    )

    score = round(
        score,
        2
    )

    # ----------------------------------------
    # Status
    # ----------------------------------------

    if score >= 60:

        status = "HIGH SUSPICION"

    elif score >= 35:

        status = "REVIEW RECOMMENDED"

    else:

        status = "NO STRONG INDICATORS"

    # ----------------------------------------
    # Explanation
    # ----------------------------------------

    indicators = []

    if suspicious_count > 0:

        indicators.append(
            f"{suspicious_count} document "
            "region(s) show unusual visual "
            "characteristics."
        )

    if texture_std > 35:

        indicators.append(
            "Local texture variation is "
            "higher than expected."
        )

    if edge_density > 0.20:

        indicators.append(
            "The document contains unusually "
            "high edge density in some areas."
        )

    if not indicators:

        indicators.append(
            "No strong regional visual "
            "irregularities were detected."
        )

    if score >= 60:

        explanation = (
            "Several visual characteristics "
            "differ from the overall document "
            "pattern. Manual inspection of the "
            "original certificate is recommended."
        )

    elif score >= 35:

        explanation = (
            "Some visual irregularities were "
            "detected. These may have legitimate "
            "causes, so manual review is recommended."
        )

    else:

        explanation = (
            "The document does not show strong "
            "visual indicators of localized "
            "manipulation."
        )

    return {

        "available": True,

        "status": status,

        "tampering_score": score,

        "suspicious_regions": suspicious_count,

        "total_regions": total_regions,

        "texture_mean": round(
            texture_mean,
            2
        ),

        "texture_std": round(
            texture_std,
            2
        ),

        "edge_density": round(
            edge_density,
            4
        ),

        "indicators": indicators,

        "explanation": explanation
    }