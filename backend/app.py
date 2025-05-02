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
import sys
import random

# Add the parent directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
timelyai_dir = os.path.join(project_root, "timelyai")
sys.path.append(timelyai_dir)

from ml.model.contextual_bandits import generate_recommendations

TOKEN_DIR = os.path.join(project_root, "timelyai/token.json")  # one JSON per user
CREDS_JSON = os.path.join(
    project_root, "timelyai/user_credentials.json"
)  # OAuth client-secret
tz = pytz.timezone("America/New_York")

app = Flask(__name__)
CORS(app)


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json()
    userId = data.get("userId")
    task = data.get("taskDetails")

    db = FB.initializeDB()
    task_id = FB.addTask(
        db, userId, task["title"], task["duration"], task["category"], task["dueDate"]
    )

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
    data = request.get_json()
    user_id = data.get("userId")
    goals = data.get("goals")

    if not user_id or not goals:
        return jsonify({"status": "error", "message": "Missing userId or goals"}), 400

    db = FB.initializeDB()
    doc_ref = db.collection("UserPreferences").document(user_id)

    try:
        doc_ref.set({"Goals": goals}, merge=True)
        return jsonify({"status": "success", "message": "Goals saved"})
    except Exception as e:
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
            return jsonify({"goals": {}})

        goals = doc.to_dict().get("Goals", {})
        return jsonify({"goals": goals})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate-recs", methods=["POST"])
def generate_recommendations_endpoint():
    data = request.get_json(silent=True) or {}
    user_id = data.get("userId")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId"}), 400

    db = FB.initializeDB()
    doc_ref = db.collection("UserTasks").document(user_id)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({"status": "error", "message": "No tasks found for user"}), 400

    tasks_map = doc.to_dict().get("tasks", {})

    all_recommendations = []
    all_event_links = []
    used_time_slots = []

    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(date_str, "%m/%d/%y")
            except ValueError:
                return datetime(9999, 12, 31)

    def convert_model_time_to_datetime(model_time, day_offset=0):
        now = datetime.now(tz)
        target_time = now + timedelta(hours=model_time)
        if day_offset > 0:
            target_time = target_time + timedelta(days=day_offset)
        return target_time

    def adjust_time_to_business_hours(hours_from_now, due_datetime=None):
        now = datetime.now(tz)
        target_time = now + timedelta(hours=hours_from_now)

        if due_datetime:
            if due_datetime.tzinfo is None:
                due_datetime = tz.localize(due_datetime)
            due_datetime = due_datetime - timedelta(hours=2)

            if target_time > due_datetime:
                target_time = due_datetime

        hour = target_time.hour

        if hour < 6:
            target_time = target_time.replace(hour=6, minute=0, second=0, microsecond=0)
        elif hour >= 23:
            target_time = (target_time + timedelta(days=1)).replace(
                hour=6, minute=0, second=0, microsecond=0
            )

        new_hours_from_now = (target_time - now).total_seconds() / 3600
        return new_hours_from_now

    def check_time_slot_availability(start_time, duration, existing_slots):
        slot_start = convert_model_time_to_datetime(start_time)
        slot_end = slot_start + timedelta(hours=duration)

        for existing_start, existing_duration in existing_slots:
            existing_start_dt = convert_model_time_to_datetime(existing_start)
            existing_end_dt = existing_start_dt + timedelta(hours=existing_duration)

            buffer_time = timedelta(minutes=30)

            if (
                slot_start < existing_end_dt + buffer_time
                and slot_end + buffer_time > existing_start_dt
            ):
                return False

        return True

    def get_random_time_slot(hours_until_due, duration, used_slots):
        now = datetime.now(tz)
        max_hours = min(hours_until_due - duration, 24 * 7)

        for _ in range(10):
            random_hours = random.uniform(1, max_hours)
            adjusted_time = adjust_time_to_business_hours(random_hours)

            if check_time_slot_availability(adjusted_time, duration, used_slots):
                return adjusted_time

        return None

    sorted_tasks = sorted(
        tasks_map.items(),
        key=lambda x: parse_date(x[1].get("taskDeadline", "9999-12-31")),
    )

    for task_id, task_data in sorted_tasks:
        task_name = task_data.get("taskName", "Untitled")
        task_type = task_data.get("taskCategory", "hw")
        task_duration = float(task_data.get("taskDuration", 1.0))
        due_date = task_data.get("taskDeadline", "")

        try:
            due_datetime = parse_date(due_date)
            if due_datetime.tzinfo is None:
                due_datetime = tz.localize(due_datetime)
            hours_until_due = (due_datetime - datetime.now(tz)).total_seconds() / 3600
        except (ValueError, TypeError):
            hours_until_due = 24.0
            due_datetime = None

        if hours_until_due <= 0:
            continue

        try:
            context_tasks = []

            for tid, tdata in tasks_map.items():
                if tid != task_id:
                    context_tasks.append(
                        {
                            "name": tdata.get("taskName", "Untitled"),
                            "duration": float(tdata.get("taskDuration", 1.0)),
                            "due_date": tdata.get("taskDeadline", "TBD"),
                            "category": tdata.get("taskCategory", "None"),
                        }
                    )

            for _, start_time, duration in all_recommendations:
                context_tasks.append(
                    {
                        "name": "Scheduled Task",
                        "duration": duration,
                        "due_date": "TBD",
                        "category": "blocked",
                        "start_time": start_time,
                    }
                )

            task_recommendations = []
            attempts = 0
            max_attempts = 10
            remaining_duration = task_duration

            while remaining_duration > 0 and attempts < max_attempts:
                session_duration = min(remaining_duration, 2.0)
                random_time = get_random_time_slot(
                    hours_until_due, session_duration, used_time_slots
                )

                if random_time is not None:
                    task_recommendations.append(
                        (f"⏰ {task_name}", random_time, session_duration)
                    )
                    used_time_slots.append((random_time, session_duration))
                    remaining_duration -= session_duration
                else:
                    break

                attempts += 1

            if task_recommendations:
                all_recommendations.extend(task_recommendations)

        except Exception as e:
            continue

    if not all_recommendations:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "No recommendations generated for any tasks",
                }
            ),
            500,
        )

    token_path = os.path.join(os.path.dirname(TOKEN_DIR), f"token.json")
    if not os.path.exists(token_path):
        return jsonify({"status": "error", "message": "User not authenticated"}), 401

    try:
        gcal = GoogleCalendar(credentials_path=CREDS_JSON, token_path=token_path)
    except Exception as e:
        return (
            jsonify({"status": "error", "message": "Failed to initialize calendar"}),
            500,
        )

    all_recommendations.sort(key=lambda x: x[1])

    successful_events = 0
    for summary, start_in, dur in all_recommendations:
        start = datetime.now(tz) + timedelta(hours=float(start_in))
        end = start + timedelta(hours=float(dur or 1))

        try:
            ev = gcal.create_event(
                summary=summary,
                description=summary,
                start_time=start,
                end_time=end,
                color_id="5",
            )
            if ev and "htmlLink" in ev:
                all_event_links.append(ev["htmlLink"])
                successful_events += 1
        except Exception as e:
            continue

    response = jsonify(
        {
            "status": "success",
            "recommendations": [r[0] for r in all_recommendations],
            "eventLinks": all_event_links,
        }
    )
    return response


if __name__ == "__main__":
    app.run(port=8888)
