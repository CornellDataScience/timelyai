#!/usr/bin/env python3
"""
Event Categories for the Time Recommendation System

This module defines the event categories used in the time recommendation system,
mapping them to the categories from the backend app.
"""

# Main categories from the backend app
CATEGORIES = {
    "Clubs": {
        "description": "Club activities and extracurricular events",
        "event_types": ["club_meeting", "club_activity", "extracurricular"],
        "typical_duration": 1.5,  # hours
        "typical_urgency": "medium",
        "preferred_times": "afternoon",  # afternoon/evening
    },
    "Health & Fitness": {
        "description": "Health and fitness related activities",
        "event_types": ["workout", "exercise", "meditation", "yoga", "gym"],
        "typical_duration": 1.0,  # hours
        "typical_urgency": "low",
        "preferred_times": "morning",  # morning/evening
    },
    "Hobbies": {
        "description": "Personal hobbies and recreational activities",
        "event_types": ["hobby", "craft", "gaming", "music", "art"],
        "typical_duration": 2.0,  # hours
        "typical_urgency": "low",
        "preferred_times": "evening",  # evening/weekend
    },
    "Job": {
        "description": "Work-related activities",
        "event_types": ["work", "job_task", "work_meeting", "work_project"],
        "typical_duration": 2.0,  # hours
        "typical_urgency": "high",
        "preferred_times": "morning",  # morning/afternoon
    },
    "Other": {
        "description": "Miscellaneous activities",
        "event_types": ["other", "misc", "errand", "appointment"],
        "typical_duration": 1.0,  # hours
        "typical_urgency": "medium",
        "preferred_times": "flexible",  # flexible
    },
    "School": {
        "description": "Academic and educational activities",
        "event_types": ["hw", "study", "class", "exam", "project", "reading"],
        "typical_duration": 2.0,  # hours
        "typical_urgency": "high",
        "preferred_times": "afternoon",  # afternoon/evening
    },
    "Sleep": {
        "description": "Sleep and rest activities",
        "event_types": ["sleep", "nap", "rest", "relax"],
        "typical_duration": 8.0,  # hours
        "typical_urgency": "high",
        "preferred_times": "night",  # night
    },
    "Social": {
        "description": "Social activities and gatherings",
        "event_types": ["social", "meeting", "hangout", "party", "date"],
        "typical_duration": 2.0,  # hours
        "typical_urgency": "medium",
        "preferred_times": "evening",  # evening/weekend
    },
}

# Map of specific event types to their categories
EVENT_TYPE_TO_CATEGORY = {}
for category, info in CATEGORIES.items():
    for event_type in info["event_types"]:
        EVENT_TYPE_TO_CATEGORY[event_type] = category

# Default event types for each category (used when category is known but specific type is not)
DEFAULT_EVENT_TYPES = {
    "Clubs": "club_activity",
    "Health & Fitness": "workout",
    "Hobbies": "hobby",
    "Job": "work",
    "Other": "other",
    "School": "hw",
    "Sleep": "sleep",
    "Social": "social",
}


def get_category_for_event_type(event_type):
    """
    Get the category for a given event type.

    Args:
        event_type: The event type string

    Returns:
        The category name or None if not found
    """
    return EVENT_TYPE_TO_CATEGORY.get(event_type)


def get_default_event_type_for_category(category):
    """
    Get the default event type for a given category.

    Args:
        category: The category name

    Returns:
        The default event type or None if not found
    """
    return DEFAULT_EVENT_TYPES.get(category)


def get_all_event_types():
    """
    Get a list of all event types across all categories.

    Returns:
        A list of all event type strings
    """
    all_types = []
    for category_info in CATEGORIES.values():
        all_types.extend(category_info["event_types"])
    return all_types


def get_event_type_info(event_type):
    """
    Get information about a specific event type.

    Args:
        event_type: The event type string

    Returns:
        A dictionary with information about the event type or None if not found
    """
    category = get_category_for_event_type(event_type)
    if category:
        return {
            "category": category,
            "description": CATEGORIES[category]["description"],
            "typical_duration": CATEGORIES[category]["typical_duration"],
            "typical_urgency": CATEGORIES[category]["typical_urgency"],
            "preferred_times": CATEGORIES[category]["preferred_times"],
        }
    return None
