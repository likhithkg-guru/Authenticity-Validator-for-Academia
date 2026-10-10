import os
from utils.authenticity import find_best_reference

reference_folder = "reference_documents"

# Put the path to an existing uploaded PDF here.
uploaded_pdf = os.path.join(
    "uploads",
    "your_uploaded_file.pdf"
)

if not os.path.isfile(uploaded_pdf):
    print("Please replace the filename with an existing uploaded PDF.")

else:
    result = find_best_reference(
        uploaded_pdf,
        reference_folder
    )

    print("\nREFERENCE MATCHING RESULT")
    print("-------------------------")
    print("Similarity:", result["similarity"], "%")
    print("Best reference:", result["filename"])
    print("Status:", result["status"])
    print("Document type:", result["document_type"])
    print("References checked:", result["reference_count"])
    print("Category matches:", result["matching_category_count"])
    print("Explanation:", result["explanation"])