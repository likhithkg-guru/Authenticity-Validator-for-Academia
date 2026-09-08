from utils.ocr import extract_text_from_pdf, extract_details

pdf_path = "uploads/10markscard.pdf"

text = extract_text_from_pdf(pdf_path)

print("\n========== EXTRACTED TEXT ==========\n")
print(text)

details = extract_details(text)

print("\n========== EXTRACTED DETAILS ==========\n")

for key, value in details.items():
    print(key, ":", value)