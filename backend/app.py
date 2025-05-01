from flask import Flask, request, jsonify
from flask_cors import CORS
from firestoreAPI import firestore_module as FB
from datetime import datetime, timedelta
import json
import os
from timelyai.backend.googleCalendarAPI.googleCalendarAPI import (
    GoogleCalendar,
    DEFAULT_COLOR_ID,
)
from timelyai.backend.model_manager import ModelManager

# from timelyai.ml.model.contextual_bandits import (
#     generate_recommendations as baseline_recommendations,
#     record_binary_feedback,
#     train_model,
#     update_model,
#     reset_recommended_times,
#     add_blocked_time,
#     clear_blocked_times,
#     clear_scheduled_events,
#     add_scheduled_event,
# )

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


@app.route("/api/generate-recs", methods=["POST"])
def generate_recommendations():
    print("🚀 Incoming POST to /api/generate-recs")
    data = request.get_json()
    user_id = data.get("userId")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId"}), 400

    try:
        # Get user's tasks and preferences
        db = FB.initializeDB()
        tasks_doc = db.collection("UserTasks").document(user_id).get()
        prefs_doc = db.collection("UserPreferences").document(user_id).get()

        if not tasks_doc.exists or not prefs_doc.exists:
            return jsonify({"status": "error", "message": "User data not found"}), 404

        tasks = tasks_doc.to_dict().get("tasks", {})
        preferences = prefs_doc.to_dict().get("Goals", {})

        # Initialize Google Calendar API
        calendar = GoogleCalendar()

        # Get user's busy times
        busy_times = calendar.find_busy_slots(
            [calendar.get_user_email()], datetime.now()
        )

        # Generate recommendations using user's specific model
        recommendations = model_manager.get_recommendations(
            user_id, tasks, preferences, busy_times
        )

        # Convert recommendations to calendar events
        events = []
        for rec in recommendations:
            event = calendar.create_event(
                summary=rec["title"],
                description=rec["description"],
                start_time=rec["start_time"],
                end_time=rec["end_time"],
                color_id=rec.get("color_id", DEFAULT_COLOR_ID),
            )
            events.append(event)

        print(f"✅ Generated and scheduled {len(events)} recommendations for {user_id}")
        return jsonify(
            {
                "status": "success",
                "events": events,
                "message": f"Successfully scheduled {len(events)} events",
            }
        )
    except Exception as e:
        print(f"❌ Error generating recommendations: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/calendar/webhook", methods=["POST"])
def handle_calendar_webhook():
    print("🚀 Incoming webhook from Google Calendar")
    try:
        # Get the notification data from Google Calendar
        data = request.get_json()
        event_id = data.get("id")
        user_id = data.get(
            "userId"
        )  # This would need to be mapped from the calendar email
        status = data.get("status")  # "accepted", "declined", "tentative"

        if not all([event_id, user_id, status]):
            return (
                jsonify({"status": "error", "message": "Missing required fields"}),
                400,
            )

        # Update user's model with feedback
        model_manager.update_with_feedback(user_id, event_id, status)

        print(
            f"✅ Processed calendar webhook for event {event_id} with status {status}"
        )
        return jsonify({"status": "success", "message": "Webhook processed"})
    except Exception as e:
        print(f"❌ Error processing calendar webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def edit_task(task_id):
    print(f"🚀 Incoming PUT to /api/tasks/{task_id}")
    data = request.get_json()
    user_id = data.get("userId")
    task = data.get("taskDetails")

    if not user_id or not task:
        return (
            jsonify({"status": "error", "message": "Missing userId or task details"}),
            400,
        )

    try:
        db = FB.initializeDB()
        success = FB.updateTask(
            db,
            user_id,
            task_id,
            task["title"],
            task["duration"],
            task["category"],
            task["dueDate"],
        )

        if success:
            print(f"✅ Task {task_id} updated for user {user_id}")
            return jsonify({"status": "success", "message": "Task updated"})
        else:
            return jsonify({"status": "error", "message": "Task not found"}), 404
    except Exception as e:
        print(f"❌ Error updating task: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    print(f"🚀 Incoming DELETE to /api/tasks/{task_id}")
    user_id = request.args.get("userId")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId"}), 400

    try:
        db = FB.initializeDB()
        success = FB.deleteTask(db, user_id, task_id)

        if success:
            print(f"✅ Task {task_id} deleted for user {user_id}")
            return jsonify({"status": "success", "message": "Task deleted"})
        else:
            return jsonify({"status": "error", "message": "Task not found"}), 404
    except Exception as e:
        print(f"❌ Error deleting task: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Initialize model manager
model_manager = ModelManager()


if __name__ == "__main__":
    app.run(port=8888)
