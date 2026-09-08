import cv2
import os
import fitz


def analyze_image(image_path):

    # If PDF, convert first page to image
    if image_path.lower().endswith(".pdf"):

        pdf = fitz.open(image_path)

        if len(pdf) == 0:
            return {
                "image_quality": "Unable to read document",
                "blur_score": 0,
                "width": 0,
                "height": 0
            }

        page = pdf[0]

        # Render PDF page as image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        image = pix.tobytes("png")

        temp_image = "static/uploads/temp_page.png"

        with open(temp_image, "wb") as f:
            f.write(image)

        image_path = temp_image

    # Read image
    image = cv2.imread(image_path)

    if image is None:
        return {
            "image_quality": "Unable to read image",
            "blur_score": 0,
            "width": 0,
            "height": 0
        }

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate sharpness
    blur_score = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    # Decide quality
    if blur_score > 100:
        quality = "Good"
    elif blur_score > 40:
        quality = "Moderate"
    else:
        quality = "Low"

    # Get resolution
    height, width = image.shape[:2]

    return {
        "image_quality": quality,
        "blur_score": round(blur_score, 2),
        "width": width,
        "height": height
    }