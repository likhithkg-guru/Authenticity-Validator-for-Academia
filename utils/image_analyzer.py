import cv2
import fitz
import os


# ==================================================
# ANALYZE DOCUMENT IMAGE
# ==================================================

def analyze_image(file_path):

    image = None


    # ------------------------------------------
    # PDF FILE
    # ------------------------------------------

    if file_path.lower().endswith(".pdf"):

        try:

            document = fitz.open(file_path)

            if len(document) == 0:

                return {
                    "image_quality": "Unable to read document",
                    "blur_score": 0,
                    "width": 0,
                    "height": 0
                }

            # First page
            page = document[0]

            # Convert PDF page to image
            pix = page.get_pixmap(
                matrix=fitz.Matrix(2, 2)
            )

            temp_path = os.path.join(
                "static",
                "uploads",
                "temp_document.png"
            )

            pix.save(temp_path)

            document.close()

            # Read converted image
            image = cv2.imread(
                temp_path
            )

        except Exception:

            return {
                "image_quality": "Unable to analyze",
                "blur_score": 0,
                "width": 0,
                "height": 0
            }


    # ------------------------------------------
    # IMAGE FILE
    # ------------------------------------------

    else:

        image = cv2.imread(
            file_path
        )


    # ------------------------------------------
    # IMAGE CHECK
    # ------------------------------------------

    if image is None:

        return {
            "image_quality": "Unable to read image",
            "blur_score": 0,
            "width": 0,
            "height": 0
        }


    # ------------------------------------------
    # GRAYSCALE
    # ------------------------------------------

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )


    # ------------------------------------------
    # SHARPNESS
    # ------------------------------------------

    blur_score = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()


    # ------------------------------------------
    # QUALITY
    # ------------------------------------------

    if blur_score >= 100:

        quality = "Good"

    elif blur_score >= 40:

        quality = "Moderate"

    else:

        quality = "Low"


    # ------------------------------------------
    # RESOLUTION
    # ------------------------------------------

    height, width = image.shape[:2]


    return {

        "image_quality": quality,

        "blur_score": round(
            blur_score,
            2
        ),

        "width": width,

        "height": height
    }