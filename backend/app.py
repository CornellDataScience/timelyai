# from google.cloud import firestore
# from datetime import datetime

# # Initialize Firestore
# db = firestore.Client()

# timestamp = datetime.now()

# data = {
#     "Tasks": {
#         "MATH HW:": {
#             "category": "School",
#             "deadline": timestamp,
#             "duration": 4
#         },
#     },
#     "User Preferences": {
#         "Goals" : {
#             "Clubs": 10,
#             "Health & Fitness": 5,
#             "Hobbies": 10,
#             "Job": 0,
#             "Other": 0,
#             "School": 40,
#             "Sleep": 56,
#             "Social": 15
#         },
#         "Sleep" : {
#             "Bedtime": "11:00pm EST",
#             "Wakeup": "7:00am EST"
#         }
#     }
# }

# #Specify the collection and document name

# collection_name = "user_preferences" 
# document_name = "user4"  


# # Add the data to Firestore
# try:
#     doc_ref = db.collection(collection_name).document(document_name)
#     doc_ref.set(data)
#     print(f"Data added successfully to document: {doc_ref.id}")
# except Exception as e:
#     print(f"Error adding data: {e}")


# # Example of adding data with an auto-generated ID:
# #try:
#     #doc_ref = db.collection(collection_name).add(data)
#     #print(f"Data added successfully to document: {doc_ref[1].id}")

# #except Exception as e:
#     #print(f"Error adding data: {e}")

from flask import Flask, request, jsonify
from flask_cors import CORS
from firestoreAPI import firestore_module as FB
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

@app.route('/api/add-task', methods=['POST'])
def add_task():
    print("🚀 Incoming POST to /api/add-task")
    data = request.get_json()
    userId = data.get('userId')
    task = data.get('taskDetails')
   
    print(f"✅ Task received from {userId}: {task}")

    db = FB.initializeDB()
    task_id = FB.addTask(db,userId,task["title"], task["duration"], task["category"],task["dueDate"])
    print(f"✅ Task added to {userId}: {task_id}")
    # You can now do something with the task here, like:
    # - Save to DB
    # - Run your optimizer
    # - Respond with a suggested schedule

    return jsonify({'status': 'success', 'message': 'Task processed', 'received': task})


@app.route('/api/edit-task', methods=['POST'])
def edit_task():
    print("🚀 Incoming POST to /api/edit-task")
    data = request.get_json()
    userId = data.get('userId')
    task = data.get('taskDetails')
    taskId = data.get('taskId')
   
    print(f"✅ Task received from {userId}: {task}")

    db = FB.initializeDB()
    task_id = FB.updateTask(db,userId,taskId,task["title"], task["duration"], task["category"],task["dueDate"])
    print(f"✅ Task added to {userId}: {task_id}")
   
    # You can now do something with the task here, like:
    # - Save to DB
    # - Run your optimizer
    # - Respond with a suggested schedule

    return jsonify({'status': 'success', 'message': 'Task processed', 'received': task})



if __name__ == '__main__':
    app.run(port=8888)