from utils.ml_detector import analyze_with_ml


REFERENCE_FOLDER = "reference_documents"


print("\n========================================")
print("TEST 1: SIMILAR DOCUMENT")
print("========================================")

result1 = analyze_with_ml(
    "test_documents/similar_document.pdf",
    REFERENCE_FOLDER
)

print("Available:", result1["available"])
print("Status:", result1["status"])
print("Anomaly Score:", result1["anomaly_score"])
print("Prediction:", result1["prediction"])
print("References:", result1["reference_count"])
print("Explanation:", result1["explanation"])


print("\n========================================")
print("TEST 2: DIFFERENT DOCUMENT")
print("========================================")

result2 = analyze_with_ml(
    "test_documents/different_document.pdf",
    REFERENCE_FOLDER
)

print("Available:", result2["available"])
print("Status:", result2["status"])
print("Anomaly Score:", result2["anomaly_score"])
print("Prediction:", result2["prediction"])
print("References:", result2["reference_count"])
print("Explanation:", result2["explanation"])


print("\n========================================")
print("TESTING COMPLETE")
print("========================================")