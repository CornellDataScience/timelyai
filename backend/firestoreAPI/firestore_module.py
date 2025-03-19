import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from datetime import datetime
import pandas as pd
import os



"""
TimelyAI Firestore Integration Module

This module provides functions to interact with Firestore for the TimelyAI project,
handling user preferences, goals, tasks, and schedule management.
"""

def initializeDB():
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "firestore_credentials.json"))
        firebase_admin.initialize_app(cred)
    
    # Get a reference to the Firestore database
    return firestore.client()

def loadBaseUserPreferences(db, user_id):
    """
    Initialize a new user document in Firestore with default values.
    """
    doc_ref = db.collection("UserPreferences").document(user_id)
    
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
    }

    doc_ref.set(data)
    return data

def getUserDocument(db, user_id):
    """Retrieve the entire user document."""
    doc_ref = db.collection("UserPreferences").document(user_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def update_user_field(db, user_id, field, value):
    """Generic function to update a specific field in the user document."""
    doc_ref = db.collection("UserPreferences").document(user_id)
    doc_ref.update({
        field: value,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })
    return True

def addTask(db, user_id, task_data):
    """Add a new task for the user."""
    doc_ref = db.collection("UserPreferences").document(user_id)
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

def modifyTask(db, user_id, task_id, updated_data):
    """Modify an existing task."""
    doc_ref = db.collection("UserPreferences").document(user_id)
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

def deleteTask(db, user_id, task_id):
    """Delete a task."""
    doc_ref = db.collection("UserPreferences").document(user_id)
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

def updateGoals(db, user_id, goal_category, goal_name, duration):
    """Update user's goal duration."""
    doc_ref = db.collection("UserPreferences").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    
    user_data = doc.to_dict()
    goals = user_data.get("UserPreferences", {}).get("goals", {})
    if goal_category not in goals:
        return False
    
    if isinstance(goals[goal_category], dict):
        goals[goal_category][goal_name] = duration
    else:
        goals[goal_category] = {goal_name: duration}
    
    update_user_field(user_id, "UserPreferences.goals", goals)
    return True

def loadUserCalendarDataframe(db, df, collection_name, user_id):
    """
    Load data from a pandas DataFrame and write it to Firestore
    mapping all events to a single user ID
    
    Args:
        df: pandas DataFrame containing calendar events
        collection_name: Name of the Firestore collection to write to
        user_id: ID of the user to associate with all events
    """
    # Get a reference to the document that will store all events
    user_doc_ref = db.collection(collection_name).document(user_id)
    
    # Create a dictionary of all events with event_id as key
    events_dict = {}
    for _, row in df.iterrows():
        # Convert row to dictionary and handle NaN values
        row_dict = row.to_dict()
        for key, value in row_dict.items():
            if pd.isna(value):
                row_dict[key] = None
        
        # Use event_id as key in the events dictionary
        if 'event_id' in row:
            event_id = row['event_id']
        else:
            # Generate a unique ID if event_id is not present
            event_id = user_doc_ref.collection('temp').document().id
        
        events_dict[event_id] = row_dict
    
    # Write the entire events dictionary to Firestore
    # print(f"Writing {len(events_dict)} events to Firestore document: {user_id}")

    user_doc_ref.set({"events": events_dict})
    print("Successfully wrote events dictionary to Firestore")


db = initializeDB()
csv_file_path = "example_calendar.csv"
df = pd.read_csv(csv_file_path)

# Set the name of the collection in Firestore
collection_name = "UserCalendars"

# Set the user ID to associate with these events
user_id = "boss50@cornell.edu"  # Use the ID from your screenshot

# Load the DataFrame and write to Firestore
loadUserCalendarDataframe(db, df, collection_name, user_id)

