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
import atexit

# Add the parent directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
timelyai_dir = os.path.join(project_root, "timelyai")
sys.path.append(timelyai_dir)
sys.path.append(os.path.join(timelyai_dir, "ml"))
sys.path.append(os.path.join(timelyai_dir, "ml", "model"))

# Now we can import the VW bandit
from model.vw_bandit import vw_recommend, vw_feedback, save_model

# Register model save on exit
atexit.register(save_model)

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


def build_free_mask(now, busy, horizon_hours):
    """
    Return list[int] length horizon_hours; 1 = free, 0 = busy/sleep.
    """
    mask = []
    for hour in range(horizon_hours):
        slot_start = now.replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=hour
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


def _due_dt(task):
    """Helper: robust deadline parser."""
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


def load_tasks_with_remaining_hours(uid, db):
    """Load tasks that still have remaining hours to schedule."""
    doc = db.collection("UserTasks").document(uid).get()
    if not doc.exists:
        return []

    tasks_map = doc.to_dict().get("tasks", {})
    tasks_to_plan = []

    for tid, t in tasks_map.items():
        # Initialize remainingHours if not present
        if "remainingHours" not in t:
            db.collection("UserTasks").document(uid).update(
                {f"tasks.{tid}.remainingHours": float(t.get("taskDuration", 0))}
            )
            rem = float(t.get("taskDuration", 0))
        else:
            rem = float(t.get("remainingHours", 0))

        if rem > 0:
            tasks_to_plan.append((tid, t, rem))

    # Order by nearest deadline then largest remaining
    tasks_to_plan.sort(key=lambda x: (_due_dt(x[1]), -x[2]))  # remainingHours
    return tasks_to_plan[:5]  # top-5 urgent


def get_busy_slots(gcal, horizon_days: int = 7):
    """
    Return list[{start,end,title}] covering ALL calendars.
    """
    tzlocal = TZ
    now = datetime.now(tzlocal)
    horizon = now + timedelta(days=horizon_days)

    # 1) discover all calendars
    cal_ids = [c["id"] for c in gcal.service.calendarList().list().execute()["items"]]

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


def load_future_scheduled_slots(uid, db):
    """Load future scheduled slots from Firestore."""
    now = datetime.now(TZ)
    slots_ref = db.collection("ScheduledSlots").document(uid)
    future_slots = []

    # Get tasks map for title lookup
    tasks_map = (
        db.collection("UserTasks").document(uid).get().to_dict().get("tasks", {})
    )

    for s in slots_ref.collections():  # each sub-collection could be a month
        for slot_doc in s.stream():
            slot = slot_doc.to_dict()
            st = iso_to_dt(slot["start"], TZ)
            if st > now:  # ignore past slices
                future_slots.append(
                    {
                        "start": st,
                        "end": iso_to_dt(slot["end"], TZ),
                        "title": f"⏰ {tasks_map[slot['taskId']]['taskName']}",
                    }
                )
    return future_slots


def save_scheduled_slot(uid, task_id, start_dt, end_dt, db):
    """Save a scheduled slot to Firestore."""
    month_key = start_dt.strftime("%Y-%m")
    slots_ref = db.collection("ScheduledSlots").document(uid).collection(month_key)

    slots_ref.add(
        {
            "taskId": task_id,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "createdAt": datetime.now(TZ).isoformat(),
        }
    )


@app.route("/api/generate-recs", methods=["POST"])
def generate_recommendations_endpoint():
    print("🚀 Incoming POST to /api/generate-recommendations")
    data = request.get_json(silent=True) or {}
    user_id = data.get("userId")
    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId"}), 400

    # ─── Load tasks with remaining hours ───────────────────────────────────
    db = FB.initializeDB()
    tasks_to_plan = load_tasks_with_remaining_hours(user_id, db)
    if not tasks_to_plan:
        return jsonify({"status": "error", "message": "No tasks to schedule"}), 400
    print(f"Found {len(tasks_to_plan)} tasks with remaining hours")

    # ─── Google Calendar + existing busy slots ───────────────────────────────
    token_path = os.path.join(os.path.dirname(TOKEN_DIR), "token.json")
    if not os.path.exists(token_path):
        return jsonify({"status": "error", "message": "User not authenticated"}), 401
    gcal = GoogleCalendar(credentials_path=CREDS_JSON, token_path=token_path)

    # Get busy slots from calendar and future scheduled slots
    calendar_busy = get_busy_slots(gcal)
    future_slots = load_future_scheduled_slots(user_id, db)
    busy_slots = calendar_busy + future_slots
    print(f"{len(busy_slots)} busy slots from Calendar and scheduled slots")

    # Debug: Print all busy slots
    print("\n🛑 Busy slots:")
    for s in busy_slots:
        print(f"  {s['start']} to {s['end']} - {s.get('title','')}")
    print()

    # ─── Main loop over tasks ────────────────────────────────────────────────
    all_recs = []  # [(task_id, title, start_dt, dur_hrs)]
    now = datetime.now(TZ)

    # ────── build availability vector with dynamic horizon ──────
    max_hrs_left = max(
        ((_due_dt(t) - now).total_seconds() / 3600) for _, t, _ in tasks_to_plan
    )
    horizon_hours = int(min(max_hrs_left, 720))  # ≤ 30 days
    availability_vector = build_free_mask(now, busy_slots, horizon_hours)
    print(f"Mask spans {horizon_hours} h; free hours = {sum(availability_vector)}")

    # Build candidate hours from availability vector
    candidate_hours = [h for h, v in enumerate(availability_vector) if v]
    print(f"Found {len(candidate_hours)} candidate hours")

    for task_id, task, remaining_hours in tasks_to_plan:
        print(f"Processing task: {task}")
        title = task.get("taskName", "Untitled")
        cat = task.get("taskCategory", "general")
        dur_hrs = min(
            float(task.get("taskDuration", 1)), remaining_hours
        )  # Don't schedule more than remaining
        due_dt = _due_dt(task)
        hrs_left = (due_dt - now).total_seconds() / 3600
        print(
            f"\nTask «{title}»  due in {hrs_left:.1f} h, {remaining_hours:.1f} h remaining"
        )

        if hrs_left <= dur_hrs + 1:  # must finish before deadline
            print("  ⤷ too little time remaining, skipping")
            continue

        # Get recommendations from VW bandit
        recs = vw_recommend(
            task_type=cat,
            task_duration=dur_hrs,
            hrs_until_due=hrs_left,
            day_of_week=now.weekday(),
            candidate_hours=candidate_hours,
            top_k=6,
            prefer_splitting=True,
        )

        if not recs:
            # Give negative feedback for the first candidate hour
            if candidate_hours:
                prob = 1.0 / len(candidate_hours)
                vw_feedback(
                    task_type=cat,
                    task_duration=dur_hrs,
                    hrs_until_due=hrs_left,
                    day_of_week=now.weekday(),
                    chosen_hour=candidate_hours[0],
                    cost=1.0,  # cost 1 == bad
                    prob=prob,
                )
            continue

        placed = False
        for offset_h, chunk_dur in recs:
            start_dt = now + timedelta(hours=float(offset_h))
            end_dt = start_dt + timedelta(hours=float(chunk_dur))

            if violates_sleep(start_dt, end_dt):
                continue
            if slot_conflict(start_dt, end_dt, busy_slots):
                continue
            if end_dt > due_dt:
                continue

            # accept slot ---------------------------------------------------------
            all_recs.append((task_id, f"⏰ {title}", start_dt, float(chunk_dur)))
            busy_slots.append(
                {"start": start_dt, "end": end_dt, "title": f"⏰ {title}"}
            )

            # Update remaining hours
            new_remaining = remaining_hours - float(chunk_dur)
            db.collection("UserTasks").document(user_id).update(
                {f"tasks.{task_id}.remainingHours": new_remaining}
            )

            # Save to scheduled slots
            save_scheduled_slot(user_id, task_id, start_dt, end_dt, db)

            # Give positive feedback
            prob = 1.0 / len(candidate_hours)
            vw_feedback(
                task_type=cat,
                task_duration=chunk_dur,
                hrs_until_due=hrs_left,
                day_of_week=now.weekday(),
                chosen_hour=offset_h,
                cost=0.0,  # cost 0 == reward 1
                prob=prob,
            )

            print(f"  ✓ scheduled {start_dt:%a %m-%d %H:%M} for {chunk_dur} h")
            placed = True
            break

        if not placed:
            print("  ⤷ no valid recommendation after exploration")

    if not all_recs:
        return jsonify({"status": "error", "message": "No valid slots"}), 409

    # ─── Create Calendar events ────────────────────────────────────────────
    print(f"Creating {len(all_recs)} events")
    links = []

    def safe_schedule(title, start_dt, dur, task_id):
        """Return htmlLink or None."""
        # 1. TZ-aware and rounded
        if start_dt.tzinfo is None:
            start_dt = TZ.localize(start_dt)
        start_dt = start_dt.replace(second=0, microsecond=0)
        end_dt = start_dt + timedelta(hours=dur)
        # 2. guard: start in the past?
        now_local = datetime.now(TZ).replace(second=0, microsecond=0)
        if start_dt < now_local:
            start_dt = now_local + timedelta(minutes=2)
            end_dt = start_dt + timedelta(hours=dur)
        # 3. min length 15 min
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=15)

        # Create event body without custom ID
        body = {
            "summary": title,
            "description": f"Timely scheduled task: {title}",
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
            "colorId": "5",
            "extendedProperties": {
                "private": {
                    "taskId": task_id,
                    "scheduledAt": datetime.now(TZ).isoformat(),
                }
            },
        }

        try:
            ev = (
                gcal.service.events()
                .insert(calendarId="primary", body=body, sendUpdates="none")
                .execute()
            )
            return ev.get("htmlLink")
        except Exception as exc:
            # Duplicate? 409 means we already inserted it; ignore.
            if getattr(exc, "status_code", None) == 409:
                return None
            traceback.print_exc()
            return None

    for task_id, summary, start_dt, d in all_recs:
        link = safe_schedule(summary, start_dt, d, task_id)
        if link:
            links.append(link)

    # Save the VW model after successful scheduling
    save_model()

    return jsonify(
        {
            "status": "success",
            "recommendations": [
                {"title": r[1], "start": r[2].isoformat(), "duration": r[3]}
                for r in all_recs
            ],
            "eventLinks": links,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    app.run(port=8888)
