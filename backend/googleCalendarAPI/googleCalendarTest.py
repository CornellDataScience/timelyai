import datetime
from googleCalendarAPI import GoogleCalendar
import os

def main():

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Define paths relative to the project root
    token_path = os.path.join(project_root, "token.json")
    credentials_path = os.path.join(project_root, "credentials.json")


    # Initialize the calendar
    cal = GoogleCalendar(credentials_path, token_path)
    print("Google Calendar initialized\n")
    
    # Get today's date and time for examples
    now = datetime.datetime.now()
    today = now.date()

    # # Example 1: Create a regular meeting with custom reminder
    # meeting_start = now.replace(hour=14, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    # meeting_end = meeting_start + datetime.timedelta(hours=1)
    # meeting_reminder = {"useDefault": False, "overrides": [{"method": "popup", "minutes": 15}]}
    
    # print("Creating a team meeting for tomorrow...")
    # meeting = cal.create_event(
    #     summary="Team Sprint Planning",
    #     description="Weekly planning session for the project",
    #     start_time=meeting_start,
    #     end_time=meeting_end,
    #     location="Conference Room A",
    #     attendees=[
    #         {"email": "colleague1@example.com"},
    #         {"email": "colleague2@example.com"}
    #     ],
    #     reminders=meeting_reminder,
    #     with_conference=False 
    # )
    
    # # Example 2: Create an all-day event
    # allday_start = today + datetime.timedelta(days=5)
    
    # allday_event = cal.create_event(
    #     summary="Company Offsite",
    #     description="Annual team building event",
    #     start_time=allday_start,
    #     end_time=None,  # Not specified for all-day events
    #     all_day=True,
    #     additional_days=1,  # Make it a 2-day event
    #     color_id="11"  # Use a different color (red)
    # )
    
    # # Example 3: Create a deadline with early reminder
    # deadline_date = now.replace(hour=17, minute=0, second=0, microsecond=0) + datetime.timedelta(days=7)
    # deadline_reminder = {"useDefault": False, "overrides": [{"method": "popup", "minutes": 1440}]}  # 24 hours
    
    # print("\nCreating a project deadline...")
    # deadline = cal.create_event(
    #     summary="Project Milestone Deadline",
    #     description="Final submission of phase 1",
    #     start_time=deadline_date,
    #     end_time=deadline_date + datetime.timedelta(minutes=30),
    #     reminders=deadline_reminder,
    #     color_id="4"  # Use a different color (purple)
    # )
    
    # # Example 4: List upcoming events
    # print("\nListing your upcoming events...")
    # upcoming_events = cal.list_upcoming_events(max_results=5)
    
    # # Example 5: Search for events
    # print("\nSearching for team meetings...")
    # team_meetings = cal.search_events(query="Team", max_results=3)
    
    # Example 6: Find free slots

    calendar_ids = [calendar["id"] for calendar in cal.list_calendars()]

    next_monday = today + datetime.timedelta(days=(7 - today.weekday()))
    print(f"\nFinding free slots for next Monday ({next_monday})...")
    free_slots = cal.find_free_slots(
        calendar_ids=calendar_ids,
        search_date=datetime.datetime.combine(next_monday, datetime.time(0, 0)),
        start_hour=8,
        end_hour=22,
        duration_minutes=30
    )
    
    print("\nCalendar operations completed successfully!")

if __name__ == "__main__":
    main()