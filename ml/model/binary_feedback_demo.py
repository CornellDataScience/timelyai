#!/usr/bin/env python3
"""
FOR TESTING PURPOSES:Binary Feedback Demo for the time recommendation system.
This script demonstrates how the model learns from binary accept/reject feedback
and improves its recommendations over time.
"""

import os
import sys
from datetime import datetime
from contextual_bandits import (
    train_model,
    predict_best_time,
    generate_recommendations,
    record_binary_feedback,
    update_model,
    reset_recommended_times,
    format_duration,
    create_training_example,
)
from event_categories import (
    CATEGORIES,
    EVENT_TYPE_TO_CATEGORY,
    get_category_for_event_type,
    get_event_type_info,
)


def format_time(time_value):
    """Format a time value (e.g., 13.5) as a time string (e.g., 13:30)."""
    hours = int(time_value)
    minutes = int((time_value - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"


def format_day_and_time(day, time, duration=None):
    """Format day and time into a human-readable string."""
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    time_str = format_time(time)
    if duration:
        return f"{days[day]} at {time_str} for {format_duration(duration)}"
    return f"{days[day]} at {time_str}"


def simulate_user_preference(task_type, time, day, prefer_splitting=False):
    """
    Simulate user preference for a time recommendation.
    Returns True if the user accepts the recommendation, False otherwise.
    """
    # Get event info for the task type
    event_info = get_event_type_info(task_type)
    if not event_info:
        return True  # Default to accepting if no event info

    # Get preferred times for this task type
    preferred_times = event_info.get("preferred_times", [])
    if not preferred_times:
        return True  # Default to accepting if no preferred times

    # Check if the recommended time is in the preferred range
    if preferred_times == "morning" and 6 <= time < 12:
        return True
    elif preferred_times == "afternoon" and 12 <= time < 17:
        return True
    elif preferred_times == "evening" and 17 <= time < 22:
        return True
    elif preferred_times == "night" and (time >= 22 or time < 6):
        return True

    # For long tasks with splitting, be more lenient
    if prefer_splitting:
        return True

    # If not in preferred range, 70% chance of rejection
    return False


def main():
    """Run a demo of the binary feedback system."""
    print("🔄 Binary Feedback Learning Demo 🔄")
    print("===================================\n")

    # Train the initial model
    print("1️⃣ Training the initial model...")
    train_model()

    # First round of recommendations
    print("\n2️⃣ First round of recommendations (before feedback)...\n")
    reset_recommended_times()

    # Example 1: School task (homework due tomorrow)
    print("📚 Example 1: Homework due tomorrow (urgent, short task)")
    day1, hw_time, hw_duration = predict_best_time(
        task_type="hw", task_duration=1.5, hours_until_due=24, daily_free_time=4.0
    )
    print(f"   Recommended time: {format_day_and_time(day1, hw_time, hw_duration)}")

    # Simulate user accepting or rejecting the recommendation
    hw_accepted = simulate_user_preference("hw", hw_time, day1)
    print(f"   User {'accepted' if hw_accepted else 'rejected'} the recommendation")
    print()

    # Example 2: Social task (meeting in 3 days)
    print("👥 Example 2: Meeting in 3 days (medium urgency)")
    day2, meeting_time, meeting_duration = predict_best_time(
        task_type="meeting", task_duration=1.0, hours_until_due=72, daily_free_time=4.0
    )
    print(
        f"   Recommended time: {format_day_and_time(day2, meeting_time, meeting_duration)}"
    )

    # Simulate user accepting or rejecting the recommendation
    meeting_accepted = simulate_user_preference("meeting", meeting_time, day2)
    print(
        f"   User {'accepted' if meeting_accepted else 'rejected'} the recommendation"
    )
    print()

    # Example 3: School task (project due in 7 days)
    # First, try with splitting (prefer_splitting=True)
    print(
        "📊 Example 3a: Project due in 7 days (long task, low urgency) - With splitting"
    )
    project_recommendations = generate_recommendations(
        task_type="project",
        task_duration=6.0,
        hours_until_due=168,
        daily_free_time=4.0,
        prefer_splitting=True,
    )
    print("   Recommended times (split across multiple sessions):")
    for i, (day, time, duration) in enumerate(project_recommendations):
        print(f"   Session {i+1}: {format_day_and_time(day, time, duration)}")

    # Simulate user accepting or rejecting each session
    project_accepted = []
    for day, time, duration in project_recommendations:
        accepted = simulate_user_preference("project", time, day, prefer_splitting=True)
        project_accepted.append(accepted)
        print(
            f"   User {'accepted' if accepted else 'rejected'} session {len(project_accepted)}"
        )
    print()

    # Example 4: Health & Fitness task (workout)
    print("💪 Example 4: Workout (Health & Fitness category)")
    day4, workout_time, workout_duration = predict_best_time(
        task_type="workout", task_duration=1.0, hours_until_due=48, daily_free_time=4.0
    )
    print(
        f"   Recommended time: {format_day_and_time(day4, workout_time, workout_duration)}"
    )

    # Simulate user accepting or rejecting the recommendation
    workout_accepted = simulate_user_preference("workout", workout_time, day4)
    print(
        f"   User {'accepted' if workout_accepted else 'rejected'} the recommendation"
    )
    print()

    # Record feedback for all examples
    print("3️⃣ Recording feedback...\n")

    # Record feedback for homework
    record_binary_feedback(
        task_type="hw",
        task_duration=hw_duration,
        hours_until_due=24,
        daily_free_time=4.0,
        chosen_time=hw_time,
        day_of_week=day1,
        was_accepted=hw_accepted,
    )

    # Record feedback for meeting
    record_binary_feedback(
        task_type="meeting",
        task_duration=meeting_duration,
        hours_until_due=72,
        daily_free_time=4.0,
        chosen_time=meeting_time,
        day_of_week=day2,
        was_accepted=meeting_accepted,
    )

    # Record feedback for project sessions (with splitting)
    for i, ((day, time, duration), accepted) in enumerate(
        zip(project_recommendations, project_accepted)
    ):
        record_binary_feedback(
            task_type="project",
            task_duration=duration,
            hours_until_due=168 - (i * 24),  # Adjust hours until due for later sessions
            daily_free_time=4.0,
            chosen_time=time,
            day_of_week=day,
            was_accepted=accepted,
        )

    # Record feedback for workout
    record_binary_feedback(
        task_type="workout",
        task_duration=workout_duration,
        hours_until_due=48,
        daily_free_time=4.0,
        chosen_time=workout_time,
        day_of_week=day4,
        was_accepted=workout_accepted,
    )

    # Update the model with feedback
    print("\n4️⃣ Updating the model with feedback...")

    # Create training examples and update model for each feedback
    # Homework
    hw_example = create_training_example(
        task_type="hw",
        task_duration=hw_duration,
        hours_until_due=24,
        daily_free_time=4.0,
        chosen_time=hw_time,
        day_of_week=day1,
        actual_time=(
            hw_time if hw_accepted else hw_time + 12.0
        ),  # Use a different time for rejected recommendations
    )
    update_model(hw_example, 0.0 if hw_accepted else 1.0)

    # Meeting
    meeting_example = create_training_example(
        task_type="meeting",
        task_duration=meeting_duration,
        hours_until_due=72,
        daily_free_time=4.0,
        chosen_time=meeting_time,
        day_of_week=day2,
        actual_time=(
            meeting_time if meeting_accepted else meeting_time + 12.0
        ),  # Use a different time for rejected recommendations
    )
    update_model(meeting_example, 0.0 if meeting_accepted else 1.0)

    # Project sessions
    for i, ((day, time, duration), accepted) in enumerate(
        zip(project_recommendations, project_accepted)
    ):
        project_example = create_training_example(
            task_type="project",
            task_duration=duration,
            hours_until_due=168 - (i * 24),
            daily_free_time=4.0,
            chosen_time=time,
            day_of_week=day,
            actual_time=(
                time if accepted else time + 12.0
            ),  # Use a different time for rejected recommendations
        )
        update_model(project_example, 0.0 if accepted else 1.0)

    # Workout
    workout_example = create_training_example(
        task_type="workout",
        task_duration=workout_duration,
        hours_until_due=48,
        daily_free_time=4.0,
        chosen_time=workout_time,
        day_of_week=day4,
        actual_time=(
            workout_time if workout_accepted else workout_time + 12.0
        ),  # Use a different time for rejected recommendations
    )
    update_model(workout_example, 0.0 if workout_accepted else 1.0)

    # Second round of recommendations (after feedback)
    print("\n5️⃣ Second round of recommendations (after feedback)...\n")
    reset_recommended_times()

    # Example 1: School task (homework due tomorrow)
    print("📚 Example 1: Homework due tomorrow (urgent, short task)")
    day1_2, hw_time_2, hw_duration_2 = predict_best_time(
        task_type="hw", task_duration=1.5, hours_until_due=24, daily_free_time=4.0
    )
    print(
        f"   Recommended time: {format_day_and_time(day1_2, hw_time_2, hw_duration_2)}"
    )

    # Simulate user accepting or rejecting the recommendation
    hw_accepted_2 = simulate_user_preference("hw", hw_time_2, day1_2)
    print(f"   User {'accepted' if hw_accepted_2 else 'rejected'} the recommendation")
    print()

    # Example 2: Social task (meeting in 3 days)
    print("👥 Example 2: Meeting in 3 days (medium urgency)")
    day2_2, meeting_time_2, meeting_duration_2 = predict_best_time(
        task_type="meeting", task_duration=1.0, hours_until_due=72, daily_free_time=4.0
    )
    print(
        f"   Recommended time: {format_day_and_time(day2_2, meeting_time_2, meeting_duration_2)}"
    )

    # Simulate user accepting or rejecting the recommendation
    meeting_accepted_2 = simulate_user_preference("meeting", meeting_time_2, day2_2)
    print(
        f"   User {'accepted' if meeting_accepted_2 else 'rejected'} the recommendation"
    )
    print()

    # Example 3: School task (project due in 7 days)
    # First, try with splitting (prefer_splitting=True)
    print(
        "📊 Example 3a: Project due in 7 days (long task, low urgency) - With splitting"
    )
    project_recommendations_2 = generate_recommendations(
        task_type="project",
        task_duration=6.0,
        hours_until_due=168,
        daily_free_time=4.0,
        prefer_splitting=True,
    )
    print("   Recommended times (split across multiple sessions):")
    for i, (day, time, duration) in enumerate(project_recommendations_2):
        print(f"   Session {i+1}: {format_day_and_time(day, time, duration)}")

    # Simulate user accepting or rejecting each session
    project_accepted_2 = []
    for day, time, duration in project_recommendations_2:
        accepted = simulate_user_preference("project", time, day, prefer_splitting=True)
        project_accepted_2.append(accepted)
        print(
            f"   User {'accepted' if accepted else 'rejected'} session {len(project_accepted_2)}"
        )
    print()

    # Example 4: Health & Fitness task (workout)
    print("💪 Example 4: Workout (Health & Fitness category)")
    day4_2, workout_time_2, workout_duration_2 = predict_best_time(
        task_type="workout", task_duration=1.0, hours_until_due=48, daily_free_time=4.0
    )
    print(
        f"   Recommended time: {format_day_and_time(day4_2, workout_time_2, workout_duration_2)}"
    )

    # Simulate user accepting or rejecting the recommendation
    workout_accepted_2 = simulate_user_preference("workout", workout_time_2, day4_2)
    print(
        f"   User {'accepted' if workout_accepted_2 else 'rejected'} the recommendation"
    )
    print()


if __name__ == "__main__":
    main()
