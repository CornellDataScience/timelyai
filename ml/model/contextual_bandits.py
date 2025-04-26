import subprocess
import os
import json
import numpy as np
from datetime import datetime, timedelta
from event_categories import (
    get_category_for_event_type,
    get_default_event_type_for_category,
    get_event_type_info,
)

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
USER_DIR = os.path.join(os.path.dirname(BASE_DIR), "user")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(USER_DIR, exist_ok=True)

TRAIN_FILE = os.path.join(DATA_DIR, "train.vw")
TEST_FILE = os.path.join(DATA_DIR, "test.vw")
MODEL_FILE = os.path.join(USER_DIR, "time_recommendation.model")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "predictions.txt")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.vw")
ACTIONS_FILE = os.path.join(DATA_DIR, "actions.txt")

# Time range for recommendations (in 24-hour format)
START_HOUR = 6  # 6 AM
END_HOUR = 22  # 10 PM
TIME_STEP = 0.5  # 30-minute intervals

# Define discrete time slots for the action space
TIME_SLOTS = [
    round(x, 1) for x in np.arange(START_HOUR, END_HOUR + TIME_STEP, TIME_STEP)
]

# Global variable to track recommended time slots
# Format: {(day_of_week, time_slot): task_type}
RECOMMENDED_TIMES = {}
# Buffer time between tasks (in hours)
TASK_BUFFER = 1.0  # 1 hour buffer between tasks
# Buffer time after classes (in hours)
CLASS_BUFFER = 1.5  # 1.5 hour buffer after classes

# Global variable to track blocked times
# Format: {(day_of_week, time_slot): reason}
BLOCKED_TIMES = {}

# Global variable to track class schedules
# Format: {(day_of_week, start_time, end_time): class_name}
CLASS_SCHEDULE = {}


def generate_time_slots():
    """Generate time slots for recommendations."""
    return TIME_SLOTS


def format_vw_example(features, action=None, cost=None, probability=None):
    """
    Format an example for VW contextual bandits.

    Args:
        features: Dictionary of feature names and values
        action: The time slot chosen (if None, this is a prediction example)
        cost: The cost/reward for the action (if None, this is a prediction example)
        probability: The probability of the action (if None, this is a prediction example)

    Returns:
        A string formatted for VW
    """
    # Format features
    feature_str = " ".join([f"{k}:{v}" for k, v in features.items()])

    # If this is a training example with feedback
    if action is not None and cost is not None:
        if probability is not None:
            return f"{action}:{cost}:{probability} | {feature_str}"
        else:
            return f"{action}:{cost} | {feature_str}"

    # If this is a prediction example
    return f"| {feature_str}"


def create_training_example(
    task_type,
    task_duration,
    hours_until_due,
    daily_free_time,
    chosen_time,
    actual_completion_time,
    day_of_week=None,
    probability=None,
):
    """
    Create a training example with feedback.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        chosen_time: The time slot that was chosen
        actual_completion_time: The actual time when the task was completed
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        probability: The probability of the action (optional)

    Returns:
        A formatted VW example
    """
    # Calculate cost based on how well the recommendation worked
    # Lower cost is better (0 is perfect, higher values indicate worse performance)
    time_diff = abs(chosen_time - actual_completion_time)
    cost = time_diff / 24.0  # Normalize to [0,1] range

    # Find the closest discrete time slot
    chosen_slot = min(TIME_SLOTS, key=lambda x: abs(x - chosen_time))
    slot_index = TIME_SLOTS.index(chosen_slot)

    # If day_of_week is not provided, use the current day
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    # Get category information for the task type
    category = get_category_for_event_type(task_type)
    category_feature = (
        f"category_{category.lower().replace(' & ', '_').replace(' ', '_')}"
        if category
        else "category_unknown"
    )

    features = {
        "event_type": task_type,
        category_feature: 1,  # Add category as a feature
        "task_duration": task_duration,
        "hours_until_due": hours_until_due,
        "daily_free_time": daily_free_time,
        "day_of_week": day_of_week,  # 0=Monday, 6=Sunday
        "is_weekend": 1 if day_of_week >= 5 else 0,
        "time_of_day": datetime.now().hour + datetime.now().minute / 60.0,
    }

    return format_vw_example(features, slot_index, cost, probability)


def create_prediction_example(
    task_type, task_duration, hours_until_due, daily_free_time, day_of_week=None
):
    """
    Create a prediction example.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        day_of_week: Day of the week (0=Monday, 6=Sunday)

    Returns:
        A formatted VW example
    """
    # If day_of_week is not provided, use the current day
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    # Get category information for the task type
    category = get_category_for_event_type(task_type)
    category_feature = (
        f"category_{category.lower().replace(' & ', '_').replace(' ', '_')}"
        if category
        else "category_unknown"
    )

    features = {
        "event_type": task_type,
        category_feature: 1,  # Add category as a feature
        "task_duration": task_duration,
        "hours_until_due": hours_until_due,
        "daily_free_time": daily_free_time,
        "day_of_week": day_of_week,  # 0=Monday, 6=Sunday
        "is_weekend": 1 if day_of_week >= 5 else 0,
        "time_of_day": datetime.now().hour + datetime.now().minute / 60.0,
    }

    return format_vw_example(features)


def train_model():
    """Train the contextual bandits model."""
    print("🚂 Training time recommendation model...")

    # Create a temporary file with the action space
    with open(ACTIONS_FILE, "w") as f:
        for i, time in enumerate(TIME_SLOTS):
            f.write(f"{i}:{time}\n")

    cmd = [
        "vw",
        "--cb_explore",
        str(len(TIME_SLOTS)),  # Number of actions
        "-d",
        TRAIN_FILE,
        "-f",
        MODEL_FILE,
        "--quiet",
    ]

    subprocess.run(cmd, check=True)
    print("✅ Model trained and saved to:", MODEL_FILE)


def reset_recommended_times():
    """Reset the list of recommended times."""
    global RECOMMENDED_TIMES
    RECOMMENDED_TIMES = {}
    print("🔄 Reset recommended times")


def add_blocked_time(day_of_week, start_time, end_time, reason="blocked"):
    """
    Add a blocked time period to the calendar.

    Args:
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        start_time: Start time in 24-hour format (e.g., 14.0 for 2:00 PM)
        end_time: End time in 24-hour format (e.g., 15.0 for 3:00 PM)
        reason: Reason for blocking the time (e.g., "class", "meeting", "appointment")
    """
    global BLOCKED_TIMES

    # Find all time slots that overlap with the blocked period
    for time_slot in TIME_SLOTS:
        if start_time <= time_slot < end_time:
            BLOCKED_TIMES[(day_of_week, time_slot)] = reason

    print(
        f"🕒 Blocked time: {format_day_and_time(day_of_week, start_time)} to {format_day_and_time(day_of_week, end_time)} ({reason})"
    )


def add_class_schedule(day_of_week, start_time, end_time, class_name):
    """
    Add a class to the schedule.

    Args:
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        start_time: Start time in 24-hour format (e.g., 14.0 for 2:00 PM)
        end_time: End time in 24-hour format (e.g., 15.0 for 3:00 PM)
        class_name: Name of the class
    """
    global CLASS_SCHEDULE, BLOCKED_TIMES

    # Add to class schedule
    CLASS_SCHEDULE[(day_of_week, start_time, end_time)] = class_name

    # Also block the time
    add_blocked_time(day_of_week, start_time, end_time, f"class: {class_name}")

    # Add buffer after class
    buffer_end = min(end_time + CLASS_BUFFER, END_HOUR)
    add_blocked_time(day_of_week, end_time, buffer_end, f"class_buffer: {class_name}")

    print(
        f"📚 Added class: {class_name} on {format_day_and_time(day_of_week, start_time)} to {format_day_and_time(day_of_week, end_time)}"
    )


def clear_blocked_times():
    """Clear all blocked times."""
    global BLOCKED_TIMES
    BLOCKED_TIMES = {}
    print("🔄 Cleared all blocked times")


def clear_class_schedule():
    """Clear all class schedules."""
    global CLASS_SCHEDULE
    CLASS_SCHEDULE = {}
    print("🔄 Cleared all class schedules")


def is_time_blocked(day_of_week, time_slot):
    """
    Check if a time slot is blocked.

    Args:
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        time_slot: Time slot in 24-hour format (e.g., 14.0 for 2:00 PM)

    Returns:
        True if the time slot is blocked, False otherwise
    """
    return (day_of_week, time_slot) in BLOCKED_TIMES


def get_blocked_reason(day_of_week, time_slot):
    """
    Get the reason why a time slot is blocked.

    Args:
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        time_slot: Time slot in 24-hour format (e.g., 14.0 for 2:00 PM)

    Returns:
        The reason for blocking the time slot, or None if not blocked
    """
    return BLOCKED_TIMES.get((day_of_week, time_slot))


def format_day_and_time(day_of_week, time_slot):
    """
    Format a day and time slot as a human-readable string.

    Args:
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        time_slot: Time slot in 24-hour format (e.g., 14.0 for 2:00 PM)

    Returns:
        A formatted string (e.g., "Monday at 14:00")
    """
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    day_str = day_names[day_of_week]

    hours = int(time_slot)
    minutes = int((time_slot - hours) * 60)
    time_str = f"{hours:02d}:{minutes:02d}"

    return f"{day_str} at {time_str}"


def predict_best_time(
    task_type, task_duration, hours_until_due, daily_free_time, day_of_week=None
):
    """
    Predict the best time to work on a task.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        day_of_week: Day of the week (0=Monday, 6=Sunday)

    Returns:
        A tuple of (day_of_week, recommended_time, duration)
    """
    # If day_of_week is not provided, use the current day
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    # Calculate the appropriate day range based on hours until due
    days_until_due = hours_until_due / 24.0
    max_days_ahead = min(7, max(1, int(days_until_due)))

    # Get category information for the task type
    category = get_category_for_event_type(task_type)
    event_info = get_event_type_info(task_type)

    # If we have event info, use it to adjust parameters
    if event_info:
        # Use typical duration if not provided
        if task_duration is None or task_duration <= 0:
            task_duration = event_info["typical_duration"]

        # Adjust urgency based on category
        if event_info["typical_urgency"] == "high":
            # For high urgency tasks, prioritize days closer to due date
            max_days_ahead = min(max_days_ahead, 3)
        elif event_info["typical_urgency"] == "low":
            # For low urgency tasks, we can spread them out more
            max_days_ahead = min(max_days_ahead, 5)

    # Create a prediction example
    example = create_prediction_example(
        task_type, task_duration, hours_until_due, daily_free_time, day_of_week
    )

    # Write the example to the test file
    with open(TEST_FILE, "w") as f:
        f.write(example)

    # Run prediction
    print("🔎 Predicting best time...")
    cmd = [
        "vw",
        "--cb_explore",
        str(len(TIME_SLOTS)),  # Number of actions
        "-t",  # test mode
        "-i",
        MODEL_FILE,
        "-d",
        TEST_FILE,
        "-p",
        PREDICTIONS_FILE,
        "--quiet",
    ]

    subprocess.run(cmd, check=True)

    # Read the prediction
    with open(PREDICTIONS_FILE, "r") as f:
        prediction_str = f.read().strip()

    # Parse the prediction string (format: "action:probability,action:probability,...")
    action_probs = {}
    for pair in prediction_str.split(","):
        if ":" in pair:
            action, prob = pair.split(":")
            action_probs[int(action)] = float(prob)

    # Sort actions by probability (highest first)
    sorted_actions = sorted(action_probs.items(), key=lambda x: x[1], reverse=True)

    # Determine if this is a relaxation task (which can be scheduled closer to other tasks)
    is_relaxation = task_type.lower() in [
        "relaxation",
        "relax",
        "break",
        "rest",
        "sleep",
        "nap",
    ]

    # Find the first action that hasn't been recommended yet and respects the buffer
    predicted_time = None
    predicted_day = day_of_week

    # Determine the priority of days based on due date and task duration
    # For urgent tasks (due soon), prioritize days closer to due date
    # For less urgent tasks, distribute more evenly
    if days_until_due <= 1:
        # Very urgent (due today or tomorrow) - prioritize today and tomorrow
        day_priorities = [day_of_week, (day_of_week + 1) % 7]
    elif days_until_due <= 3:
        # Urgent (due in 2-3 days) - prioritize next 3 days
        day_priorities = [(day_of_week + i) % 7 for i in range(3)]
    else:
        # Less urgent - distribute across available days
        # Calculate how many days we can spread across
        available_days = min(
            max_days_ahead, 5
        )  # Cap at 5 days to leave some flexibility
        day_priorities = [(day_of_week + i) % 7 for i in range(available_days)]

        # For tasks with plenty of time, try to distribute evenly
        if days_until_due > 7:
            # Shuffle the days to avoid always starting with the same day
            import random

            random.shuffle(day_priorities)

    # Try each day in order of priority
    for candidate_day in day_priorities:
        for action_index, _ in sorted_actions:
            time_slot = TIME_SLOTS[action_index]

            # Check if this time slot is already recommended for this day
            if (candidate_day, time_slot) in RECOMMENDED_TIMES:
                continue

            # Check if this time slot is blocked
            if is_time_blocked(candidate_day, time_slot):
                blocked_reason = get_blocked_reason(candidate_day, time_slot)
                print(
                    f"⚠️ Time slot {format_day_and_time(candidate_day, time_slot)} is blocked: {blocked_reason}"
                )
                continue

            # For non-relaxation tasks, check if this time slot is too close to other tasks
            if not is_relaxation:
                # Check if this time slot is too close to any other recommended time on the same day
                too_close = False
                for (rec_day, rec_time), _ in RECOMMENDED_TIMES.items():
                    if rec_day == candidate_day:
                        # Calculate the time difference in hours
                        time_diff = abs(time_slot - rec_time)
                        if time_diff < TASK_BUFFER:
                            too_close = True
                            break

                if too_close:
                    continue

            # This time slot is valid
            predicted_time = time_slot
            predicted_day = candidate_day
            break

        if predicted_time is not None:
            break

    # If no suitable time slot found, find the one with the lowest probability
    if predicted_time is None:
        # Get the action with the lowest probability
        action_index = min(action_probs.items(), key=lambda x: x[1])[0]
        predicted_time = TIME_SLOTS[action_index]
        print("⚠️ No suitable time slot found. Choosing the least likely time.")

    # Add the recommended time to the set of recommended times
    RECOMMENDED_TIMES[(predicted_day, predicted_time)] = task_type

    # Format the time for display
    hours = int(predicted_time)
    minutes = int((predicted_time - hours) * 60)
    time_str = f"{hours:02d}:{minutes:02d}"

    # Format the day for display
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    day_str = day_names[predicted_day]

    # Format duration for display
    duration_str = format_duration(task_duration)

    print(f"📅 Recommended time: {day_str} at {time_str} for {duration_str}")
    return (predicted_day, predicted_time, task_duration)


def format_duration(duration_hours):
    """Format a duration in hours as a human-readable string."""
    if duration_hours < 1:
        minutes = int(duration_hours * 60)
        return f"{minutes} minutes"
    elif duration_hours == 1:
        return "1 hour"
    else:
        hours = int(duration_hours)
        minutes = int((duration_hours - hours) * 60)
        if minutes == 0:
            return f"{hours} hours"
        else:
            return f"{hours} hours and {minutes} minutes"


def predict_best_times_for_long_task(
    task_type,
    task_duration,
    hours_until_due,
    daily_free_time,
    day_of_week=None,
    prefer_splitting=False,
):
    """
    Predict multiple best times for a long task, splitting it across days.
    The splitting behavior can be controlled by the prefer_splitting parameter.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        prefer_splitting: Whether to prefer splitting the task (True) or completing it in one go (False)

    Returns:
        A list of tuples (day_of_week, recommended_time, duration)
    """
    # For tasks longer than 3 hours, consider splitting them into multiple sessions
    # if prefer_splitting is True
    if task_duration <= 3 or not prefer_splitting:
        day, time, duration = predict_best_time(
            task_type, task_duration, hours_until_due, daily_free_time, day_of_week
        )
        return [(day, time, duration)]

    # Calculate how many sessions to split the task into
    # Aim for sessions of 1-3 hours
    num_sessions = max(2, min(5, int(task_duration / 2)))
    session_duration = task_duration / num_sessions

    # Calculate days until due
    days_until_due = hours_until_due / 24.0

    # Ensure we have enough days to spread the sessions
    available_days = min(int(days_until_due), 7)
    if available_days < num_sessions:
        # If we don't have enough days, reduce the number of sessions
        num_sessions = available_days
        session_duration = task_duration / num_sessions

    # Get recommendations for each session
    recommendations = []
    for i in range(num_sessions):
        # For each session, we want to spread them across available days
        # Calculate the day offset based on the session index
        day_offset = i % available_days

        # Get the day for this session
        session_day = (
            (day_of_week + day_offset) % 7
            if day_of_week is not None
            else (datetime.now().weekday() + day_offset) % 7
        )

        # Get a time recommendation for this session
        day, time, duration = predict_best_time(
            task_type,
            session_duration,
            hours_until_due - (i * 24),  # Adjust hours until due for later sessions
            daily_free_time,
            session_day,
        )

        recommendations.append((day, time, duration))

    return recommendations


def record_feedback(
    task_type,
    task_duration,
    hours_until_due,
    daily_free_time,
    chosen_time,
    actual_completion_time,
    day_of_week=None,
    probability=None,
):
    """
    Record feedback for a recommendation.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        chosen_time: The time slot that was chosen
        actual_completion_time: The actual time when the task was completed
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        probability: The probability of the action (optional)
    """
    # Create a feedback example
    example = create_training_example(
        task_type,
        task_duration,
        hours_until_due,
        daily_free_time,
        chosen_time,
        actual_completion_time,
        day_of_week,
        probability,
    )

    # Append the example to the feedback file
    with open(FEEDBACK_FILE, "a") as f:
        f.write(example + "\n")

    print("✅ Feedback recorded")


def update_model():
    """Update the model with new feedback data."""
    if not os.path.exists(FEEDBACK_FILE) or os.path.getsize(FEEDBACK_FILE) == 0:
        print("⚠️ No feedback data to update the model")
        return

    print("🔄 Updating model with new feedback...")

    cmd = [
        "vw",
        "--cb_explore",
        str(len(TIME_SLOTS)),  # Number of actions
        "-d",
        FEEDBACK_FILE,
        "-i",
        MODEL_FILE,
        "-f",
        MODEL_FILE,
        "--quiet",
    ]

    subprocess.run(cmd, check=True)
    print("✅ Model updated with new feedback")

    # Clear the feedback file after updating
    with open(FEEDBACK_FILE, "w") as f:
        f.write("")


def record_binary_feedback(
    task_type,
    task_duration,
    hours_until_due,
    daily_free_time,
    chosen_time,
    day_of_week,
    was_accepted,
    probability=None,
):
    """
    Record binary feedback (accept/reject) for a time recommendation.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        chosen_time: The time slot that was chosen
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        was_accepted: Boolean indicating if the recommendation was accepted
        probability: The probability of the action (optional)
    """
    # Convert the chosen time to an action index
    chosen_slot = min(TIME_SLOTS, key=lambda x: abs(x - chosen_time))
    slot_index = TIME_SLOTS.index(chosen_slot)

    # Calculate cost: 0 for accepted, 1 for rejected
    cost = 0.0 if was_accepted else 1.0

    # Get category information for the task type
    category = get_category_for_event_type(task_type)
    category_feature = (
        f"category_{category.lower().replace(' & ', '_').replace(' ', '_')}"
        if category
        else "category_unknown"
    )

    # Create features
    features = {
        "event_type": task_type,
        category_feature: 1,  # Add category as a feature
        "task_duration": task_duration,
        "hours_until_due": hours_until_due,
        "daily_free_time": daily_free_time,
        "day_of_week": day_of_week,  # 0=Monday, 6=Sunday
        "is_weekend": 1 if day_of_week >= 5 else 0,
        "time_of_day": datetime.now().hour + datetime.now().minute / 60.0,
    }

    # Format the example
    example = format_vw_example(features, slot_index, cost, probability)

    # Append the example to the feedback file
    with open(FEEDBACK_FILE, "a") as f:
        f.write(example + "\n")

    print("✅ Binary feedback recorded")


def get_alternative_recommendation(
    task_type,
    task_duration,
    hours_until_due,
    daily_free_time,
    rejected_time,
    day_of_week=None,
):
    """
    Get an alternative time recommendation when a user rejects a suggestion.
    This function tries to find a time slot that is different from the rejected one.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        rejected_time: The time slot that was rejected
        day_of_week: Day of the week (0=Monday, 6=Sunday)

    Returns:
        A tuple of (day_of_week, recommended_time, duration)
    """
    # If day_of_week is not provided, use the current day
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    # Create a prediction example
    example = create_prediction_example(
        task_type, task_duration, hours_until_due, daily_free_time, day_of_week
    )

    # Write the example to the test file
    with open(TEST_FILE, "w") as f:
        f.write(example)

    # Run prediction
    print("🔎 Predicting alternative time...")
    cmd = [
        "vw",
        "--cb_explore",
        str(len(TIME_SLOTS)),  # Number of actions
        "-t",  # test mode
        "-i",
        MODEL_FILE,
        "-d",
        TEST_FILE,
        "-p",
        PREDICTIONS_FILE,
        "--quiet",
    ]

    subprocess.run(cmd, check=True)

    # Read the prediction
    with open(PREDICTIONS_FILE, "r") as f:
        prediction_str = f.read().strip()

    # Parse the prediction string (format: "action:probability,action:probability,...")
    action_probs = {}
    for pair in prediction_str.split(","):
        if ":" in pair:
            action, prob = pair.split(":")
            action_probs[int(action)] = float(prob)

    # Sort actions by probability (highest first)
    sorted_actions = sorted(action_probs.items(), key=lambda x: x[1], reverse=True)

    # Determine if this is a relaxation task (which can be scheduled closer to other tasks)
    is_relaxation = task_type.lower() in ["relaxation", "relax", "break", "rest"]

    # Find the first action that hasn't been recommended yet, is different from the rejected time,
    # and respects the buffer
    predicted_time = None
    predicted_day = day_of_week

    # Calculate the appropriate day range based on hours until due
    days_until_due = hours_until_due / 24.0
    max_days_ahead = min(7, max(1, int(days_until_due)))

    # Determine the priority of days based on due date and task duration
    if days_until_due <= 1:
        # Very urgent (due today or tomorrow) - prioritize today and tomorrow
        day_priorities = [day_of_week, (day_of_week + 1) % 7]
    elif days_until_due <= 3:
        # Urgent (due in 2-3 days) - prioritize next 3 days
        day_priorities = [(day_of_week + i) % 7 for i in range(3)]
    else:
        # Less urgent - distribute across available days
        available_days = min(
            max_days_ahead, 5
        )  # Cap at 5 days to leave some flexibility
        day_priorities = [(day_of_week + i) % 7 for i in range(available_days)]

        # For tasks with plenty of time, try to distribute evenly
        if days_until_due > 7:
            # Shuffle the days to avoid always starting with the same day
            import random

            random.shuffle(day_priorities)

    # Try each day in order of priority
    for candidate_day in day_priorities:
        for action_index, _ in sorted_actions:
            time_slot = TIME_SLOTS[action_index]

            # Skip if this is the rejected time slot on the same day
            if candidate_day == day_of_week and abs(time_slot - rejected_time) < 0.1:
                continue

            # Check if this time slot is already recommended for this day
            if (candidate_day, time_slot) in RECOMMENDED_TIMES:
                continue

            # Check if this time slot is blocked
            if is_time_blocked(candidate_day, time_slot):
                blocked_reason = get_blocked_reason(candidate_day, time_slot)
                print(
                    f"⚠️ Time slot {format_day_and_time(candidate_day, time_slot)} is blocked: {blocked_reason}"
                )
                continue

            # For non-relaxation tasks, check if this time slot is too close to other tasks
            if not is_relaxation:
                # Check if this time slot is too close to any other recommended time on the same day
                too_close = False
                for (rec_day, rec_time), _ in RECOMMENDED_TIMES.items():
                    if rec_day == candidate_day:
                        # Calculate the time difference in hours
                        time_diff = abs(time_slot - rec_time)
                        if time_diff < TASK_BUFFER:
                            too_close = True
                            break

                if too_close:
                    continue

            # This time slot is valid
            predicted_time = time_slot
            predicted_day = candidate_day
            break

        if predicted_time is not None:
            break

    # If no suitable time slot found, find one that's different from the rejected time
    if predicted_time is None:
        # Try to find a time slot that's at least 2 hours different from the rejected time
        for action_index, _ in sorted_actions:
            time_slot = TIME_SLOTS[action_index]
            if abs(time_slot - rejected_time) >= 2.0:
                predicted_time = time_slot
                predicted_day = day_of_week
                break

        # If still no suitable time slot found, use the one with the lowest probability
        if predicted_time is None:
            # Get the action with the lowest probability
            action_index = min(action_probs.items(), key=lambda x: x[1])[0]
            predicted_time = TIME_SLOTS[action_index]
            print(
                "⚠️ No suitable alternative time slot found. Choosing the least likely time."
            )

    # Add the recommended time to the set of recommended times
    RECOMMENDED_TIMES[(predicted_day, predicted_time)] = task_type

    # Format the time for display
    hours = int(predicted_time)
    minutes = int((predicted_time - hours) * 60)
    time_str = f"{hours:02d}:{minutes:02d}"

    # Format the day for display
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    day_str = day_names[predicted_day]

    # Format duration for display
    duration_str = format_duration(task_duration)

    print(f"📅 Alternative recommendation: {day_str} at {time_str} for {duration_str}")
    return (predicted_day, predicted_time, task_duration)


if __name__ == "__main__":
    # Example usage
    train_model()

    # Reset recommended times
    reset_recommended_times()

    # Add some blocked times (example)
    add_class_schedule(1, 9.0, 10.5, "Math Class")  # Tuesday 9:00 AM - 10:30 AM
    add_class_schedule(1, 11.0, 12.5, "Science Class")  # Tuesday 11:00 AM - 12:30 PM
    add_class_schedule(3, 14.0, 15.5, "History Class")  # Thursday 2:00 PM - 3:30 PM
    add_blocked_time(4, 15.0, 16.0, "Doctor Appointment")  # Friday 3:00 PM - 4:00 PM

    # Predict a time for a homework task
    day, predicted_time, duration = predict_best_time(
        task_type="hw", task_duration=2.0, hours_until_due=24, daily_free_time=6.0
    )

    # Record feedback (this would be done after the user completes the task)
    # record_feedback(
    #     task_type="hw",
    #     task_duration=2.0,
    #     hours_until_due=24,
    #     daily_free_time=6.0,
    #     chosen_time=predicted_time,
    #     day_of_week=day,
    #     actual_completion_time=14.5  # User actually completed at 2:30 PM
    # )

    # Update the model with new feedback
    # update_model()
