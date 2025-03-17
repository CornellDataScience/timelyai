import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from datetime import datetime

# Authenticate
cred = credentials.Certificate("timelyai-35463-firebase-adminsdk-fbsvc-0c08638adb.json")
app = firebase_admin.initialize_app(cred)

# Initialize client
db = firestore.client()

"""
TimelyAI Firestore Integration Module

This module provides functions to interact with Firestore for the TimelyAI project,
handling user preferences, goals, tasks, and schedule management.
"""

def initializeDoc(user_id):
    """
    Initialize a new user document in Firestore with default values.
    """
    doc_ref = db.collection("users").document(user_id)
    assert not doc_ref.get().exists, "user_id already exists"
    
    goals = {
        "Exercise": {"Run": 0, "Gym": 0},
        "Socialize": 0,
        "Sleep": 56,
        "Jobs": 0,
        "Hobbies": 0,
        "Other": {}
    }
    sleep_schedule = {"wakeTime": "08:00 AM", "bedTime": "11:00 PM"}
    user_pref = {"goals": goals, "sleep": sleep_schedule}
    
    data = {
        "userPref": user_pref,
        "Tasks": {},
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    doc_ref.set(data)
    return data

def getUserDocument(user_id):
    """Retrieve the entire user document."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def update_user_field(user_id, field, value):
    """Generic function to update a specific field in the user document."""
    doc_ref = db.collection("users").document(user_id)
    doc_ref.update({
        field: value,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })
    return True

def addTask(user_id, task_data):
    """Add a new task for the user."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None
    
    user_data = doc.to_dict()
    tasks = user_data.get("Tasks", {})
    task_id = f"task_{datetime.utcnow().timestamp()}"
    task_data["createdAt"] = firestore.SERVER_TIMESTAMP
    task_data["updatedAt"] = firestore.SERVER_TIMESTAMP
    tasks[task_id] = task_data
    update_user_field(user_id, "Tasks", tasks)
    return task_id

def modifyTask(user_id, task_id, updated_data):
    """Modify an existing task."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    
    user_data = doc.to_dict()
    tasks = user_data.get("Tasks", {})
    if task_id not in tasks:
        return False
    
    updated_data["updatedAt"] = firestore.SERVER_TIMESTAMP
    tasks[task_id].update(updated_data)
    update_user_field(user_id, "Tasks", tasks)
    return True

def deleteTask(user_id, task_id):
    """Delete a task."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    
    user_data = doc.to_dict()
    tasks = user_data.get("Tasks", {})
    if task_id in tasks:
        del tasks[task_id]
        update_user_field(user_id, "Tasks", tasks)
        return True
    return False

def updateGoals(user_id, goal_category, goal_name, duration):
    """Update user's goal duration."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    
    user_data = doc.to_dict()
    goals = user_data.get("userPref", {}).get("goals", {})
    if goal_category not in goals:
        return False
    
    if isinstance(goals[goal_category], dict):
        goals[goal_category][goal_name] = duration
    else:
        goals[goal_category] = {goal_name: duration}
    
    update_user_field(user_id, "userPref.goals", goals)
    return True
