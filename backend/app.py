from flask import Flask, request, jsonify
from flask_cors import CORS
from firestoreAPI import firestore_module as FB
from datetime import datetime
import json
from flask import request, jsonify
from googleCalendarAPI.googleCalendarAPI import GoogleCalendar
from datetime import datetime, timedelta, time as dtime
import pytz
import os
import sys
import random

# Add the parent directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
timelyai_dir = os.path.join(project_root, "timelyai")
sys.path.append(timelyai_dir)
sys.path.append(os.path.join(timelyai_dir, "ml"))
sys.path.append(os.path.join(timelyai_dir, "ml", "model"))

from ml.model.contextual_bandits import generate_recommendations

TOKEN_DIR = os.path.join(project_root, "timelyai/token.json")
CREDS_JSON = os.path.join(project_root, "timelyai/user_credentials.json")
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


def iso_to_dt(iso_str, tz):
    try:
        # Parse the ISO string to datetime
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # If the datetime is naive (no timezone), localize it
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        return dt
    except Exception as e:
        print(f"Error parsing datetime {iso_str}: {str(e)}")
        return None


def get_busy_slots_from_calendar(gcal):
    try:
        now = datetime.now(tz)
        events = gcal.list_upcoming_events(max_results=250, time_min=now.isoformat())
        busy_slots = []
        for e in events:
            try:
                start_str = e["start"].get("dateTime", e["start"].get("date"))
                end_str = e["end"].get("dateTime", e["end"].get("date"))
                if start_str and end_str:
                    start = iso_to_dt(start_str, tz)
                    end = iso_to_dt(end_str, tz)
                    if start and end:  # Only add if both times were parsed successfully
                        busy_slots.append((start, end))
            except Exception as e:
                print(f"Error processing event: {str(e)}")
                continue
        return busy_slots
    except Exception as e:
        print(f"Error fetching calendar events: {str(e)}")
        return []  # Return empty list if we can't fetch events


def load_previous_recs(uid, db):
    doc = db.collection("UserTasks").document(uid).get()
    if not doc.exists:
        return []
    rec_doc = doc.to_dict().get("lastRecommendations", [])
    return [(r["start"], r["duration"]) for r in rec_doc]


def save_recommendations(uid, recommendations, db):
    doc_ref = db.collection("UserTasks").document(uid)
    doc_ref.update(
        {
            "lastRecommendations": [
                {"start": start_dt.isoformat(), "duration": dur}
                for _, start_dt, dur in recommendations
            ]
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Generate up-to-five urgent task recommendations and create Calendar events
#  • never schedule 01:00-05:00  (sleep window)
#  • never overlap existing events or past recommendations
#  • works with hourly offsets returned by generate_recommendations()
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timedelta
import os, pytz, traceback
from flask import request, jsonify

TZ = pytz.timezone("America/New_York")
SLEEP_START = 1  # 01:00
SLEEP_END = 5  # 05:00


def slot_conflict(start, end, slots):
    for s in slots:
        if start < s["end"] and end > s["start"]:
            return s
    return None


def build_free_mask(now, busy, horizon_days=7):
    """
    Return list[int] length 24*horizon_days; 1 = free, 0 = busy/sleep.
    """
    mask = []
    for day in range(horizon_days):
        for hour in range(24):
            slot_start = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                days=day, hours=hour
            )
            slot_end = slot_start + timedelta(hours=1)

            # hard ban 01-05
            if 1 <= slot_start.hour < 5:
                mask.append(0)
                continue

            if slot_conflict(slot_start, slot_end, busy):
                mask.append(0)
            else:
                mask.append(1)
    return mask


def violates_sleep(start, end):
    # forbid any part that is strictly between 01:00 and 05:00
    midnight = start.replace(hour=0, minute=0, second=0, microsecond=0)
    ban_start = midnight + timedelta(hours=1)
    ban_end = midnight + timedelta(hours=5)
    return not (end <= ban_start or start >= ban_end)


@app.route("/api/generate-recs", methods=["POST"])
def generate_recommendations_endpoint():
    print("🚀 Incoming POST to /api/generate-recommendations")
    data = request.get_json(silent=True) or {}
    user_id = data.get("userId")
    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId"}), 400

    # ─── Pull tasks from Firestore ───────────────────────────────────────────
    db = FB.initializeDB()
    user_doc = db.collection("UserTasks").document(user_id).get()
    if not user_doc.exists:
        return jsonify({"status": "error", "message": "No tasks for user"}), 400
    tasks_map = user_doc.to_dict().get("tasks", {})
    print(f"Found {len(tasks_map)} tasks")
    print(f"Got tasks")

    # ─── Helper: robust deadline parser ──────────────────────────────────────
    def _due_dt(task):
        raw = task.get("taskDeadline")
        try:
            d = datetime.strptime(raw, "%Y-%m-%d")
        except Exception:
            try:
                d = datetime.strptime(raw, "%m/%d/%y")
            except Exception:
                # fallback: seven days from now
                d = datetime.now(TZ) + timedelta(days=7)
        return TZ.localize(d).replace(hour=23, minute=59)

    # pick top-5 urgent (nearest due-date, then longer duration first)
    tasks_sorted = sorted(
        tasks_map.values(), key=lambda t: (_due_dt(t), -float(t.get("taskDuration", 1)))
    )[:5]
    print(f"Processing {len(tasks_sorted)} most-urgent tasks")

    # ─── Google Calendar + existing busy slots ───────────────────────────────
    token_path = os.path.join(os.path.dirname(TOKEN_DIR), "token.json")
    if not os.path.exists(token_path):
        return jsonify({"status": "error", "message": "User not authenticated"}), 401
    gcal = GoogleCalendar(credentials_path=CREDS_JSON, token_path=token_path)

    def _iso_to_dt(iso):
        if len(iso) == 10:  # all-day  YYYY-MM-DD
            iso += "T00:00:00Z"
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)

    def get_busy_slots(gcal, horizon_days: int = 7):
        """
        Return list[{start,end,title}] covering ALL calendars.
        """
        tzlocal = TZ
        now = datetime.now(tzlocal)
        horizon = now + timedelta(days=horizon_days)

        # 1) discover all calendars
        cal_ids = [
            c["id"] for c in gcal.service.calendarList().list().execute()["items"]
        ]

        # 2) freeBusy query
        body = {
            "timeMin": now.isoformat(),
            "timeMax": horizon.isoformat(),
            "items": [{"id": cid} for cid in cal_ids],
        }
        fb = gcal.service.freebusy().query(body=body).execute()

        busy = []
        for cid, data in fb["calendars"].items():
            for interval in data.get("busy", []):
                # Handle UTC 'Z' suffix by replacing with +00:00
                s = datetime.fromisoformat(
                    interval["start"].replace("Z", "+00:00")
                ).astimezone(tzlocal)
                e = datetime.fromisoformat(
                    interval["end"].replace("Z", "+00:00")
                ).astimezone(tzlocal)
                busy.append({"start": s, "end": e, "title": f"Busy ({cid})"})
        return busy

    busy_slots = get_busy_slots(gcal)
    print(f"{len(busy_slots)} busy slots from Calendar")

    def get_busy_slots_from_calendar(gcal):
        try:
            now = datetime.now(tz)
            events = gcal.list_upcoming_events(
                max_results=250, time_min=now.isoformat()
            )
            busy_slots = []
            for e in events:
                try:
                    start_str = e["start"].get("dateTime", e["start"].get("date"))
                    end_str = e["end"].get("dateTime", e["end"].get("date"))
                    if start_str and end_str:
                        start = iso_to_dt(start_str, tz)
                        end = iso_to_dt(end_str, tz)
                        if (
                            start and end
                        ):  # Only add if both times were parsed successfully
                            busy_slots.append((start, end))
                except Exception as e:
                    print(f"Error processing event: {str(e)}")
                    continue
            return busy_slots
        except Exception as e:
            print(f"Error fetching calendar events: {str(e)}")
            return []  # Return empty list if we can't fetch events

    def load_previous_recs(uid, db):
        doc = db.collection("UserTasks").document(uid).get()
        if not doc.exists:
            return []
        rec_doc = doc.to_dict().get("lastRecommendations", [])
        return [(r["start"], r["duration"]) for r in rec_doc]

    def save_recommendations(uid, recommendations, db):
        doc_ref = db.collection("UserTasks").document(uid)
        doc_ref.update(
            {
                "lastRecommendations": [
                    {"start": start_dt.isoformat(), "duration": dur}
                    for _, start_dt, dur in recommendations
                ]
            }
        )

    # previous recommendations (so repeated calls stay unique)
    def load_prev_recs():
        recs = user_doc.to_dict().get("lastRecommendations", [])
        slots = []
        for r in recs:
            try:
                st = _iso_to_dt(r["start"])
                slots.append(
                    {
                        "start": st,
                        "end": st + timedelta(hours=float(r["duration"])),
                        "title": r["title"],
                    }
                )
            except Exception:
                continue
        return slots

    used_time_slots = load_prev_recs()
    print(f"{len(used_time_slots)} past recommendations loaded")

    # ─── Main loop over tasks ────────────────────────────────────────────────
    all_recs = []  # [(title,start_dt,dur_hrs)]
    now = datetime.now(TZ)

    # Build availability vector once per run
    availability_vector = build_free_mask(now, busy_slots + used_time_slots)

    for task in tasks_sorted:
        print(f"Processing task: {task}")
        title = task.get("taskName", "Untitled")
        cat = task.get("taskCategory", "general")
        dur_hrs = float(task.get("taskDuration", 1))
        due_dt = _due_dt(task)
        hrs_left = (due_dt - now).total_seconds() / 3600
        print(f"\nTask «{title}»  due in {hrs_left:.1f} h")

        if hrs_left <= dur_hrs + 1:  # must finish before deadline
            print("  ⤷ too little time remaining, skipping")
            continue

        # context for model
        context = [
            {
                "name": t.get("taskName", "Untitled"),
                "duration": float(t.get("taskDuration", 1)),
                "due_date": t.get("taskDeadline", "TBD"),
                "category": t.get("taskCategory", "None"),
            }
            for t in tasks_sorted
            if t is not task
        ]

        max_tries = 10
        placed = False

        for attempt in range(1, max_tries + 1):
            recs = generate_recommendations(
                task_type=cat,
                task_duration=dur_hrs,
                hours_until_due=hrs_left,
                daily_free_time=8.0,
                day_of_week=now.weekday(),
                prefer_splitting=True,
                context_tasks=context,
                availability_vector=availability_vector,  # NEW
                top_k=6,  # NEW
            )

            if not recs:
                # tell model this attempt failed -> encourage exploration
                generate_recommendations(
                    task_type=cat,
                    task_duration=dur_hrs,
                    hours_until_due=hrs_left,
                    daily_free_time=8.0,
                    day_of_week=now.weekday(),
                    prefer_splitting=True,
                    context_tasks=context,
                    reward=-1,
                )
                continue

            if isinstance(recs, tuple):
                recs = [recs]

            # iterate through the up-to-6 candidate slots
            for _, offset_h, d in recs:
                start_dt = now + timedelta(hours=float(offset_h))
                end_dt = start_dt + timedelta(hours=float(d))

                if violates_sleep(start_dt, end_dt):
                    continue
                if slot_conflict(start_dt, end_dt, busy_slots + used_time_slots):
                    continue
                if end_dt > due_dt:
                    continue

                # accept slot ---------------------------------------------------------
                all_recs.append((f"⏰ {title}", start_dt, float(d)))
                used_time_slots.append(
                    {"start": start_dt, "end": end_dt, "title": f"⏰ {title}"}
                )
                print(
                    f"  ✓ scheduled {start_dt:%a %m-%d %H:%M} for {d} h (try {attempt})"
                )
                placed = True
                break  # stop iterating rec list

            if placed:
                break  # stop tries loop
            else:
                # negative reward for each rejected rec list
                generate_recommendations(
                    task_type=cat,
                    task_duration=dur_hrs,
                    hours_until_due=hrs_left,
                    daily_free_time=8.0,
                    day_of_week=now.weekday(),
                    prefer_splitting=True,
                    context_tasks=context,
                    reward=-1,
                )

        if not placed:
            print("  ⤷ no valid recommendation after exploration")

    if not all_recs:
        return jsonify({"status": "error", "message": "No valid slots"}), 409

    # ─── Create Calendar events ──────────────────────────────────────────────
    print(f"Creating {len(all_recs)} events")
    links = []
    for summary, start_dt, d in all_recs:
        try:
            ev = gcal.create_event(
                summary=summary,
                description=summary,
                start_time=start_dt,
                end_time=start_dt + timedelta(hours=d),
                color_id="5",
            )
            if ev and "htmlLink" in ev:
                links.append(ev["htmlLink"])
        except Exception:
            traceback.print_exc()

    # persist for uniqueness next call
    db.collection("UserTasks").document(user_id).set(
        {
            "lastRecommendations": [
                {"title": r[0], "start": r[1].isoformat(), "duration": r[2]}
                for r in all_recs
            ]
        },
        merge=True,
    )
    print(f"Created {len(all_recs)} events")
    return jsonify(
        {
            "status": "success",
            "recommendations": [
                {"title": r[0], "start": r[1].isoformat(), "duration": r[2]}
                for r in all_recs
            ],
            "eventLinks": links,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    app.run(port=8888)
