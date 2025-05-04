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

@app.route('/api/tasks', methods=['POST', 'PUT'])  # Accept both POST and PUT
def add_or_edit_task():
    print("🚀 Incoming request to /api/tasks")

    data = request.get_json()
    print("📦 Incoming JSON payload:")
    print(data)
    print("🔎 taskId:", data.get("taskId"))

    user_id = data.get("userId")
    task = data.get("taskDetails")
    task_id = data.get("taskId")  # ✅ FIXED: use the correct key

    db = FB.initializeDB()

    if not user_id or not task:
        return jsonify({"status": "error", "message": "Missing user or task data"}), 400

    try:
        if task_id:
            print(f"✏️ Updating task {task_id} for {user_id}")
            success = FB.updateTask(
                db,
                user_id,
                task_id,
                task["taskName"],
                task["taskDuration"],
                task["taskCategory"],
                task["taskDeadline"]
            )
            if success:
                return jsonify({"status": "success", "message": "Task updated"})
            else:
                print("❌ Update failed — task ID not found in Firestore.")
                return jsonify({"status": "error", "message": "Task not found"}), 404
        else:
            print(f"➕ Adding task for {user_id}")
            new_task_id = FB.addTask(
                db,
                user_id,
                task["taskName"],
                task["taskDuration"],
                task["taskCategory"],
                task["taskDeadline"]
            )
            return jsonify({"status": "success", "message": "Task added", "taskId": new_task_id})
    except Exception as e:
        print(f"❌ Error processing task: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# @app.route('/api/tasks', methods=['POST'])
# def edit_task():
#     print("🚀 Incoming POST to /api/edit-task")
#     data = request.get_json()
#     userId = data.get('userId')
#     task = data.get('taskDetails')
#     taskId = data.get('taskId')
   
#     print(f"✅ Task received from {userId}: {task}")

#     db = FB.initializeDB()
#     task_id = FB.updateTask(db,userId,taskId,task["title"], task["duration"], task["category"],task["dueDate"])
#     print(f"✅ Task added to {userId}: {task_id}")
   
#     # You can now do something with the task here, like:
#     # - Save to DB
#     # - Run your optimizer
#     # - Respond with a suggested schedule

#     return jsonify({'status': 'success', 'message': 'Task processed', 'received': task})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    user_id = request.args.get("userId")
    db = FB.initializeDB()
    doc_ref = db.collection("UserTasks").document(user_id)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify([])

    tasks_map = doc.to_dict().get("tasks", {})
    tasks = []

    for task_id, task_data in tasks_map.items():
        tasks.append({
            "id": task_id,
            "title": task_data.get("taskName", "Untitled"),
            "dueDate": task_data.get("taskDeadline", "TBD"),
            "duration": task_data.get("taskDuration", "TBD"),
            "category": task_data.get("taskCategory", "None")
        })

    return jsonify(tasks)

@app.route('/api/goals', methods=['POST'])
def save_goals():
    print("🚀 Incoming POST to /api/goals")
    data = request.get_json()
    user_id = data.get("userId")
    goals = data.get("goals")

    if not user_id or not goals:
        return jsonify({"status": "error", "message": "Missing userId or goals"}), 400

    db = FB.initializeDB()
    doc_ref = db.collection("UserPreferences").document(user_id)

    try:
        doc_ref.set({ "Goals": goals }, merge=True)
        print(f"✅ Goals saved for user {user_id}")
        return jsonify({"status": "success", "message": "Goals saved"})
    except Exception as e:
        print(f"❌ Error saving goals: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/goals', methods=['GET'])
def load_goals():
    user_id = request.args.get("userId")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId"}), 400

    db = FB.initializeDB()
    doc_ref = db.collection("UserPreferences").document(user_id)

    try:
        doc = doc_ref.get()
        if not doc.exists:
            print(f"⚠️ No goals found for user {user_id}")
            return jsonify({"goals": {}})
        
        goals = doc.to_dict().get("Goals", {})
        print(f"✅ Loaded goals for {user_id}: {goals}")
        return jsonify({"goals": goals})
    except Exception as e:
        print(f"❌ Error loading goals: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/api/generate-recs', methods=['POST'])
def generate_recommendations():
    print("🚀 Incoming POST to /api/generate-recs")
    data = request.get_json()
    user_id = data.get("userId")

    if not user_id:
        return jsonify({ "status": "error", "message": "Missing userId" }), 400

    try:
        # TODO: Replace with real model call or logic
        fake_recommendations = [
            "📚 Study 2 hours tonight for CS exam",
            "🎨 Spend 1 hour on hobbies this weekend",
            "💬 Call a friend on Friday"
        ]
        print(f"✅ Generated recommendations for {user_id}")
        return jsonify({ "status": "success", "recommendations": fake_recommendations })
    except Exception as e:
        print(f"❌ Error generating recommendations: {e}")
        return jsonify({ "status": "error", "message": str(e) }), 500

@app.route('/api/delete-task', methods=['DELETE'])
def delete_task_route():
    data = request.get_json()
    user_id = data.get("userId")
    task_id = data.get("taskId")

    print(f"➡️ Received delete request: userId={user_id}, taskId={task_id}")

    db = FB.initializeDB()
    if not user_id or not task_id:
        return jsonify({"status": "error", "message": "Missing userId or taskId"}), 400

    try:
        success = FB.deleteTask(db, user_id, task_id)
        if success:
            return jsonify({"status": "success", "message": f"Task {task_id} deleted"})
        else:
            return jsonify({"status": "error", "message": "Task not found"}), 404
    except Exception as e:
        print(f"❌ Error deleting task: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=8888)
