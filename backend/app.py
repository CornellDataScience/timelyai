from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
import traceback
import sys

# Add the parent directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
timelyai_dir = os.path.join(project_root, "timelyai")
sys.path.append(timelyai_dir)
sys.path.append(os.path.join(timelyai_dir, "ml"))
sys.path.append(os.path.join(timelyai_dir, "ml", "model"))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
import firestoreAPI.firestore_module as FB
from model.vw_bandit import vw_recommend, vw_feedback, save_model
from googleCalendarAPI.googleCalendarAPI import GoogleCalendar
import atexit

# Register model save on exit
atexit.register(save_model)

app = Flask(__name__)
CORS(app)

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Google Calendar API setup
SCOPES = ["https://www.googleapis.com/auth/calendar"]
USER_CREDS_JSON = os.path.join(project_root, "user_calendar_credentials.json")
TIMELY_TOKEN_JSON = os.path.join(project_root, "timely_calendar_token.json")
TIMELY_CREDS_JSON = os.path.join(project_root, "timely_calendar_credentials.json")

# Initialize Firestore
db = FB.initializeDB()

# Timezone setup
TZ = pytz.timezone("America/New_York")

USER_TOKEN_DIR = os.path.join(project_root, "token.json")
USER_CREDS_JSON = os.path.join(project_root, "user_credentials.json")

# Remove duplicate definitions
# TIMELY_TOKEN_DIR = os.path.join(project_root, "timely_calendar_token.json")
# TIMLEY_CREDS_JSON = os.path.join(project_root, "timely_calendar_credentials.json")

tz = pytz.timezone("America/New_York")


def get_timely_calendar_service():
    """Returns a Google Calendar API service instance for TimelyAI's calendar."""
    if not os.path.exists(TIMELY_TOKEN_JSON):
        print(f"❌ Timely token file not found at: {TIMELY_TOKEN_JSON}")
        raise FileNotFoundError(f"Timely token file not found at: {TIMELY_TOKEN_JSON}")

    creds = Credentials.from_authorized_user_file(
        TIMELY_TOKEN_JSON,
        ["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=creds)


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json()
    userId = data.get("userId")
    task = data.get("taskDetails")

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


def start_calendar_watch(timely_gcal, webhook_url):
    """Set up Calendar push notifications to receive event updates."""
    # Generate a unique channel ID using timestamp
    channel_id = f"timely-ai-chan-{int(datetime.now().timestamp())}"

    body = {
        "id": channel_id,  # unique channel ID
        "type": "web_hook",
        "address": webhook_url,  # e.g. https://mydomain.com/api/calendar-webhook
        "params": {"ttl": "86400"},  # how long before you need to renew (in seconds)
    }

    print(f"🔄 Setting up calendar watch with channel ID: {channel_id}")
    return timely_gcal.events().watch(calendarId="primary", body=body).execute()


def send_invite_via_timely(
    timely_gcal,
    title,
    start_dt,
    dur,
    user_email,
    task_id,
    task_type,
    hrs_until_due,
    chosen_hour,
    prob,
):
    """
    Insert the event on TimelyAI's calendar and e‑mail the invite.
    Returns htmlLink (string) or None.
    """
    if start_dt.tzinfo is None:
        start_dt = TZ.localize(start_dt)
    end_dt = start_dt + timedelta(hours=dur)

    body = {
        "summary": title,
        "description": f"TimelyAI scheduled task «{title}»",
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
        "attendees": [{"email": user_email}],
        "extendedProperties": {
            "private": {
                "taskId": task_id,
                "scheduledAt": datetime.now(TZ).isoformat(),
            }
        },
    }

    try:
        ev = (
            timely_gcal.events()
            .insert(calendarId="primary", body=body, sendUpdates="none")
            .execute()
        )

        # --- store model context for when the user responds ---
        db.collection("InviteTracking").document(ev["id"]).set(
            {
                "taskId": task_id,
                "taskType": task_type,
                "chunkDuration": dur,
                "hrsUntilDue": hrs_until_due,
                "dayOfWeek": datetime.now(TZ).weekday(),
                "chosenHour": chosen_hour,
                "prob": prob,
                "handled": False,
                "createdAt": datetime.now(TZ).isoformat(),
            }
        )

        return ev.get("htmlLink"), ev.get("id")
    except Exception:
        traceback.print_exc()
        return None, None


@app.route("/api/calendar-webhook", methods=["POST"])
def process_feedback_webhook():
    """
    Receives push notifications from Google Calendar.
    When an invite is accepted or declined, we fetch the event,
    look up our stored context, and send a positive or negative reward.
    """
    print("\n📨 Received calendar webhook notification")

    # Google will send a bare notification; the headers carry the resource ID:
    channel_id = request.headers.get("X-Goog-Channel-ID")
    resource_id = request.headers.get("X-Goog-Resource-ID")  # calendarId
    resource_uri = request.headers.get("X-Goog-Resource-URI")  # includes ?eventId=...

    print(f"  • Channel ID: {channel_id}")
    print(f"  • Resource ID: {resource_id}")
    print(f"  • Resource URI: {resource_uri}")

    # Extract the eventId from resource_uri query-string
    from urllib.parse import urlparse, parse_qs

    event_id = parse_qs(urlparse(resource_uri).query).get("eventId", [None])[0]
    if not event_id:
        print("  ❌ No event ID found in resource URI")
        return ("", 400)

    print(f"  • Event ID: {event_id}")

    # fetch the up-to-date event from the TimelyAI calendar
    timely_gcal = get_timely_calendar_service()
    ev = timely_gcal.events().get(calendarId="primary", eventId=event_id).execute()

    # find the attendee entry for our user
    attendees = ev.get("attendees", [])
    user_att = next(
        (a for a in attendees if a.get("self") or a["email"].endswith("@cornell.edu")),
        None,
    )
    if not user_att:
        print("  ⚠️  No matching attendee found")
        return ("", 204)

    resp = user_att.get(
        "responseStatus"
    )  # "accepted", "declined", "tentative", or "needsAction"
    print(f"  • Response status: {resp}")

    # only reward when they explicitly accept or decline
    if resp not in ("accepted", "declined"):
        print("  ⚠️  Not an explicit accept/decline")
        return ("", 204)

    # load our saved context
    doc = db.collection("InviteTracking").document(event_id).get()
    if not doc.exists:
        print("  ❌ No tracking context found")
        return ("", 404)
    ctx = doc.to_dict()

    # Check if we've already handled this response
    if ctx.get("handled", False):
        print("  ⚠️  Already handled this response")
        return ("", 200)

    cost = 0.0 if resp == "accepted" else 1.0
    print(f"  • Providing feedback with cost: {cost}")

    vw_feedback(
        task_type=ctx["taskType"],
        task_duration=ctx["chunkDuration"],
        hrs_until_due=ctx["hrsUntilDue"],
        day_of_week=ctx["dayOfWeek"],
        chosen_hour=ctx["chosenHour"],
        cost=cost,
        prob=ctx["prob"],
    )

    # mark this invite as "handled" so you don't double-count
    db.collection("InviteTracking").document(event_id).update(
        {
            "handled": True,
            "responseStatus": resp,
            "feedbackAt": datetime.now(TZ).isoformat(),
        }
    )

    print("  ✅ Feedback processed successfully")
    return ("", 200)


@app.route("/api/generate-recs", methods=["POST"])
def generate_recommendations_endpoint():
    """Generate scheduling recommendations for tasks."""
    try:
        print("\n🚀 Starting recommendation generation...")
        data = request.get_json() or {}
        print(f"📦 Received request data: {json.dumps(data, indent=2)}")

        # ------------------------------------------------------------------ #
        # 1. Basic input
        # ------------------------------------------------------------------ #
        user_id = data.get("userId")
        if not user_id:
            return jsonify({"error": "Missing userId"}), 400

        # ------------------------------------------------------------------ #
        # 2. Resolve token path automatically
        # ------------------------------------------------------------------ #
        #  • first priority: constant USER_TOKEN_DIR (per‑user token file)
        #  • fall‑back: ~/.config/timelyai/<user>@token.json
        # ------------------------------------------------------------------ #
        token_path = USER_TOKEN_DIR
        # if not os.path.exists(token_path):
        #     token_path = os.path.expanduser(
        #         f"~/.config/timelyai/{user_id.replace('@', '_')}_token.json"
        #     )

        if not os.path.exists(token_path):
            print(f"❌ OAuth token not found for {user_id}: {token_path}")
            return (
                jsonify(
                    {
                        "error": "User not authenticated",
                        "expectedTokenPath": token_path,
                    }
                ),
                401,
            )

        print(f"👤 userId ..... {user_id}")
        print(f"🔑 tokenPath .. {token_path}")

        # ------------------------------------------------------------------ #
        # 3. Calendar clients
        # ------------------------------------------------------------------ #
        user_gcal = GoogleCalendar(
            credentials_path=USER_CREDS_JSON, token_path=token_path
        )
        timely_gcal = get_timely_calendar_service()
        print("✅ Calendar services initialised")

        # ------------------------------------------------------------------ #
        # 4. Load tasks, busy slots, build availability mask
        # ------------------------------------------------------------------ #
        tasks = load_tasks_with_remaining_hours(user_id, db)
        calendar_busy = get_busy_slots(user_gcal)
        future_slots = load_future_scheduled_slots(user_id, db)
        busy_slots = calendar_busy + future_slots

        now = datetime.now(TZ)
        horizon = 24 * 7  # 1 week
        free_mask = build_free_mask(now, busy_slots, horizon)
        candidate_hours = [h for h, ok in enumerate(free_mask) if ok]

        if not candidate_hours:
            print("⚠️  No free hours in the next week")
            return jsonify({"error": "No free hours in next week"}), 409

        # ------------------------------------------------------------------ #
        # 5. Iterate over tasks → VW recommendations → schedule ≤ needed hrs
        # ------------------------------------------------------------------ #
        all_recs = []  # [(task_id, summary, start_dt, dur)]
        links = []  # List to store calendar invite links
        now = datetime.now(TZ)

        def slot_ok(start_dt, dur, due_dt):
            """
            Return True if the proposed slice is
              – inside the allowed day‑time window
              – not overlapping busy slots we already know about
              – finishing **on or before the task's deadline**
            """
            end_dt = start_dt + timedelta(hours=dur)
            if end_dt > due_dt:
                return False
            if violates_sleep(start_dt, end_dt):
                return False
            return slot_conflict(start_dt, end_dt, busy_slots) is None

        print("\n📊 Model Recommendation Log:")
        print("=" * 50)

        for task_id, task, remaining in tasks:
            print(f"\n🔄 Processing task: {task.get('taskName', 'Untitled')}")
            print(f"  • ID: {task_id}")
            print(f"  • Category: {task.get('taskCategory', 'default')}")
            print(f"  • Remaining hours: {remaining:.1f}")

            if remaining <= 0:
                print("  ⏭️  Skipping - no remaining hours")
                continue

            # ── per‑task horizon and candidate list ───────────────────────
            due_dt = _due_dt(task)  # robust TZ‑aware helper
            max_off = int(((due_dt - now).total_seconds() / 3600) - 0.01)
            task_hours = [h for h in candidate_hours if h <= max_off]

            if not task_hours:
                print("  ⚠️  No time left before the deadline → skipping")
                continue

            cat = task.get("taskCategory", "default")
            print(f"  • Hours until deadline: {max_off:.1f}")
            print(f"  • Available hours: {len(task_hours)}")
            print(f"  • First few candidate hours: {task_hours[:5]}")

            vw_slots = vw_recommend(
                task_type=cat,
                task_duration=remaining,
                hrs_until_due=max_off,
                day_of_week=now.weekday(),
                candidate_hours=task_hours,
                top_k=6,  # candidates – we'll screen them
                prefer_splitting=True,
            )

            print(f"  📈 Model recommendations:")
            for i, (offset_h, dur) in enumerate(
                vw_slots, 1
            ):  # Note: vw_recommend returns (offset, duration)
                if remaining <= 0:
                    print("  ⏹️  Task hours satisfied")
                    break  # already filled this task

                dur = min(dur, remaining)  # never overshoot
                start_dt = now + timedelta(hours=offset_h)

                print(
                    f"    {i}. Start: {start_dt.strftime('%Y-%m-%d %H:%M')}, Duration: {dur:.1f}h"
                )

                if not slot_ok(start_dt, dur, due_dt):
                    print(
                        "    ❌ Slot rejected – conflicts, sleep window or after deadline"
                    )
                    continue  # try next suggestion

                # ---------- accept slot -------------------------------------------
                print(f"    ✅ Slot accepted")
                all_recs.append(
                    (task_id, task.get("taskName", "Untitled"), start_dt, dur)
                )
                busy_slots.append(
                    {
                        "start": start_dt,
                        "end": start_dt + timedelta(hours=dur),
                        "title": f"⏰ {task.get('taskName','')}",
                    }
                )

                # Remove the hours we just used from the *free* list
                used_range = range(offset_h, offset_h + int(dur))
                candidate_hours = [h for h in candidate_hours if h not in used_range]

                remaining -= dur  # update for this task

                # Send invite with context for feedback
                link, event_id = send_invite_via_timely(
                    timely_gcal,
                    task.get("taskName", "Untitled"),
                    start_dt,
                    dur,
                    user_id,
                    task_id,
                    cat,  # task_type
                    max_off,  # hrs_until_due
                    offset_h,  # chosen_hour
                    1.0,  # default probability since vw_recommend doesn't return it
                )

                if link:
                    print(f"    📨 Created invite: {link}")
                    links.append(link)
                else:
                    print(f"    ❌ Failed to create invite")

                break  # stop after first accepted slice for this task

            # Update remaining hours in Firestore
            if remaining < float(task.get("taskDuration", 0)):
                print(f"  💾 Updating remaining hours in Firestore: {remaining:.1f}h")
                db.collection("UserTasks").document(user_id).update(
                    {f"tasks.{task_id}.remainingHours": remaining}
                )

        print("\n📅 Final Schedule:")
        print("=" * 50)
        for i, (task_id, summary, start_dt, dur) in enumerate(all_recs, 1):
            print(f"{i}. {summary}")
            print(f"   • Start: {start_dt.strftime('%Y-%m-%d %H:%M')}")
            print(f"   • Duration: {dur:.1f}h")
            print(f"   • Task ID: {task_id}")

        print(f"\n✨ Generated {len(links)} invite(s)")
        return jsonify({"links": links})

    except Exception as err:
        print("❌ Error in recommendation generation:", err)
        traceback.print_exc()
        return jsonify({"error": str(err)}), 500


# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Start calendar watch for feedback
    webhook_url = "https://your.ngrok.io/api/calendar-webhook"  # Replace with your actual webhook URL
    try:
        watch_resp = start_calendar_watch(get_timely_calendar_service(), webhook_url)
        print("✅ Calendar watch started:", watch_resp)
    except Exception as e:
        print("❌ Failed to start calendar watch:", str(e))
        traceback.print_exc()  # Add traceback for better error visibility

    app.run(port=8888)
