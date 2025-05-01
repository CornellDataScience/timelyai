from flask import Flask, request, jsonify
from flask_cors import CORS
from firestoreAPI import firestore_module as FB
from datetime import datetime
import json
from flask import request, jsonify
from googleCalendarAPI.googleCalendarAPI import GoogleCalendar  # ← your helper class
from datetime import datetime, timedelta
import pytz
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
TOKEN_DIR = os.path.join(project_root, "timelyai/token.json")  # one JSON per user
CREDS_JSON = os.path.join(
    project_root, "timelyai/user_credentials.json"
)  # OAuth client-secret


app = Flask(__name__)
CORS(app)


@app.route("/api/tasks", methods=["POST"])
def add_task():
    print("🚀 Incoming POST to /api/tasks")
    data = request.get_json()
    userId = data.get("userId")
    task = data.get("taskDetails")

    print(f"✅ Task received from {userId}: {task}")

    db = FB.initializeDB()
    task_id = FB.addTask(
        db, userId, task["title"], task["duration"], task["category"], task["dueDate"]
    )
    print(f"✅ Task added to {userId}: {task_id}")
    # You can now do something with the task here, like:
    # - Save to DB
    # - Run your optimizer
    # - Respond with a suggested schedule

    return jsonify({"status": "success", "message": "Task processed", "received": task})


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


@app.route("/api/tasks", methods=["GET"])
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
        tasks.append(
            {
                "id": task_id,
                "title": task_data.get("taskName", "Untitled"),
                "dueDate": task_data.get("taskDeadline", "TBD"),
                "duration": task_data.get("taskDuration", "TBD"),
                "category": task_data.get("taskCategory", "None"),
            }
        )

    return jsonify(tasks)


@app.route("/api/goals", methods=["POST"])
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
        doc_ref.set({"Goals": goals}, merge=True)
        print(f"✅ Goals saved for user {user_id}")
        return jsonify({"status": "success", "message": "Goals saved"})
    except Exception as e:
        print(f"❌ Error saving goals: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/goals", methods=["GET"])
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


# @app.route("/api/generate-recs", methods=["POST"])
# def generate_recommendations():
#     print("🚀 Incoming POST to /api/generate-recs")
#     data = request.get_json()
#     user_id = data.get("userId")

#     if not user_id:
#         return jsonify({"status": "error", "message": "Missing userId"}), 400

#     try:
#         # TODO: Replace with real model call or logic
#         fake_recommendations = [
#             "📚 Study 2 hours tonight for CS exam",
#             "🎨 Spend 1 hour on hobbies this weekend",
#             "💬 Call a friend on Friday",
#         ]
#         print(f"✅ Generated recommendations for {user_id}")
#         return jsonify({"status": "success", "recommendations": fake_recommendations})
#     except Exception as e:
#         print(f"❌ Error generating recommendations: {e}")
#         return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate-recs", methods=["POST"])
def generate_recommendations():
    print("🚀 Incoming POST to /api/generate-recs")
    data = request.get_json(silent=True) or {}
    user_id = data.get("userId")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId"}), 400

    # ---------------------------------------------------------------------
    # 1.  Build / fetch recommendations  (replace with real ML later)
    # ---------------------------------------------------------------------
    fake_recommendations = [
        {
            "summary": "📚 Study 2 h for CS exam",
            "start_in": 2,
            "duration_h": 2,
        },  # start in N hours
        {"summary": "🎨 Work on hobbies", "start_in": 26, "duration_h": 1},
        {"summary": "💬 Call a friend", "start_in": 50, "duration_h": 0.5},
    ]

    # ---------------------------------------------------------------------
    # 2.  Connect to Google Calendar as *this* user
    # ---------------------------------------------------------------------
    # token_path = os.path.join(TOKEN_DIR, f"{user_id}.json")
    gcal = GoogleCalendar(credentials_path=CREDS_JSON, token_path=TOKEN_DIR)

    # ---------------------------------------------------------------------
    # 3.  Create calendar events
    # ---------------------------------------------------------------------
    tz = pytz.timezone("America/New_York")  # adjust as you like
    event_urls = []

    for rec in fake_recommendations:
        start_dt = datetime.now(tz) + timedelta(hours=rec["start_in"])
        end_dt = start_dt + timedelta(hours=rec["duration_h"])

        try:
            event = gcal.create_event(
                summary=rec["summary"],
                description=rec["summary"],  # ← quick placeholder
                start_time=start_dt,
                end_time=end_dt,
            )
            event_urls.append(event.get("htmlLink"))
            print(f"✅ Created event «{rec['summary']}»")
        except Exception as e:
            print(f"❌ Failed to create event «{rec['summary']}»: {e}")

    return jsonify(
        {
            "status": "success",
            "recommendations": [r["summary"] for r in fake_recommendations],
            "eventLinks": event_urls,
        }
    )


if __name__ == "__main__":
    app.run(port=8888)
