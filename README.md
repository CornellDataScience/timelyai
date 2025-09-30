# TimelyAI

## Purpose

TimelyAI is a web application that connects to Google Calendar to turn goals and constraints into a realistic, time‑boxed weekly plan. It schedules focused work blocks, respects quiet hours and existing events, and keeps your calendar as the single source of truth.

## Implementation

### Backend

* Python API for scheduling and calendar orchestration
* Google OAuth2 + Calendar API integration (read busy times; create/update events)
* Scheduling engine that packs tasks into feasible windows with buffers and conflict handling
* Policy layer for quiet hours, no‑meeting blocks, and location/commute considerations

### Frontend

* Web UI for task intake, constraint editing, and plan review (accept/undo changes)
* Explanations for why a block was placed (deadline, priority, availability)

### ML

* **Duration estimation:** Uses natural language descriptors of tasks and past completion history to predict how long a task will take.
* **Priority ranking:** Applies multi‑factor scoring (deadlines, importance weights, dependencies) to order tasks for scheduling.
* **Preference modeling:** Captures user productivity patterns (morning vs evening focus, study vs gym blocks) to place tasks in optimal times.
* **Conflict resolution:** Suggests alternative placements and quantifies trade‑offs when tasks cannot fit within constraints.

## Local Setup

### 1) Clone the repository

```bash
git clone https://github.com/CornellDataScience/timelyai.git
cd timelyai
```

### 2) Configure environment

Create a `.env` (and/or `backend/.env`) with the required values:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:PORT/oauth/callback

# App
APP_BASE_URL=http://localhost:PORT
SESSION_SECRET=...

# Optional
OPENAI_API_KEY=...
DATABASE_URL=postgresql://...
```

### 3) Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # starts the API server
```

### 4) Frontend

```bash
cd ../frontend
npm install
npm run dev   # starts the web client
```

### 5) Link Google Calendar

Open the app in your browser, sign in, and complete the OAuth flow to grant Calendar access. Generate a draft plan and sync it to your calendar.

---

## Project Structure

```
backend/   # Python API, scheduler core, calendar integrations
frontend/  # Web client (planner UI, OAuth handoff)
ml/        # Duration/priority models, preference learning, conflict handling
```
