import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional
from event_categories import get_category_for_event_type

# Constants for time recommendations
START_HOUR = 6  # 6 AM
END_HOUR = 22  # 10 PM
TIME_STEP = 0.5  # 30-minute intervals


def generate_time_slots() -> List[float]:
    """Generate discrete time slots for recommendations."""
    return np.arange(START_HOUR, END_HOUR + TIME_STEP, TIME_STEP)


# Generate time slots once at module import
TIME_SLOTS = generate_time_slots()


def format_vw_example(
    features: Dict[str, Union[str, float, int]],
    action: int,
    cost: Optional[float] = None,
    probability: Optional[float] = None,
) -> str:
    """
    Format an example for VW contextual bandits.

    Args:
        features: Dictionary of feature names and values
        action: Index of the chosen action
        cost: Cost/reward for the action (optional)
        probability: Probability of the action (optional)

    Returns:
        Formatted VW example string
    """
    # Format features
    feature_str = " ".join(f"{k}:{v}" for k, v in features.items())

    # Format action and cost/probability if provided
    if cost is not None and probability is not None:
        return f"{action}:{cost}:{probability} | {feature_str}"
    elif cost is not None:
        return f"{action}:{cost} | {feature_str}"
    else:
        return f"{action} | {feature_str}"


def format_day_and_time(day: int, time: float) -> str:
    """Convert day of week and time slot to human-readable string."""
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    hour = int(time)
    minute = int((time - hour) * 60)
    return f"{days[day]} at {hour:02d}:{minute:02d}"


def format_duration(hours: float) -> str:
    """Convert duration in hours to human-readable string."""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes} minutes"
    else:
        whole_hours = int(hours)
        minutes = int((hours - whole_hours) * 60)
        if minutes == 0:
            return f"{whole_hours} hour{'s' if whole_hours != 1 else ''}"
        else:
            return f"{whole_hours} hour{'s' if whole_hours != 1 else ''} and {minutes} minutes"


def is_time_blocked(
    day: int, time: float, blocked_times: Dict[Tuple[int, float], str]
) -> bool:
    """Check if a time slot is blocked."""
    return (day, time) in blocked_times


def get_blocked_reason(
    day: int, time: float, blocked_times: Dict[Tuple[int, float], str]
) -> Optional[str]:
    """Get the reason for blocking a time slot."""
    return blocked_times.get((day, time))


def create_training_example(
    task_type: str,
    task_duration: float,
    hours_until_due: float,
    daily_free_time: float,
    chosen_time: float,
    actual_time: float,
    day_of_week: int,
    probability: Optional[float] = None,
) -> str:
    """
    Create a training example with feedback.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        chosen_time: The time slot that was chosen
        actual_time: The actual time the task was completed
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        probability: The probability of the action (optional)

    Returns:
        Formatted VW example string
    """
    # Find the closest time slot to the chosen time
    chosen_slot = min(TIME_SLOTS, key=lambda x: abs(x - chosen_time))

    # Find the index of the chosen slot in TIME_SLOTS
    # Use a more robust method to find the index
    slot_index = 0
    for i, slot in enumerate(TIME_SLOTS):
        if abs(slot - chosen_slot) < 0.01:  # Use a small epsilon for float comparison
            slot_index = i
            break

    # Calculate cost based on the difference between chosen and actual time
    cost = abs(chosen_time - actual_time) / 24.0  # Normalize to [0, 1]

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
    return format_vw_example(features, slot_index, cost, probability)


def create_prediction_example(
    task_type: str,
    task_duration: float,
    hours_until_due: float,
    daily_free_time: float,
    day_of_week: int,
) -> str:
    """
    Create a prediction example without feedback.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        task_duration: Expected duration in hours
        hours_until_due: Hours until the task is due
        daily_free_time: Available free time in the day
        day_of_week: Day of the week (0=Monday, 6=Sunday)

    Returns:
        Formatted VW example string
    """
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

    # Format the example without action or cost
    return format_vw_example(
        features, 0
    )  # Action index will be ignored during prediction
