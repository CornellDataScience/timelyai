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
    predict_best_times_for_long_task,
    record_binary_feedback,
    get_alternative_recommendation,
    update_model,
    reset_recommended_times,
    format_duration,
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


def format_day_and_time(day, time_value, duration=None):
    """Format a day and time value as a readable string."""
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    day_str = day_names[day]
    time_str = format_time(time_value)

    if duration is not None:
        duration_str = format_duration(duration)
        return f"{day_str} at {time_str} for {duration_str}"
    else:
        return f"{day_str} at {time_str}"


def simulate_user_preference(
    task_type, recommended_time, day_of_week, prefer_splitting=False
):
    """
    Simulate whether a user would accept or reject a recommendation.
    This creates realistic feedback data for the model to learn from.

    Args:
        task_type: Type of task (e.g., 'hw', 'meeting', 'reading')
        recommended_time: The time recommended by the model
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        prefer_splitting: Whether the user prefers to split tasks (True) or complete them in one go (False)

    Returns:
        A boolean indicating whether the user would accept the recommendation
    """
    # Get category information for the task type
    category = get_category_for_event_type(task_type)
    event_info = get_event_type_info(task_type)

    # If we have event info, use it to determine preferences
    if event_info:
        preferred_times = event_info["preferred_times"]

        # Check if the recommended time aligns with preferred times
        if preferred_times == "morning" and recommended_time < 12.0:
            return True
        elif preferred_times == "afternoon" and 12.0 <= recommended_time < 18.0:
            return True
        elif preferred_times == "evening" and recommended_time >= 18.0:
            return True
        elif preferred_times == "night" and (
            recommended_time >= 20.0 or recommended_time < 6.0
        ):
            return True
        elif preferred_times == "flexible":
            # For flexible tasks, accept most times
            return True

    # Fallback to specific task type preferences if no category info
    if task_type == "hw":
        # User prefers to do homework in the morning (before 12:00)
        return recommended_time < 12.0
    elif task_type == "meeting":
        # User prefers meetings in the afternoon (after 13:00)
        return recommended_time >= 13.0
    elif task_type == "reading":
        # User prefers reading in the evening (after 18:00)
        return recommended_time >= 18.0
    elif task_type == "project":
        # For projects, consider the user's preference for splitting
        if prefer_splitting:
            # User prefers to split projects into smaller sessions
            return True
        else:
            # User prefers to complete projects in one go
            return recommended_time >= 14.0 and recommended_time <= 20.0
    elif task_type in ["relaxation", "relax", "break", "rest", "sleep", "nap"]:
        # User is flexible with relaxation time
        return True
    else:
        # For other tasks, user is somewhat flexible
        return True


def main():
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

    # If rejected, get an alternative recommendation
    if not hw_accepted:
        print("   Getting alternative recommendation...")
        day1, hw_time, hw_duration = get_alternative_recommendation(
            task_type="hw",
            task_duration=1.5,
            hours_until_due=24,
            daily_free_time=4.0,
            rejected_time=hw_time,
            day_of_week=day1,
        )
        print(
            f"   Alternative recommendation: {format_day_and_time(day1, hw_time, hw_duration)}"
        )
        # Simulate whether the user accepts the alternative
        hw_accepted = simulate_user_preference("hw", hw_time, day1)
        print(
            f"   User {'accepted' if hw_accepted else 'rejected'} the alternative recommendation"
        )
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

    # If rejected, get an alternative recommendation
    if not meeting_accepted:
        print("   Getting alternative recommendation...")
        day2, meeting_time, meeting_duration = get_alternative_recommendation(
            task_type="meeting",
            task_duration=1.0,
            hours_until_due=72,
            daily_free_time=4.0,
            rejected_time=meeting_time,
            day_of_week=day2,
        )
        print(
            f"   Alternative recommendation: {format_day_and_time(day2, meeting_time, meeting_duration)}"
        )
        # Simulate whether the user accepts the alternative
        meeting_accepted = simulate_user_preference("meeting", meeting_time, day2)
        print(
            f"   User {'accepted' if meeting_accepted else 'rejected'} the alternative recommendation"
        )
    print()

    # Example 3: School task (project due in 7 days)
    # First, try with splitting (prefer_splitting=True)
    print(
        "📊 Example 3a: Project due in 7 days (long task, low urgency) - With splitting"
    )
    project_recommendations = predict_best_times_for_long_task(
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

        # If rejected, get an alternative recommendation
        if not accepted:
            print(
                f"   Getting alternative recommendation for session {len(project_accepted)}..."
            )
            alt_day, alt_time, alt_duration = get_alternative_recommendation(
                task_type="project",
                task_duration=duration,
                hours_until_due=168,
                daily_free_time=4.0,
                rejected_time=time,
                day_of_week=day,
            )
            print(
                f"   Alternative recommendation: {format_day_and_time(alt_day, alt_time, alt_duration)}"
            )
            # Update the recommendation
            project_recommendations[len(project_accepted) - 1] = (
                alt_day,
                alt_time,
                alt_duration,
            )
            # Simulate whether the user accepts the alternative
            accepted = simulate_user_preference(
                "project", alt_time, alt_day, prefer_splitting=True
            )
            print(
                f"   User {'accepted' if accepted else 'rejected'} the alternative recommendation"
            )
            project_accepted[-1] = accepted
    print()

    # Now try without splitting (prefer_splitting=False)
    print(
        "📊 Example 3b: Project due in 7 days (long task, low urgency) - Without splitting"
    )
    project_recommendations_no_split = predict_best_times_for_long_task(
        task_type="project",
        task_duration=6.0,
        hours_until_due=168,
        daily_free_time=4.0,
        prefer_splitting=False,
    )
    print("   Recommended time (single session):")
    for i, (day, time, duration) in enumerate(project_recommendations_no_split):
        print(f"   {format_day_and_time(day, time, duration)}")

    # Simulate user accepting or rejecting the recommendation
    project_accepted_no_split = []
    for day, time, duration in project_recommendations_no_split:
        accepted = simulate_user_preference(
            "project", time, day, prefer_splitting=False
        )
        project_accepted_no_split.append(accepted)
        print(f"   User {'accepted' if accepted else 'rejected'} the recommendation")

        # If rejected, get an alternative recommendation
        if not accepted:
            print("   Getting alternative recommendation...")
            alt_day, alt_time, alt_duration = get_alternative_recommendation(
                task_type="project",
                task_duration=duration,
                hours_until_due=168,
                daily_free_time=4.0,
                rejected_time=time,
                day_of_week=day,
            )
            print(
                f"   Alternative recommendation: {format_day_and_time(alt_day, alt_time, alt_duration)}"
            )
            # Update the recommendation
            project_recommendations_no_split[0] = (alt_day, alt_time, alt_duration)
            # Simulate whether the user accepts the alternative
            accepted = simulate_user_preference(
                "project", alt_time, alt_day, prefer_splitting=False
            )
            print(
                f"   User {'accepted' if accepted else 'rejected'} the alternative recommendation"
            )
            project_accepted_no_split[0] = accepted
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

    # If rejected, get an alternative recommendation
    if not workout_accepted:
        print("   Getting alternative recommendation...")
        day4, workout_time, workout_duration = get_alternative_recommendation(
            task_type="workout",
            task_duration=1.0,
            hours_until_due=48,
            daily_free_time=4.0,
            rejected_time=workout_time,
            day_of_week=day4,
        )
        print(
            f"   Alternative recommendation: {format_day_and_time(day4, workout_time, workout_duration)}"
        )
        # Simulate whether the user accepts the alternative
        workout_accepted = simulate_user_preference("workout", workout_time, day4)
        print(
            f"   User {'accepted' if workout_accepted else 'rejected'} the alternative recommendation"
        )
    print()

    # Record feedback for the first round
    print("3️⃣ Recording feedback for the first round...")
    record_binary_feedback(
        task_type="hw",
        task_duration=hw_duration,
        hours_until_due=24,
        daily_free_time=4.0,
        chosen_time=hw_time,
        day_of_week=day1,
        was_accepted=hw_accepted,
    )

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

    # Record feedback for project (without splitting)
    for i, ((day, time, duration), accepted) in enumerate(
        zip(project_recommendations_no_split, project_accepted_no_split)
    ):
        record_binary_feedback(
            task_type="project",
            task_duration=duration,
            hours_until_due=168,
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
    update_model()

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

    # If rejected, get an alternative recommendation
    if not hw_accepted_2:
        print("   Getting alternative recommendation...")
        day1_2, hw_time_2, hw_duration_2 = get_alternative_recommendation(
            task_type="hw",
            task_duration=1.5,
            hours_until_due=24,
            daily_free_time=4.0,
            rejected_time=hw_time_2,
            day_of_week=day1_2,
        )
        print(
            f"   Alternative recommendation: {format_day_and_time(day1_2, hw_time_2, hw_duration_2)}"
        )
        # Simulate whether the user accepts the alternative
        hw_accepted_2 = simulate_user_preference("hw", hw_time_2, day1_2)
        print(
            f"   User {'accepted' if hw_accepted_2 else 'rejected'} the alternative recommendation"
        )
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

    # If rejected, get an alternative recommendation
    if not meeting_accepted_2:
        print("   Getting alternative recommendation...")
        day2_2, meeting_time_2, meeting_duration_2 = get_alternative_recommendation(
            task_type="meeting",
            task_duration=1.0,
            hours_until_due=72,
            daily_free_time=4.0,
            rejected_time=meeting_time_2,
            day_of_week=day2_2,
        )
        print(
            f"   Alternative recommendation: {format_day_and_time(day2_2, meeting_time_2, meeting_duration_2)}"
        )
        # Simulate whether the user accepts the alternative
        meeting_accepted_2 = simulate_user_preference("meeting", meeting_time_2, day2_2)
        print(
            f"   User {'accepted' if meeting_accepted_2 else 'rejected'} the alternative recommendation"
        )
    print()

    # Example 3: School task (project due in 7 days)
    # First, try with splitting (prefer_splitting=True)
    print(
        "📊 Example 3a: Project due in 7 days (long task, low urgency) - With splitting"
    )
    project_recommendations_2 = predict_best_times_for_long_task(
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

        # If rejected, get an alternative recommendation
        if not accepted:
            print(
                f"   Getting alternative recommendation for session {len(project_accepted_2)}..."
            )
            alt_day, alt_time, alt_duration = get_alternative_recommendation(
                task_type="project",
                task_duration=duration,
                hours_until_due=168,
                daily_free_time=4.0,
                rejected_time=time,
                day_of_week=day,
            )
            print(
                f"   Alternative recommendation: {format_day_and_time(alt_day, alt_time, alt_duration)}"
            )
            # Update the recommendation
            project_recommendations_2[len(project_accepted_2) - 1] = (
                alt_day,
                alt_time,
                alt_duration,
            )
            # Simulate whether the user accepts the alternative
            accepted = simulate_user_preference(
                "project", alt_time, alt_day, prefer_splitting=True
            )
            print(
                f"   User {'accepted' if accepted else 'rejected'} the alternative recommendation"
            )
            project_accepted_2[-1] = accepted
    print()

    # Now try without splitting (prefer_splitting=False)
    print(
        "📊 Example 3b: Project due in 7 days (long task, low urgency) - Without splitting"
    )
    project_recommendations_no_split_2 = predict_best_times_for_long_task(
        task_type="project",
        task_duration=6.0,
        hours_until_due=168,
        daily_free_time=4.0,
        prefer_splitting=False,
    )
    print("   Recommended time (single session):")
    for i, (day, time, duration) in enumerate(project_recommendations_no_split_2):
        print(f"   {format_day_and_time(day, time, duration)}")

    # Simulate user accepting or rejecting the recommendation
    project_accepted_no_split_2 = []
    for day, time, duration in project_recommendations_no_split_2:
        accepted = simulate_user_preference(
            "project", time, day, prefer_splitting=False
        )
        project_accepted_no_split_2.append(accepted)
        print(f"   User {'accepted' if accepted else 'rejected'} the recommendation")

        # If rejected, get an alternative recommendation
        if not accepted:
            print("   Getting alternative recommendation...")
            alt_day, alt_time, alt_duration = get_alternative_recommendation(
                task_type="project",
                task_duration=duration,
                hours_until_due=168,
                daily_free_time=4.0,
                rejected_time=time,
                day_of_week=day,
            )
            print(
                f"   Alternative recommendation: {format_day_and_time(alt_day, alt_time, alt_duration)}"
            )
            # Update the recommendation
            project_recommendations_no_split_2[0] = (alt_day, alt_time, alt_duration)
            # Simulate whether the user accepts the alternative
            accepted = simulate_user_preference(
                "project", alt_time, alt_day, prefer_splitting=False
            )
            print(
                f"   User {'accepted' if accepted else 'rejected'} the alternative recommendation"
            )
            project_accepted_no_split_2[0] = accepted
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

    # If rejected, get an alternative recommendation
    if not workout_accepted_2:
        print("   Getting alternative recommendation...")
        day4_2, workout_time_2, workout_duration_2 = get_alternative_recommendation(
            task_type="workout",
            task_duration=1.0,
            hours_until_due=48,
            daily_free_time=4.0,
            rejected_time=workout_time_2,
            day_of_week=day4_2,
        )
        print(
            f"   Alternative recommendation: {format_day_and_time(day4_2, workout_time_2, workout_duration_2)}"
        )
        # Simulate whether the user accepts the alternative
        workout_accepted_2 = simulate_user_preference("workout", workout_time_2, day4_2)
        print(
            f"   User {'accepted' if workout_accepted_2 else 'rejected'} the alternative recommendation"
        )
    print()

    # Record feedback for the second round
    print("6️⃣ Recording feedback for the second round...")
    record_binary_feedback(
        task_type="hw",
        task_duration=hw_duration_2,
        hours_until_due=24,
        daily_free_time=4.0,
        chosen_time=hw_time_2,
        day_of_week=day1_2,
        was_accepted=hw_accepted_2,
    )

    record_binary_feedback(
        task_type="meeting",
        task_duration=meeting_duration_2,
        hours_until_due=72,
        daily_free_time=4.0,
        chosen_time=meeting_time_2,
        day_of_week=day2_2,
        was_accepted=meeting_accepted_2,
    )

    # Record feedback for project sessions (with splitting)
    for i, ((day, time, duration), accepted) in enumerate(
        zip(project_recommendations_2, project_accepted_2)
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

    # Record feedback for project (without splitting)
    for i, ((day, time, duration), accepted) in enumerate(
        zip(project_recommendations_no_split_2, project_accepted_no_split_2)
    ):
        record_binary_feedback(
            task_type="project",
            task_duration=duration,
            hours_until_due=168,
            daily_free_time=4.0,
            chosen_time=time,
            day_of_week=day,
            was_accepted=accepted,
        )

    # Record feedback for workout
    record_binary_feedback(
        task_type="workout",
        task_duration=workout_duration_2,
        hours_until_due=48,
        daily_free_time=4.0,
        chosen_time=workout_time_2,
        day_of_week=day4_2,
        was_accepted=workout_accepted_2,
    )

    # Update the model with feedback again
    print("\n7️⃣ Updating the model with more feedback...")
    update_model()

    # Show how recommendations have improved
    print("\n8️⃣ How recommendations have improved:")
    print(
        f"   Homework: {format_day_and_time(day1, hw_time, hw_duration)} → {format_day_and_time(day1_2, hw_time_2, hw_duration_2)}"
    )
    print(
        f"   Meeting: {format_day_and_time(day2, meeting_time, meeting_duration)} → {format_day_and_time(day2_2, meeting_time_2, meeting_duration_2)}"
    )
    print("   Project: Options for both splitting and completing in one go")
    print(
        f"   Workout: {format_day_and_time(day4, workout_time, workout_duration)} → {format_day_and_time(day4_2, workout_time_2, workout_duration_2)}"
    )

    print("\n✅ Binary feedback demo completed!")
    print(
        "\nThe model has learned from user accept/reject feedback and adjusted its recommendations."
    )
    print(
        "Notice how the recommendations get closer to the user's preferred times over time."
    )
    print("When a recommendation is rejected, the system offers an alternative time.")
    print(
        "For long tasks, the system can adapt to user preferences for splitting or completing in one go."
    )
    print(
        "The model now considers event categories from the backend app to make better recommendations."
    )


if __name__ == "__main__":
    main()
