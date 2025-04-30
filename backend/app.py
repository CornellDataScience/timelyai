from google.cloud import firestore
from datetime import datetime

# Initialize Firestore
db = firestore.Client()

timestamp = datetime.now()

data = {
    "Tasks": {
        "MATH HW:": {"category": "School", "deadline": timestamp, "duration": 4},
    },
    "User Preferences": {
        "Goals": {
            "Clubs": 10,
            "Health & Fitness": 5,
            "Hobbies": 10,
            "Job": 0,
            "Other": 0,
            "School": 40,
            "Sleep": 56,
            "Social": 15,
        },
        "Sleep": {"Bedtime": "11:00pm EST", "Wakeup": "7:00am EST"},
    },
}

# Specify the collection and document name

collection_name = "user_preferences"
document_name = "user4"


# Add the data to Firestore
try:
    doc_ref = db.collection(collection_name).document(document_name)
    doc_ref.set(data)
    print(f"Data added successfully to document: {doc_ref.id}")
except Exception as e:
    print(f"Error adding data: {e}")


# Example of adding data with an auto-generated ID:
# try:
# doc_ref = db.collection(collection_name).add(data)
# print(f"Data added successfully to document: {doc_ref[1].id}")

# except Exception as e:
# print(f"Error adding data: {e}")
