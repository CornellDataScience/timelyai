import os
import sys
import numpy as np
from datetime import datetime, timedelta
from contextual_bandits import (
    predict_best_time,
    predict_best_times_for_long_task,
    record_binary_feedback,
    update_model,
    reset_recommended_times,
    add_class_schedule,
    add_blocked_time,
    clear_blocked_times,
    clear_class_schedule,
    format_day_and_time,
    format_duration,
)
from event_categories import (
    CATEGORIES,
    EVENT_TYPE_TO_CATEGORY,
    get_category_for_event_type,
    get_event_type_info,
)


def simulate_user_preference(
    task_type, recommended_time, day_of_week, prefer_splitting=False
):
    """
    Simulate whether a user would accept a time recommendation.
    This is a simplified simulation - in a real application, this would be
    based on actual user feedback.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        recommended_time: The recommended time slot
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        prefer_splitting: Whether the user prefers to split long tasks

    Returns:
        True if the user would accept the recommendation, False otherwise
    """
    # Get category information for the task type
    category = get_category_for_event_type(task_type)
    event_info = get_event_type_info(task_type)

    # If we have event info, use it to determine acceptance
    if event_info:
        # Check if the recommended time is within the preferred times
        preferred_times = event_info.get("preferred_times", [])
        if preferred_times:
            # Check if the recommended time is within any of the preferred time ranges
            for time_range in preferred_times:
                # Handle both tuple and list formats
                if isinstance(time_range, (tuple, list)) and len(time_range) == 2:
                    start_time, end_time = time_range
                    if start_time <= recommended_time <= end_time:
                        return True
                # Handle single value format
                elif isinstance(time_range, (int, float)):
                    # If it's a single value, consider it a preferred time with a 1-hour window
                    if abs(time_range - recommended_time) <= 0.5:
                        return True

    # Fallback to task-specific logic
    if task_type.lower() in ["hw", "homework", "study", "reading"]:
        # Prefer morning or evening for academic tasks
        return 8.0 <= recommended_time <= 11.0 or 18.0 <= recommended_time <= 21.0
    elif task_type.lower() in ["meeting", "call", "interview"]:
        # Prefer middle of the day for meetings
        return 10.0 <= recommended_time <= 16.0
    elif task_type.lower() in ["project", "work", "coding"]:
        # For project work, consider the prefer_splitting parameter
        if prefer_splitting:
            # If user prefers splitting, accept shorter time slots
            return True
        else:
            # Otherwise, prefer longer uninterrupted blocks
            return 9.0 <= recommended_time <= 17.0
    elif task_type.lower() in ["workout", "exercise", "gym"]:
        # Prefer morning or evening for workouts
        return 6.0 <= recommended_time <= 9.0 or 17.0 <= recommended_time <= 20.0
    elif task_type.lower() in ["relaxation", "relax", "break", "rest"]:
        # Accept any time for relaxation
        return True
    else:
        # Default: accept with 70% probability
        return np.random.random() < 0.7


def format_day_and_time(day_of_week, time_slot, duration=None):
    """
    Format a day and time slot as a human-readable string.

    Args:
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        time_slot: Time slot in 24-hour format (e.g., 14.0 for 2:00 PM)
        duration: Optional duration in hours

    Returns:
        A formatted string (e.g., "Monday at 14:00 for 2 hours")
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

    if duration is not None:
        duration_str = format_duration(duration)
        return f"{day_str} at {time_str} for {duration_str}"
    else:
        return f"{day_str} at {time_str}"


def main():
    """Run a demo of the binary feedback system."""
    print("🚀 Starting Binary Feedback Demo")
    print("=================================")

    # Reset recommended times
    reset_recommended_times()

    # Clear any existing blocked times and class schedules
    clear_blocked_times()
    clear_class_schedule()

    # Add some example class schedules
    print("\n📚 Adding class schedules:")
    add_class_schedule(0, 9.0, 10.5, "Math Class")  # Monday 9:00 AM - 10:30 AM
    add_class_schedule(0, 11.0, 12.5, "Science Class")  # Monday 11:00 AM - 12:30 PM
    add_class_schedule(2, 14.0, 15.5, "History Class")  # Wednesday 2:00 PM - 3:30 PM
    add_class_schedule(4, 13.0, 14.5, "English Class")  # Friday 1:00 PM - 2:30 PM

    # Add some other blocked times
    print("\n🕒 Adding other blocked times:")
    add_blocked_time(1, 15.0, 16.0, "Doctor Appointment")  # Tuesday 3:00 PM - 4:00 PM
    add_blocked_time(3, 12.0, 13.0, "Lunch Meeting")  # Thursday 12:00 PM - 1:00 PM

    # Example 1: Short task (homework)
    print("\n📝 Example 1: Short task (homework)")
    print("----------------------------------")
    day, time, duration = predict_best_time(
        task_type="hw", task_duration=1.5, hours_until_due=48, daily_free_time=6.0
    )
    print(f"Recommended time: {format_day_and_time(day, time, duration)}")

    # Simulate user feedback
    was_accepted = simulate_user_preference("hw", time, day)
    print(f"User {'accepted' if was_accepted else 'rejected'} the recommendation")

    # Record feedback
    record_binary_feedback(
        task_type="hw",
        task_duration=1.5,
        hours_until_due=48,
        daily_free_time=6.0,
        chosen_time=time,
        day_of_week=day,
        was_accepted=was_accepted,
    )

    # If rejected, get an alternative recommendation
    if not was_accepted:
        print("\n🔄 Getting alternative recommendation...")
        day, time, duration = predict_best_time(
            task_type="hw", task_duration=1.5, hours_until_due=48, daily_free_time=6.0
        )
        print(f"Alternative recommendation: {format_day_and_time(day, time, duration)}")

        # Simulate user feedback for the alternative
        was_accepted = simulate_user_preference("hw", time, day)
        print(f"User {'accepted' if was_accepted else 'rejected'} the alternative")

        # Record feedback for the alternative
        record_binary_feedback(
            task_type="hw",
            task_duration=1.5,
            hours_until_due=48,
            daily_free_time=6.0,
            chosen_time=time,
            day_of_week=day,
            was_accepted=was_accepted,
        )

    # Example 2: Medium task (meeting)
    print("\n👥 Example 2: Medium task (meeting)")
    print("----------------------------------")
    day, time, duration = predict_best_time(
        task_type="meeting", task_duration=2.0, hours_until_due=72, daily_free_time=8.0
    )
    print(f"Recommended time: {format_day_and_time(day, time, duration)}")

    # Simulate user feedback
    was_accepted = simulate_user_preference("meeting", time, day)
    print(f"User {'accepted' if was_accepted else 'rejected'} the recommendation")

    # Record feedback
    record_binary_feedback(
        task_type="meeting",
        task_duration=2.0,
        hours_until_due=72,
        daily_free_time=8.0,
        chosen_time=time,
        day_of_week=day,
        was_accepted=was_accepted,
    )

    # Example 3a: Long task with splitting (project work)
    print("\n💻 Example 3a: Long task with splitting (project work)")
    print("--------------------------------------------------")
    recommendations = predict_best_times_for_long_task(
        task_type="project",
        task_duration=6.0,
        hours_until_due=120,
        daily_free_time=8.0,
        prefer_splitting=True,
    )

    print("Recommended times:")
    for i, (day, time, duration) in enumerate(recommendations, 1):
        print(f"  {i}. {format_day_and_time(day, time, duration)}")

    # Simulate user feedback for each recommendation
    for i, (day, time, duration) in enumerate(recommendations, 1):
        was_accepted = simulate_user_preference(
            "project", time, day, prefer_splitting=True
        )
        print(f"User {'accepted' if was_accepted else 'rejected'} recommendation {i}")

        # Record feedback
        record_binary_feedback(
            task_type="project",
            task_duration=duration,
            hours_until_due=120
            - (i - 1) * 24,  # Adjust hours until due for later sessions
            daily_free_time=8.0,
            chosen_time=time,
            day_of_week=day,
            was_accepted=was_accepted,
        )

    # Example 3b: Long task without splitting (project work)
    print("\n💻 Example 3b: Long task without splitting (project work)")
    print("----------------------------------------------------")
    day, time, duration = predict_best_time(
        task_type="project", task_duration=6.0, hours_until_due=120, daily_free_time=8.0
    )
    print(f"Recommended time: {format_day_and_time(day, time, duration)}")

    # Simulate user feedback
    was_accepted = simulate_user_preference(
        "project", time, day, prefer_splitting=False
    )
    print(f"User {'accepted' if was_accepted else 'rejected'} the recommendation")

    # Record feedback
    record_binary_feedback(
        task_type="project",
        task_duration=6.0,
        hours_until_due=120,
        daily_free_time=8.0,
        chosen_time=time,
        day_of_week=day,
        was_accepted=was_accepted,
    )

    # Example 4: Workout (considering class schedules)
    print("\n💪 Example 4: Workout (considering class schedules)")
    print("-----------------------------------------------")
    day, time, duration = predict_best_time(
        task_type="workout", task_duration=1.0, hours_until_due=24, daily_free_time=4.0
    )
    print(f"Recommended time: {format_day_and_time(day, time, duration)}")

    # Simulate user feedback
    was_accepted = simulate_user_preference("workout", time, day)
    print(f"User {'accepted' if was_accepted else 'rejected'} the recommendation")

    # Record feedback
    record_binary_feedback(
        task_type="workout",
        task_duration=1.0,
        hours_until_due=24,
        daily_free_time=4.0,
        chosen_time=time,
        day_of_week=day,
        was_accepted=was_accepted,
    )

    # Update the model with all the feedback
    print("\n🔄 Updating model with feedback...")
    update_model()

    # Show how recommendations improve after feedback
    print("\n📊 Showing improved recommendations after feedback")
    print("---------------------------------------------")

    # Example 5: Homework after feedback
    print("\n📝 Example 5: Homework after feedback")
    print("----------------------------------")
    day, time, duration = predict_best_time(
        task_type="hw", task_duration=1.5, hours_until_due=48, daily_free_time=6.0
    )
    print(f"Recommended time: {format_day_and_time(day, time, duration)}")

    # Example 6: Meeting after feedback
    print("\n👥 Example 6: Meeting after feedback")
    print("----------------------------------")
    day, time, duration = predict_best_time(
        task_type="meeting", task_duration=2.0, hours_until_due=72, daily_free_time=8.0
    )
    print(f"Recommended time: {format_day_and_time(day, time, duration)}")

    # Example 7: Project work after feedback (with splitting)
    print("\n💻 Example 7: Project work after feedback (with splitting)")
    print("--------------------------------------------------")
    recommendations = predict_best_times_for_long_task(
        task_type="project",
        task_duration=6.0,
        hours_until_due=120,
        daily_free_time=8.0,
        prefer_splitting=True,
    )

    print("Recommended times:")
    for i, (day, time, duration) in enumerate(recommendations, 1):
        print(f"  {i}. {format_day_and_time(day, time, duration)}")

    # Example 8: Workout after feedback
    print("\n💪 Example 8: Workout after feedback")
    print("-----------------------------------------------")
    day, time, duration = predict_best_time(
        task_type="workout", task_duration=1.0, hours_until_due=24, daily_free_time=4.0
    )
    print(f"Recommended time: {format_day_and_time(day, time, duration)}")

    print("\n✅ Binary feedback demo completed")


if __name__ == "__main__":
    main()
