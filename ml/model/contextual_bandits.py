import subprocess
import os
import json
import numpy as np
import pandas as pd
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Optional
from event_categories import (
    get_category_for_event_type,
    get_default_event_type_for_category,
    get_event_type_info,
)
from contextual_bandits_helpers import (
    TIME_SLOTS,
    format_vw_example,
    format_day_and_time,
    format_duration,
    is_time_blocked,
    get_blocked_reason,
    create_training_example,
    create_prediction_example,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
USER_DIR = os.path.join(os.path.dirname(BASE_DIR), "user")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(USER_DIR, exist_ok=True)

TRAIN_FILE = os.path.join(DATA_DIR, "train.vw")
TEST_FILE = os.path.join(DATA_DIR, "test.vw")
MODEL_FILE = os.path.join(USER_DIR, "time_recommendation.model")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "predictions.txt")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.vw")
ACTIONS_FILE = os.path.join(DATA_DIR, "actions.txt")

START_HOUR = 6
END_HOUR = 22
TIME_STEP = 0.5
RECOMMENDED_TIMES = {}
TASK_BUFFER = 1.0
EVENT_BUFFER = 1.5
BLOCKED_TIMES = {}
SCHEDULED_EVENTS = {}

# ************************* BACKEND-FACING FUNCTIONS **************************


def generate_recommendations(
    task_type: str,
    task_duration: float,
    hours_until_due: float,
    daily_free_time: float,
    day_of_week: Optional[int] = None,
    prefer_splitting: bool = False,
    long_task_threshold: float = 4.0,
) -> Union[Tuple[float, float, float], List[Tuple[float, float, float]]]:
    """
    Predict the best time(s) for a task, handling both short and long tasks.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        prefer_splitting: Whether to prefer splitting long tasks
        long_task_threshold: Duration threshold for considering a task "long"

    Returns:
        For short tasks: A tuple of (day_of_week, time_slot, duration)
        For long tasks with splitting: A list of tuples [(day_of_week, time_slot, duration), ...]
    """
    # If day_of_week is not provided, use the current day
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    # For short tasks, use the standard prediction
    if task_duration <= long_task_threshold or not prefer_splitting:
        day, time, duration = predict_best_time(
            task_type, task_duration, hours_until_due, daily_free_time, day_of_week
        )
        return (day, time, duration)

    # For long tasks that should be split
    num_sessions = int(np.ceil(task_duration / long_task_threshold))
    session_duration = task_duration / num_sessions
    recommendations = []

    # Calculate hours until due for each session
    hours_per_session = hours_until_due / num_sessions

    for i in range(num_sessions):
        # Get recommendation for this session
        day, time, _ = predict_best_time(
            task_type,
            session_duration,
            hours_per_session * (num_sessions - i),
            daily_free_time,
            day_of_week,
        )
        recommendations.append((day, time, session_duration))

        # Move to next day for next session
        day_of_week = (day_of_week + 1) % 7

    return recommendations


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
            if is_time_blocked(candidate_day, time_slot, BLOCKED_TIMES):
                blocked_reason = get_blocked_reason(
                    candidate_day, time_slot, BLOCKED_TIMES
                )
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


def record_binary_feedback(
    task_type: str,
    task_duration: float,
    hours_until_due: float,
    daily_free_time: float,
    chosen_time: float,
    day_of_week: int,
    was_accepted: bool,
    probability: Optional[float] = None,
) -> None:
    """
    Record binary feedback for a time recommendation.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        chosen_time: The time slot that was chosen
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        was_accepted: Whether the recommendation was accepted
        probability: The probability of the action (optional)
    """
    # Create training example with binary feedback
    example = create_training_example(
        task_type,
        task_duration,
        hours_until_due,
        daily_free_time,
        chosen_time,
        chosen_time,  # For binary feedback, we use the chosen time as the actual time
        day_of_week,
        probability,
    )

    # Cost is 0 if accepted, 1 if rejected
    cost = 0 if was_accepted else 1

    # Update the model with the feedback
    update_model(example, cost)


def update_model(example: str, cost: float):
    """
    Update the model with new feedback data.

    Args:
        example: The training example to add to the feedback file
        cost: The cost/reward for the action
    """
    # Append the example to the feedback file
    with open(FEEDBACK_FILE, "a") as f:
        f.write(f"{example}\n")

    # Check if we have enough feedback to update the model
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
        reason: Reason for blocking the time (e.g., "meeting", "appointment", "scheduled event")
    """
    global BLOCKED_TIMES

    # Find all time slots that overlap with the blocked period
    for time_slot in TIME_SLOTS:
        if start_time <= time_slot < end_time:
            BLOCKED_TIMES[(day_of_week, time_slot)] = reason

    print(
        f"🕒 Blocked time: {format_day_and_time(day_of_week, start_time)} to {format_day_and_time(day_of_week, end_time)} ({reason})"
    )


def clear_blocked_times():
    """Clear all blocked times."""
    global BLOCKED_TIMES
    BLOCKED_TIMES = {}
    print("🔄 Cleared all blocked times")


def clear_scheduled_events():
    """Clear all scheduled events."""
    global SCHEDULED_EVENTS
    SCHEDULED_EVENTS = {}
    print("🔄 Cleared all scheduled events")


def add_scheduled_event(day_of_week, start_time, end_time, event_name):
    """
    Add a scheduled event to the calendar.

    Args:
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        start_time: Start time in 24-hour format (e.g., 14.0 for 2:00 PM)
        end_time: End time in 24-hour format (e.g., 15.0 for 3:00 PM)
        event_name: Name of the scheduled event
    """
    global SCHEDULED_EVENTS, BLOCKED_TIMES

    # Add to scheduled events
    SCHEDULED_EVENTS[(day_of_week, start_time, end_time)] = event_name

    # Also block the time
    add_blocked_time(day_of_week, start_time, end_time, f"scheduled: {event_name}")

    # Add buffer after scheduled event
    buffer_end = min(end_time + EVENT_BUFFER, END_HOUR)
    add_blocked_time(day_of_week, end_time, buffer_end, f"event_buffer: {event_name}")

    print(
        f"📅 Added scheduled event: {event_name} on {format_day_and_time(day_of_week, start_time)} to {format_day_and_time(day_of_week, end_time)}"
    )


# ***************************** FOR DEMO + TESTING *****************************

if __name__ == "__main__":
    # Example usage
    train_model()

    # Reset recommended times
    reset_recommended_times()

    # Add some blocked times (example)
    add_scheduled_event(1, 9.0, 10.5, "Math Class")  # Tuesday 9:00 AM - 10:30 AM
    add_scheduled_event(1, 11.0, 12.5, "Science Class")  # Tuesday 11:00 AM - 12:30 PM
    add_scheduled_event(3, 14.0, 15.5, "History Class")  # Thursday 2:00 PM - 3:30 PM
    add_blocked_time(4, 15.0, 16.0, "Doctor Appointment")  # Friday 3:00 PM - 4:00 PM

    # Predict a time for a homework task
    result = generate_recommendations(
        task_type="hw", task_duration=2.0, hours_until_due=24, daily_free_time=6.0
    )

    # Handle both single recommendation and multiple recommendations
    if isinstance(result, tuple):
        day, predicted_time, duration = result
        print(
            f"Single recommendation: {format_day_and_time(day, predicted_time)} for {format_duration(duration)}"
        )
    else:
        print("Multiple recommendations:")
        for i, (day, time, duration) in enumerate(result, 1):
            print(
                f"  {i}. {format_day_and_time(day, time)} for {format_duration(duration)}"
            )

    # Example of a long task with splitting
    long_result = generate_recommendations(
        task_type="project",
        task_duration=8.0,
        hours_until_due=72,
        daily_free_time=6.0,
        prefer_splitting=True,
    )

    print("\nLong task recommendations:")
    for i, (day, time, duration) in enumerate(long_result, 1):
        print(
            f"  {i}. {format_day_and_time(day, time)} for {format_duration(duration)}"
        )
