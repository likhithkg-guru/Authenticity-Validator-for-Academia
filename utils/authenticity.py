import cv2
import fitz
import numpy as np
import os


# --------------------------------------------------
# Convert first PDF page to image
# --------------------------------------------------

def pdf_to_image(pdf_path):

    try:
        document = fitz.open(pdf_path)

        if len(document) == 0:
            document.close()
            return None

        page = document[0]

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2)
        )

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
                cv2.COLOR_RGBA2BGR
            )

        else:

            image = cv2.cvtColor(
                image,
                cv2.COLOR_RGB2BGR
            )

        document.close()

        return image

    except Exception:

        return None


# --------------------------------------------------
# Prepare image
# --------------------------------------------------

def prepare_image(image):

    return cv2.resize(
        image,
        (800, 1100)
    )


# --------------------------------------------------
# Compare two documents
# --------------------------------------------------

def compare_documents(
    uploaded_path,
    reference_path
):

    uploaded_image = pdf_to_image(
        uploaded_path
    )

    reference_image = pdf_to_image(
        reference_path
    )

    if uploaded_image is None:

        return {
            "similarity": 0,
            "status": "Unable to analyze uploaded document"
        }

    if reference_image is None:

        return {
            "similarity": 0,
            "status": "Unable to read reference document"
        }

    uploaded_image = prepare_image(
        uploaded_image
    )

    reference_image = prepare_image(
        reference_image
    )

    uploaded_gray = cv2.cvtColor(
        uploaded_image,
        cv2.COLOR_BGR2GRAY
    )

    reference_gray = cv2.cvtColor(
        reference_image,
        cv2.COLOR_BGR2GRAY
    )

    difference = cv2.absdiff(
        uploaded_gray,
        reference_gray
    )

    mean_difference = np.mean(
        difference
    )

    similarity = max(
        0,
        100 - (
            mean_difference / 255 * 100
        )
    )

    similarity = round(
        similarity,
        2
    )

    if similarity >= 90:

        status = "HIGH SIMILARITY"

    elif similarity >= 70:

        status = "MODERATE SIMILARITY"

    else:

        status = "LOW SIMILARITY"

    return {
        "similarity": similarity,
        "status": status
    }


# ==================================================
# MULTIPLE REFERENCE DOCUMENTS
# ==================================================

def find_best_reference(
    uploaded_path,
    reference_folder
):

    best_match = None
    best_similarity = -1

    if not os.path.exists(reference_folder):

        return None


    reference_files = [

        file

        for file in os.listdir(reference_folder)

        if file.lower().endswith(".pdf")
    ]


    if not reference_files:

        return None


    # Compare with every reference document

    for filename in reference_files:

        reference_path = os.path.join(
            reference_folder,
            filename
        )

        result = compare_documents(
            uploaded_path,
            reference_path
        )

        similarity = result["similarity"]


        if similarity > best_similarity:

            best_similarity = similarity

            best_match = {

                "filename": filename,

                "similarity": similarity,

                "status": result["status"]
            }


    return best_match