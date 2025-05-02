import subprocess
import os
import json
import numpy as np
import pandas as pd
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Optional
from .event_categories import (
    get_category_for_event_type,
    get_default_event_type_for_category,
    get_event_type_info,
)
from .contextual_bandits_helpers import (
    TIME_SLOTS,
    format_vw_example,
    format_day_and_time,
    format_duration,
    is_time_blocked,
    get_blocked_reason,
    create_training_example,
    create_prediction_example,
)
import math

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
    task_type,
    task_duration,
    hours_until_due,
    daily_free_time=4.0,
    prefer_splitting=False,
    context_tasks=None,
    day_of_week=None,
):
    # Clear any existing blocked times
    blocked_times = []

    # Add context tasks to blocked times
    if context_tasks:
        for task in context_tasks:
            if task.get("category") == "blocked":
                start_time = task.get("start_time", 0)
                duration = task.get("duration", 0)
                blocked_times.append((start_time, start_time + duration))

    # Block time slots based on due dates
    if hours_until_due > 0:
        # Block the last 2 hours before due date
        blocked_times.append((hours_until_due - 2, hours_until_due))

    # Sort blocked times for easier processing
    blocked_times.sort()

    # Generate time slots
    if prefer_splitting and task_duration > 2.0:
        # Split into multiple sessions
        num_sessions = math.ceil(task_duration / 2.0)
        session_duration = task_duration / num_sessions
        recommendations = []

        for i in range(num_sessions):
            # Try to find a non-blocked time slot
            start_time = find_available_time_slot(
                session_duration, blocked_times, hours_until_due, day_of_week
            )
            if start_time is not None:
                recommendations.append((0, start_time, session_duration))
                # Add this slot to blocked times
                blocked_times.append((start_time, start_time + session_duration))
                blocked_times.sort()

        return recommendations if recommendations else None
    else:
        # Single session
        start_time = find_available_time_slot(
            task_duration, blocked_times, hours_until_due, day_of_week
        )
        if start_time is not None:
            return (0, start_time, task_duration)
        return None


def find_available_time_slot(
    duration, blocked_times, hours_until_due, day_of_week=None
):
    # If no day specified, use current day
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    # Calculate available hours for the day
    day_start = day_of_week * 24
    day_end = (day_of_week + 1) * 24

    # Find gaps between blocked times
    available_slots = []
    current_time = day_start

    for start, end in blocked_times:
        if start > current_time:
            available_slots.append((current_time, start))
        current_time = max(current_time, end)

    # Add the remaining time until due date
    if current_time < hours_until_due:
        available_slots.append((current_time, min(day_end, hours_until_due)))

    # Find the first slot that can fit the duration
    for start, end in available_slots:
        if end - start >= duration:
            return start

    return None


def predict_best_time(
    task_type, task_duration, hours_until_due, daily_free_time, day_of_week=None
):
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    days_until_due = hours_until_due / 24.0
    max_days_ahead = min(7, max(1, int(days_until_due)))

    category = get_category_for_event_type(task_type)
    event_info = get_event_type_info(task_type)

    if event_info:
        if task_duration is None or task_duration <= 0:
            task_duration = event_info["typical_duration"]

        if event_info["typical_urgency"] == "high":
            max_days_ahead = min(max_days_ahead, 3)
        elif event_info["typical_urgency"] == "low":
            max_days_ahead = min(max_days_ahead, 5)

    example = create_prediction_example(
        task_type, task_duration, hours_until_due, daily_free_time, day_of_week
    )

    with open(TEST_FILE, "w") as f:
        f.write(example)

    cmd = [
        "vw",
        "--cb_explore",
        str(len(TIME_SLOTS)),
        "-t",
        "-i",
        MODEL_FILE,
        "-d",
        TEST_FILE,
        "-p",
        PREDICTIONS_FILE,
        "--quiet",
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return None

    try:
        with open(PREDICTIONS_FILE, "r") as f:
            prediction_str = f.read().strip()
    except FileNotFoundError:
        return None

    if not prediction_str:
        return None

    action_probs = {}
    for pair in prediction_str.split(","):
        if ":" in pair:
            action, prob = pair.split(":")
            action_probs[int(action)] = float(prob)

    if not action_probs:
        return None

    sorted_actions = sorted(action_probs.items(), key=lambda x: x[1], reverse=True)

    is_relaxation = task_type.lower() in [
        "relaxation",
        "relax",
        "break",
        "rest",
        "sleep",
    ]

    for action, prob in sorted_actions:
        time_slot = TIME_SLOTS[action]

        if is_time_blocked(day_of_week, time_slot, BLOCKED_TIMES):
            continue

        if not is_relaxation:
            if (
                time_slot - TASK_BUFFER < START_HOUR
                or time_slot + task_duration + TASK_BUFFER > END_HOUR
            ):
                continue

        return (day_of_week, time_slot, task_duration)

    return None


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
        probability: The probability of the action (20% of week for this task)
    """
    # Calculate probability as 20% of the week for this task
    if probability is None:
        # Calculate total available hours in a week (16 hours per day * 7 days)
        total_weekly_hours = 16 * 7
        # Calculate probability as 20% of the week for this task
        probability = (task_duration / total_weekly_hours) * 0.2

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
    with open(FEEDBACK_FILE, "a") as f:
        f.write(f"{example}\n")

    if not os.path.exists(FEEDBACK_FILE) or os.path.getsize(FEEDBACK_FILE) == 0:
        return

    cmd = [
        "vw",
        "--cb_explore",
        str(len(TIME_SLOTS)),
        "-d",
        FEEDBACK_FILE,
        "-i",
        MODEL_FILE,
        "-f",
        MODEL_FILE,
        "--quiet",
    ]

    subprocess.run(cmd, check=True)

    with open(FEEDBACK_FILE, "w") as f:
        f.write("")


def train_model():
    with open(ACTIONS_FILE, "w") as f:
        for i, time in enumerate(TIME_SLOTS):
            f.write(f"{i}:{time}\n")

    cmd = [
        "vw",
        "--cb_explore",
        str(len(TIME_SLOTS)),
        "-d",
        TRAIN_FILE,
        "-f",
        MODEL_FILE,
        "--quiet",
    ]

    subprocess.run(cmd, check=True)


def reset_recommended_times():
    global RECOMMENDED_TIMES
    RECOMMENDED_TIMES = {}


def add_blocked_time(day_of_week, start_time, end_time, reason="blocked"):
    global BLOCKED_TIMES

    for time_slot in TIME_SLOTS:
        if start_time <= time_slot < end_time:
            BLOCKED_TIMES[(day_of_week, time_slot)] = reason


def clear_blocked_times():
    global BLOCKED_TIMES
    BLOCKED_TIMES = {}


def clear_scheduled_events():
    global SCHEDULED_EVENTS
    SCHEDULED_EVENTS = {}


def add_scheduled_event(day_of_week, start_time, end_time, event_name):
    global SCHEDULED_EVENTS, BLOCKED_TIMES

    SCHEDULED_EVENTS[(day_of_week, start_time, end_time)] = event_name

    add_blocked_time(day_of_week, start_time, end_time, f"scheduled: {event_name}")

    buffer_end = min(end_time + EVENT_BUFFER, END_HOUR)
    add_blocked_time(day_of_week, end_time, buffer_end, f"event_buffer: {event_name}")


# ***************************** FOR DEMO + TESTING *****************************

if __name__ == "__main__":
    train_model()
    reset_recommended_times()

    add_scheduled_event(1, 9.0, 10.5, "Math Class")
    add_scheduled_event(1, 11.0, 12.5, "Science Class")
    add_scheduled_event(3, 14.0, 15.5, "History Class")
    add_blocked_time(4, 15.0, 16.0, "Doctor Appointment")

    result = generate_recommendations(
        task_type="hw", task_duration=2.0, hours_until_due=24, daily_free_time=6.0
    )

    if isinstance(result, tuple):
        day, predicted_time, duration = result
    else:
        for i, (day, time, duration) in enumerate(result, 1):
            pass

    long_result = generate_recommendations(
        task_type="project",
        task_duration=8.0,
        hours_until_due=72,
        daily_free_time=6.0,
        prefer_splitting=True,
    )
