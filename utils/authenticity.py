
import os
import re

import cv2
import fitz
import numpy as np


# =========================================================
# DOCUMENT TYPE DETECTION
# =========================================================

DOCUMENT_KEYWORDS = {
    "MARKSHEET": [
        "marksheet",
        "mark sheet",
        "marks card",
        "marks obtained",
        "maximum marks",
        "scholastic subjects",
        "sslc",
        "school examination",
        "grade",
        "total marks",
    ],
    "DEGREE_CERTIFICATE": [
        "degree certificate",
        "degree awarded",
        "bachelor of",
        "master of",
        "degree conferred",
    ],
    "TRANSCRIPT": [
        "transcript",
        "semester grade",
        "grade point",
        "credit hours",
    ],
    "PROVISIONAL_CERTIFICATE": [
        "provisional certificate",
        "provisional degree",
    ],
    "DIPLOMA_CERTIFICATE": [
        "diploma certificate",
        "diploma awarded",
    ],
    "BONAFIDE_CERTIFICATE": [
        "bonafide certificate",
        "bonafide",
        "bonafide student",
    ],
    "TRANSFER_CERTIFICATE": [
        "transfer certificate",
        "tc number",
    ],
    "MIGRATION_CERTIFICATE": [
        "migration certificate",
        "migration certificate no",
    ],
}


def detect_document_type(text, filename=""):
    """
    Estimate document type from extracted PDF text and filename.
    Returns UNKNOWN if there is not enough evidence.
    """

    combined_text = (
        str(text or "") + " " + str(filename or "")
    ).lower()

    combined_text = re.sub(
        r"\s+",
        " ",
        combined_text
    )

    scores = {}

    for document_type, keywords in DOCUMENT_KEYWORDS.items():
        score = sum(
            1
            for keyword in keywords
            if keyword in combined_text
        )

        if score:
            scores[document_type] = score

    if not scores:
        return "UNKNOWN"

    return max(
        scores,
        key=scores.get
    )


# =========================================================
# LOAD A DOCUMENT PAGE
# =========================================================

def load_document_page(filepath):
    """
    Loads the first page of a PDF or an image.

    Returns:
        image: OpenCV BGR image, or None
        text: Extracted text where available
    """

    if not filepath or not os.path.isfile(filepath):
        return None, ""

    extension = os.path.splitext(filepath)[1].lower()

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    if extension == ".pdf":
        try:
            with fitz.open(filepath) as pdf:
                if len(pdf) == 0:
                    return None, ""

                page = pdf[0]

                # Read text from the first page.
                text = page.get_text("text") or ""

                # Render the page at a useful resolution.
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(1.5, 1.5),
                    colorspace=fitz.csRGB,
                    alpha=False
                )

                image = np.frombuffer(
                    pix.samples,
                    dtype=np.uint8
                ).reshape(
                    pix.height,
                    pix.width,
                    3
                )

                # PyMuPDF produces RGB; OpenCV uses BGR.
                image = cv2.cvtColor(
                    image,
                    cv2.COLOR_RGB2BGR
                )

                return image, text

        except Exception as error:
            print(
                f"Could not read PDF {filepath}: {error}"
            )
            return None, ""

    # -----------------------------------------------------
    # IMAGE
    # -----------------------------------------------------

    image_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    }

    if extension in image_extensions:
        try:
            image = cv2.imread(filepath)

            if image is None:
                return None, ""

            return image, ""

        except Exception as error:
            print(
                f"Could not read image {filepath}: {error}"
            )
            return None, ""

    return None, ""


# =========================================================
# NORMALIZE IMAGE FOR COMPARISON
# =========================================================

def prepare_image(image):
    """
    Normalizes page dimensions and creates grayscale and edge images.
    """

    if image is None or image.size == 0:
        return None

    if len(image.shape) == 3:
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )
    else:
        gray = image.copy()

    original_height, original_width = gray.shape

    if original_width == 0 or original_height == 0:
        return None

    # Resize to a consistent comparison canvas.
    gray = cv2.resize(
        gray,
        (500, 700),
        interpolation=cv2.INTER_AREA
    )

    # Reduce minor scan noise.
    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    edges = cv2.Canny(
        gray,
        50,
        150
    )

    # Histogram helps compare overall visual distribution.
    histogram = cv2.calcHist(
        [gray],
        [0],
        None,
        [64],
        [0, 256]
    )

    cv2.normalize(
        histogram,
        histogram,
        alpha=1,
        norm_type=cv2.NORM_L1
    )

    aspect_ratio = original_width / original_height

    return {
        "gray": gray,
        "edges": edges,
        "histogram": histogram,
        "aspect_ratio": aspect_ratio,
    }


# =========================================================
# VISUAL SIMILARITY
# =========================================================

def compare_documents(uploaded_image, reference_image):
    """
    Produces a visual similarity estimate from 0 to 100.

    The score combines:
        - grayscale appearance
        - edge/layout similarity
        - histogram similarity
        - original page aspect ratio

    This is a visual comparison score, not a fraud probability.
    """

    first = prepare_image(uploaded_image)
    second = prepare_image(reference_image)

    if first is None or second is None:
        return 0.0

    # -----------------------------------------------------
    # 1. Grayscale appearance
    # -----------------------------------------------------

    gray_difference = cv2.absdiff(
        first["gray"],
        second["gray"]
    )

    mean_difference = float(
        np.mean(gray_difference)
    )

    pixel_similarity = max(
        0.0,
        100.0 - (mean_difference / 255.0 * 100.0)
    )

    # -----------------------------------------------------
    # 2. Edge/layout similarity
    # -----------------------------------------------------

    edge_difference = cv2.absdiff(
        first["edges"],
        second["edges"]
    )

    mean_edge_difference = float(
        np.mean(edge_difference)
    )

    edge_similarity = max(
        0.0,
        100.0 - (
            mean_edge_difference / 255.0 * 100.0
        )
    )

    # -----------------------------------------------------
    # 3. Histogram similarity
    # -----------------------------------------------------

    correlation = cv2.compareHist(
        first["histogram"],
        second["histogram"],
        cv2.HISTCMP_CORREL
    )

    # Correlation can range from -1 to 1.
    histogram_similarity = (
        (float(correlation) + 1.0) / 2.0
    ) * 100.0

    histogram_similarity = max(
        0.0,
        min(100.0, histogram_similarity)
    )

    # -----------------------------------------------------
    # 4. Page aspect ratio
    # -----------------------------------------------------

    ratio_a = first["aspect_ratio"]
    ratio_b = second["aspect_ratio"]

    ratio_difference = abs(
        ratio_a - ratio_b
    ) / max(ratio_a, ratio_b, 0.001)

    aspect_similarity = max(
        0.0,
        100.0 * (1.0 - ratio_difference)
    )

    # -----------------------------------------------------
    # Combined score
    # -----------------------------------------------------

    score = (
        pixel_similarity * 0.25
        + edge_similarity * 0.35
        + histogram_similarity * 0.20
        + aspect_similarity * 0.20
    )

    return round(
        max(0.0, min(100.0, score)),
        2
    )


# =========================================================
# FIND REFERENCE PDFs
# =========================================================

def get_reference_files(reference_folder):
    """
    Finds PDF reference documents recursively, including PDFs
    stored in category subfolders.
    """

    reference_files = []

    if not os.path.isdir(reference_folder):
        return reference_files

    for root, directories, files in os.walk(reference_folder):
        # Ignore hidden directories.
        directories[:] = sorted(
            directory
            for directory in directories
            if not directory.startswith(".")
        )

        for filename in sorted(files):
            if filename.lower().endswith(".pdf"):
                reference_files.append(
                    os.path.join(root, filename)
                )

    return reference_files


# =========================================================
# FIND THE BEST MATCH
# =========================================================

def find_best_reference(upload_path, reference_folder):
    """
    Finds the closest reference PDF.

    Compatible with the existing app.py call:
        find_best_reference(filepath, REFERENCE_FOLDER)

    Returns a dictionary containing:
        similarity
        filename
        status
        document_type
        reference_count
        matching_category_count
        explanation
    """

    empty_result = {
        "similarity": 0.0,
        "filename": None,
        "status": "NO_REFERENCE",
        "document_type": "UNKNOWN",
        "reference_count": 0,
        "matching_category_count": 0,
        "explanation": "",
    }

    # -----------------------------------------------------
    # Load uploaded document
    # -----------------------------------------------------

    uploaded_image, uploaded_text = load_document_page(
        upload_path
    )

    if uploaded_image is None:
        empty_result["status"] = "COMPARISON_FAILED"
        empty_result["explanation"] = (
            "The uploaded document could not be read for "
            "visual comparison."
        )
        return empty_result

    uploaded_type = detect_document_type(
        uploaded_text,
        os.path.basename(upload_path)
    )

    # -----------------------------------------------------
    # Find PDF references
    # -----------------------------------------------------

    reference_files = get_reference_files(
        reference_folder
    )

    empty_result["document_type"] = uploaded_type
    empty_result["reference_count"] = len(reference_files)

    if not reference_files:
        empty_result["explanation"] = (
            "No PDF reference documents were found. "
            "Add verified reference PDFs before comparing."
        )
        return empty_result

    # -----------------------------------------------------
    # Load usable reference samples
    # -----------------------------------------------------

    references = []

    for reference_path in reference_files:
        reference_image, reference_text = load_document_page(
            reference_path
        )

        if reference_image is None:
            print(
                "Skipping unreadable reference:",
                reference_path
            )
            continue

        reference_type = detect_document_type(
            reference_text,
            os.path.basename(reference_path)
        )

        references.append({
            "path": reference_path,
            "image": reference_image,
            "type": reference_type,
        })

    if not references:
        empty_result["status"] = "COMPARISON_FAILED"
        empty_result["explanation"] = (
            "Reference PDFs were found, but none could be "
            "read successfully."
        )
        return empty_result

    # -----------------------------------------------------
    # Prefer references of the same document type
    # -----------------------------------------------------

    matching_references = []

    if uploaded_type != "UNKNOWN":
        matching_references = [
            reference
            for reference in references
            if reference["type"] == uploaded_type
        ]

    if matching_references:
        candidates = matching_references

        explanation = (
            "Compared against references classified as "
            + uploaded_type
            + "."
        )

    else:
        # Do not return a false "no match" just because a
        # reference filename or PDF contains little text.
        candidates = references

        explanation = (
            "No reference could be confidently classified as "
            + uploaded_type
            + ". Compared against all readable references; "
            "the result may be less relevant."
        )

    # -----------------------------------------------------
    # Compare uploaded page against candidate references
    # -----------------------------------------------------

    best_reference = None
    best_score = -1.0

    for reference in candidates:
        score = compare_documents(
            uploaded_image,
            reference["image"]
        )

        if score > best_score:
            best_score = score
            best_reference = reference

    if best_reference is None:
        empty_result["status"] = "COMPARISON_FAILED"
        empty_result["explanation"] = (
            "No reference could be compared successfully."
        )
        return empty_result

    # -----------------------------------------------------
    # Return a compatible result
    # -----------------------------------------------------

    relative_filename = os.path.relpath(
        best_reference["path"],
        reference_folder
    )

    result = {
        "similarity": round(
            max(0.0, min(100.0, best_score)),
            2
        ),
        "filename": relative_filename,
        "status": "COMPARISON_COMPLETE",
        "document_type": uploaded_type,
        "reference_count": len(references),
        "matching_category_count": len(
            matching_references
        ),
        "explanation": explanation,
    }

    print("\n===== SMART REFERENCE MATCHING =====")
    print("Uploaded document:", os.path.basename(upload_path))
    print("Detected type:", uploaded_type)
    print("Readable references:", len(references))
    print("Category-matched references:", len(matching_references))
    print("Best reference:", relative_filename)
    print("Visual similarity:", result["similarity"], "%")
    print("Explanation:", explanation)
    print("====================================\n")

    return result
