import cv2
import fitz
import numpy as np
import os


def pdf_to_image(pdf_path):
    """
    Convert the first page of a PDF into an OpenCV image.
    """

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

    except Exception as error:

        print("PDF IMAGE ERROR:", error)

        return None


def analyze_image_quality(pdf_path):
    """
    Analyze the quality of the first page of a PDF.
    """

    image = pdf_to_image(pdf_path)

    if image is None:

        return {
            "image_quality": "Unknown",
            "blur_score": 0,
            "width": 0,
            "height": 0
        }

    try:

        height, width = image.shape[:2]

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # Laplacian variance is used as a simple
        # sharpness / blur indicator.
        blur_score = cv2.Laplacian(
            gray,
            cv2.CV_64F
        ).var()

        blur_score = round(
            float(blur_score),
            2
        )

        if blur_score >= 100:

            quality = "Good"

        elif blur_score >= 40:

            quality = "Moderate"

        else:

            quality = "Low"

        return {
            "image_quality": quality,
            "blur_score": blur_score,
            "width": width,
            "height": height
        }

    except Exception as error:

        print("IMAGE QUALITY ERROR:", error)

        return {
            "image_quality": "Unknown",
            "blur_score": 0,
            "width": 0,
            "height": 0
        }