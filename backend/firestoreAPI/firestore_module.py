import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from datetime import datetime
import pandas as pd
import os

# import datetime

"""
TimelyAI Firestore Integration Module

This module provides functions to interact with Firestore for the TimelyAI project,
handling user preferences, goals, tasks, and schedule management.
"""

def initializeDB():
    if not firebase_admin._apps:
        cred = credentials.Certificate(
            os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "firestore_credentials.json",
            )
        )
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
        "Other": {},
    }
    sleep_schedule = {"wakeTime": "08:00 AM", "bedTime": "11:00 PM"}
    data = {
        "goals": goals,
        "sleep_schedule": sleep_schedule,
    }

    doc_ref.set(data)
    return data


def loadUserTasks(db, user_id):
    """
    Initialize a new user subcollection in the collection "UserTasks".
    """
    doc_ref = db.collection("UserTasks").document(user_id)
    doc_ref.set({})


def getUserDocument(db, user_id):
    """Retrieve the entire user document."""
    doc_ref = db.collection("UserPreferences").document(user_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None


# TO BE UPDATED
def updateUserGoals(db, user_id, goal, value):
    """
    Generic function to update a goal field in the userPreferences document.

    goal = goal that you want to update
    value = value that you wish to assign to the field
    """

    doc_ref = db.collection("UserPreferences").document(user_id)
    doc_ref.update(
        {
            goal: value,
            # "updatedAt": firestore.SERVER_TIMESTAMP
        }
    )
    return True


# def updateUserSleep() {

# }


def addTask(db, user_id, taskName, taskDuration, taskCategory, taskDeadline):
    """
    Add a new task for the user and return the taskID generated for the task.

    db = initilized firestore database
    task_name = name of the task (String)
    task_duration = duration it takes to complete the task (int)
    task_deadline = datetime object formatted in str as '%d/%m/%y %H:%M:%S' (datetime)
    task_category = category of tasks assigned by users (str)
    """

    doc_ref = db.collection("UserTasks").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None

    # task_data["createdAt"] = firestore.SERVER_TIMESTAMP
    # task_data["updatedAt"] = firestore.SERVER_TIMESTAMP
    # Generate a unique task ID

    user_data = doc.to_dict()  # Convert document snapshot to dictionary
    existing_tasks = user_data.get(
        "tasks", {}
    )  # Get 'tasks' field or empty dict if it doesn't exist

    task_id = None
    first = True

    while task_id is None or task_id in existing_tasks:
        if first:
            first = False
        else:
            print("Task ID already exists, generating another.")
        task_id = db.collection("UserTasks").document().id  # This generates a random ID

    task_data = {
        "taskName": taskName,
        "taskDuration": taskDuration,
        "taskCategory": taskCategory,
        "taskDeadline": taskDeadline
    }
    # doc_ref.set({taskName: task_data})
    # Update the user document with the new task using the generated task_id
    doc_ref.update({f"tasks.{task_id}": task_data})
    return task_id


def updateTask(
    db, user_id, task_id, taskName, taskDuration, taskCategory, taskDeadline
):
    """Modify an existing task."""

    doc_ref = db.collection("UserTasks").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False

    task_data = {
        "taskName": taskName,
        "taskDuration": taskDuration,
        "taskCategory": taskCategory,
        "taskDeadline": taskDeadline
    }

    user_data = doc.to_dict()  # Convert document snapshot to dictionary
    existing_tasks = user_data.get(
        "tasks", {}
    )  # Get 'tasks' field or empty dict if it doesn't exist

    if task_id not in existing_tasks:
        print("Task ID doesn't exists.")
        return False
    else:
        doc_ref.update({f"tasks.{task_id}": task_data})
    return True


def deleteTask(db, user_id, task_id):
    """
    Delete a specific task for a user.

    Args:
        db: initialized firestore database
        user_id (str): ID of the user
        task_id (str): ID of the task to delete

    Returns:
        bool: True if successful, False if user not found or task doesn't exist
    """

    doc_ref = db.collection("UserTasks").document(user_id)
    doc = doc_ref.get()

    # Check if user exists
    if not doc.exists:
        return False

    # Get user data
    user_data = doc.to_dict()
    tasks = user_data.get("tasks", {})

    # Check if task exists
    if task_id not in tasks:
        return False

    # Delete the task using the FieldValue.delete() method
    doc_ref.update({f"tasks.{task_id}": firestore.DELETE_FIELD})

    return True

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
        if "event_id" in row:
            event_id = row["event_id"]
        else:
            # Generate a unique ID if event_id is not present
            event_id = user_doc_ref.collection("temp").document().id

        events_dict[event_id] = row_dict

    # Write the entire events dictionary to Firestore
    # print(f"Writing {len(events_dict)} events to Firestore document: {user_id}")

    user_doc_ref.set({"events": events_dict})
    print("Successfully wrote events dictionary to Firestore")


def TestRunCSV():
    db = initializeDB()
    csv_file_path = "example_calendar.csv"
    df = pd.read_csv(csv_file_path)

    # Set the name of the collection in Firestore
    collection_name = "UserCalendars"

    # Set the user ID to associate with these events
    user_id = "boss456@cornell.edu"  # Use the ID from your screenshot

    # Load the DataFrame and write to Firestore
    loadUserCalendarDataframe(db, df, collection_name, user_id)


def TestRunUserPref():
    db = initializeDB()
    loadBaseUserPreferences(db, "Boss456@gmail.com")


# TestRunUserPref()
db = initializeDB()
user_id = "TestALL2"
taskID = "6VSfb3LDldhurSLE4cQl"
deadline = datetime.strptime("31/01/22 23:59:59", "%d/%m/%y %H:%M:%S")
# loadUserTasks(db,user_id)
# loadBaseUserPreferences(db,user_id)
# addTask(db,user_id,"taskTwo",5,"Studying",deadline)
# updateTask(db,user_id,taskID,"taskTwoEdited",5,"Editing",deadline)
deleteTask(db, user_id, taskID)
