from datetime import datetime, time, timedelta, timezone
from dateutil.relativedelta import relativedelta
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
import pandas as pd
import pickle
import os.path





# Global default settings
DEFAULT_CALENDAR_ID = "primary"
DEFAULT_REMINDERS = {"useDefault": True}
DEFAULT_COLOR_ID = "1"  # Blue in Google Calendar
DEFAULT_MAX_RESULTS = 10
DEFAULT_EVENT_TRANSPARENCY = "opaque"  # opaque = blocks time, transparent = free
SCOPES = ["https://www.googleapis.com/auth/calendar"] #permissions
START_TIME = 7
END_TIME = 22


class GoogleCalendar:
    """A class to manage Google Calendar operations."""
    
    def __init__(self, credentials_path=None, token_path=None):
        """
        Initialize the GoogleCalendar class.
        
        Args:
            credentials_path: Path to the credentials.json file (default: looks in project root)
            token_path: Path to store/retrieve the token.json file (default: looks in project root)
        """
        self.timezone = timezone
        
        # Set up file paths
        if credentials_path is None or token_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            
            if token_path is None:
                token_path = os.path.join(project_root, "token.json")
            
            if credentials_path is None:
                credentials_path = os.path.join(project_root, "credentials.json")
        
        self.token_path = token_path
        self.credentials_path = credentials_path
        
        # Create the service
        self.service = self._create_service()

        #Timezones
        calendar_id = "primary"
        calendar = self.service.calendars().get(calendarId=calendar_id).execute()
        self.timezone = calendar['timeZone']
        self.tz = pytz.timezone(self.timezone)
    
    def _create_service(self):
        """
        Create and authenticate the Google Calendar service.
        
        Returns:
            Google Calendar API service instance
        """
        # Permissions
        
        
        # Authentication
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        
        # Return calendar service
        return build("calendar", "v3", credentials=creds)
    
    def create_event(self, summary, description, start_time, end_time, 
                    location=None, attendees=None, reminders=DEFAULT_REMINDERS, 
                    calendar_id=DEFAULT_CALENDAR_ID, color_id=DEFAULT_COLOR_ID, 
                    transparency=DEFAULT_EVENT_TRANSPARENCY, recurrence=None, 
                    all_day=False, additional_days=0, with_conference=False):
        """
        Unified function to create various types of calendar events.
        
        Args:
            summary: Title of the event
            description: Description of the event
            start_time: Start time as datetime object (for all_day=True, date portion is used)
            end_time: End time as datetime object (for all_day=True, can be None)
            location: Location of the event (optional)
            attendees: List of dictionaries with 'email' keys (optional)
            reminders: Dictionary with 'useDefault' and optional 'overrides' (optional)
            calendar_id: Calendar ID to add event to (default from global setting)
            color_id: ID of the color to use (default from global setting)
            transparency: Whether the event blocks time ("opaque") or not ("transparent")
            recurrence: List of recurrence rules (e.g. ['RRULE:FREQ=WEEKLY;COUNT=10']) (optional)
            all_day: Whether this is an all-day event (default False)
            additional_days: Number of additional days the all-day event lasts (default 0)
            with_conference: Whether to add a Google Meet conference link (default False)
            
        Returns:
            Created event object
        """
        # Create the basic event dictionary
        event = {
            'summary': summary,
            'description': description,
        }
        
        # Handle all-day events differently
        if all_day:
            # Convert datetime to date if needed
            if isinstance(start_time, datetime.datetime):
                start_date = start_time.date()
            else:
                start_date = start_time
            
            # Calculate end date (exclusive in Google Calendar)
            if end_time is None:
                end_date = start_date + datetime.timedelta(days=additional_days+1)
            elif isinstance(end_time, datetime.datetime):
                end_date = end_time.date()
            else:
                end_date = end_time
                
            # If no additional days specified but end_date is provided, ensure it's at least 1 day later
            if additional_days == 0 and end_date <= start_date:
                end_date = start_date + datetime.timedelta(days=1)
                
            event['start'] = {'date': start_date.isoformat()}
            event['end'] = {'date': end_date.isoformat()}
        else:
            # Regular event with specific times
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': self.timezone,
            }
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': self.timezone,
            }
        
        # Add optional fields if provided
        if location:
            event['location'] = location
            
        if attendees:
            event['attendees'] = attendees
            
        if reminders:
            event['reminders'] = reminders
            
        if color_id:
            event['colorId'] = color_id
            
        if transparency:
            event['transparency'] = transparency
            
        if recurrence:
            event['recurrence'] = recurrence
            
        if with_conference:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': f'sample-request-{datetime.datetime.now().timestamp()}'
                }
            }
        
        # Execute the API call, with conferenceDataVersion if needed
        if with_conference:
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event,
                conferenceDataVersion=1
            ).execute()
        else:
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
        
        # Construct an informative message
        event_type_str = "all-day " if all_day else ""
        if recurrence:
            event_type_str += "recurring "
        if with_conference:
            event_type_str += "conference "
        
        print(f'{event_type_str}Event created: {created_event.get("htmlLink")}')
        return created_event
    
    def update_event(self, event_id, updates, calendar_id=DEFAULT_CALENDAR_ID):
        """
        Update an existing event's details.
        
        Args:
            event_id: ID of the event to update
            updates: Dictionary of fields to update
            calendar_id: Calendar ID containing the event (default from global setting)
            
        Returns:
            Updated event object
        """
        # First, get the event
        event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Update fields
        for key, value in updates.items():
            event[key] = value
        
        updated_event = self.service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event).execute()
        
        print(f'Event updated: {updated_event["htmlLink"]}')
        return updated_event
    
    def delete_event(self, event_id, calendar_id=DEFAULT_CALENDAR_ID):
        """
        Delete an event from the calendar.
        
        Args:
            event_id: ID of the event to delete
            calendar_id: Calendar ID containing the event (default from global setting)
        """
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print(f'Event {event_id} deleted')
    
    def list_upcoming_events(self, max_results=DEFAULT_MAX_RESULTS, calendar_id=DEFAULT_CALENDAR_ID, 
                             time_min=None, order_by="startTime"):
        """
        List upcoming events.
        
        Args:
            max_results: Maximum number of events to return (default from global setting)
            calendar_id: Calendar ID to get events from (default from global setting)
            time_min: Datetime object for earliest time to include (default now)
            order_by: How to order results (default "startTime")
            
        Returns:
            List of event objects
        """
        if time_min is None:
            datetime.datetime.now(self.tz)
        
        time_min_utc = time_min.astimezone(pytz.UTC)
        time_min_str = time_min_utc.isoformat()
        
        events_result = self.service.events().list(
            calendarId=calendar_id, timeMin=time_min_str,
            maxResults=max_results, singleEvents=True,
            orderBy=order_by).execute()
        
        events = events_result.get('items', [])
    
        if not events:
            print('No upcoming events found.')
            return []
        
        print('Upcoming events:')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f'{start} - {event["summary"]}')
        
        return events
    
    def search_events(self, query, max_results=DEFAULT_MAX_RESULTS, calendar_id=DEFAULT_CALENDAR_ID, 
                     time_min=None, order_by="startTime"):
        """
        Search for events matching a specific query.
        
        Args:
            query: Search query string
            max_results: Maximum number of events to return (default from global setting)
            calendar_id: Calendar ID to search in (default from global setting)
            time_min: Datetime object for earliest time to include (default now)
            order_by: How to order results (default "startTime")
            
        Returns:
            List of matching event objects
        """
        if time_min is None:
            time_min = datetime.datetime.utcnow()
        
        time_min_str = time_min.isoformat() + 'Z'
        
        events_result = self.service.events().list(
            calendarId=calendar_id, timeMin=time_min_str,
            maxResults=max_results, singleEvents=True,
            orderBy=order_by, q=query).execute()
        
        events = events_result.get('items', [])
    
        if not events:
            print(f'No events matching "{query}" found.')
            return []
        
        print(f'Events matching "{query}":')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f'{start} - {event["summary"]}')
        
        return events
    
    def get_events_in_date_range(self, start_date, end_date, calendar_id=DEFAULT_CALENDAR_ID, order_by="startTime"):
        """
        Get events within a specific date range.
        
        Args:
            start_date: Datetime object for range start
            end_date: Datetime object for range end
            calendar_id: Calendar ID to get events from (default from global setting)
            order_by: How to order results (default "startTime")
            
        Returns:
            List of event objects in the date range
        """
        # Convert to ISO format with Z
        time_min = start_date.isoformat() + 'Z'
        time_max = end_date.isoformat() + 'Z'
        
        events_result = self.service.events().list(
            calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
            singleEvents=True, orderBy=order_by).execute()
        
        events = events_result.get('items', [])
    
        if not events:
            print(f'No events found between {start_date.date()} and {end_date.date()}.')
            return []
        
        print(f'Events between {start_date.date()} and {end_date.date()}:')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f'{start} - {event["summary"]}')
        
        return events
    
    def create_calendar(self, calendar_name):
        """
        Create a new calendar.
        
        Args:
            calendar_name: Name for the new calendar
            
        Returns:
            Created calendar object
        """
        calendar = {
            'summary': calendar_name,
            'timeZone': self.timezone
        }
        
        created_calendar = self.service.calendars().insert(body=calendar).execute()
        print(f'Calendar created: {created_calendar["id"]}')
        return created_calendar
    
    def list_calendars(self):
        """
        List all calendars that the user has access to.
        
        Returns:
            List of calendar objects
        """
        calendar_list = self.service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
    
        if not calendars:
            print('No calendars found.')
            return []
        
        print('Calendars:')
        for calendar in calendars:
            print(f'{calendar["summary"]} ({calendar["id"]})')
        
        return calendars
    
    def check_busy_times(self, calendar_ids, time_min, time_max):
        """
        Check when people are busy across multiple calendars.
        
        Args:
            calendar_ids: List of calendar IDs to check
            time_min: Start datetime for the period to check
            time_max: End datetime for the period to check
            
        Returns:
            Dictionary with free/busy information
        """
        body = {
            "timeMin": time_min.isoformat() + 'Z',
            "timeMax": time_max.isoformat() + 'Z',
            "items": [{"id": calendar_id} for calendar_id in calendar_ids]
        }
        
        free_busy_request = self.service.freebusy().query(body=body).execute()
        
        print("Busy periods:")
        for calendar_id, calendar_info in free_busy_request['calendars'].items():
            print(f"Calendar: {calendar_id}")
            if not calendar_info['busy']:
                print("  No busy times in this period")
            else:
                for busy_period in calendar_info['busy']:
                    print(f"  Busy from {busy_period['start']} to {busy_period['end']}")
        
        return free_busy_request
   
    def find_free_slots(self, calendar_ids, search_date, start_hour=9, end_hour=17, duration_minutes=30):
        """
        Find free time slots in a day across multiple calendars.
        Args:
            calendar_ids: List of calendar IDs to check
            search_date: Date to search for free slots
            start_hour: Beginning of workday hour (default 9)
            end_hour: End of workday hour (default 17)
            duration_minutes: Minimum duration in minutes for a free slot (default 30)
        Returns:
            List of tuples with start and end times for free slots
        """
        # Set timezone (adjust as needed)
        local_tz = pytz.timezone(self.timezone)


        # Create timezone-aware datetime objects for the day
        time_min = datetime.combine(search_date.date(), time(start_hour, 0)).replace(tzinfo=local_tz)
        time_max = datetime.combine(search_date.date(), time(end_hour, 0)).replace(tzinfo=local_tz)

        # Prepare request body for Google Calendar API
        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": calendar_id} for calendar_id in calendar_ids]
        }

        # Debugging: Print calendar IDs being checked
        print(f"Checking free slots across {len(calendar_ids)} calendars:")
        for cal_id in calendar_ids:
            print(f" - {cal_id}")

        # Call Google Calendar API to get busy periods
        free_busy_request = self.service.freebusy().query(body=body).execute()

        # Collect all busy periods from all calendars
        all_busy_periods = []
        for calendar_id, calendar_info in free_busy_request['calendars'].items():
            print(f"Found {len(calendar_info.get('busy', []))} busy periods in calendar {calendar_id}")
            for busy_period in calendar_info.get('busy', []):
                start = datetime.fromisoformat(busy_period['start']).astimezone(local_tz)
                end = datetime.fromisoformat(busy_period['end']).astimezone(local_tz)
                all_busy_periods.append((start, end))
                print(f" Busy: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")

        # Sort busy periods by start time
        all_busy_periods.sort(key=lambda x: x[0])

        # Merge overlapping or adjacent busy periods
        merged_busy_periods = []
        for period in all_busy_periods:
            if not merged_busy_periods or period[0] > merged_busy_periods[-1][1]:
                merged_busy_periods.append(period)
            else:
                merged_busy_periods[-1] = (merged_busy_periods[-1][0], max(merged_busy_periods[-1][1], period[1]))

        # Debugging: Print merged busy periods
        print("Merged busy periods:")
        for start, end in merged_busy_periods:
            print(f" Busy: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")

        # Find free slots between busy periods
        free_slots = []
        current_time = time_min

        for busy_start, busy_end in merged_busy_periods:
            if (busy_start - current_time).total_seconds() / 60 >= duration_minutes:
                free_slots.append((current_time, busy_start))
            current_time = max(current_time, busy_end)  # Ensure current_time moves forward

        # Check after the last busy period until the end of the workday
        if (time_max - current_time).total_seconds() / 60 >= duration_minutes:
            free_slots.append((current_time, time_max))

        # Debugging: Print free slots found
        print(f"Free {duration_minutes}-minute slots on {search_date.date()}:")
        for start, end in free_slots:
            max_duration_minutes = (end - start).total_seconds() / 60
            print(f" {start.strftime('%H:%M')} - {end.strftime('%H:%M')} ({max_duration_minutes:.0f} minutes available)")

        return free_slots

    def find_busy_slots(self, calendar_ids, search_date, start_hour=9, end_hour=17):
        """
        Find busy time slots in a day across multiple calendars.
        Args:
            calendar_ids: List of calendar IDs to check
            search_date: Date to search for busy slots
            start_hour: Beginning of workday hour (default 9)
            end_hour: End of workday hour (default 17)
        Returns:
            List of tuples with start and end times for busy slots
        """
        local_tz = pytz.timezone(self.timezone)

        # Create time range for the day
        time_min = datetime.combine(search_date.date(), time(start_hour, 0)).replace(tzinfo=local_tz)
        time_max = datetime.combine(search_date.date(), time(end_hour, 0)).replace(tzinfo=local_tz)

        # Prepare API request
        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": cal_id} for cal_id in calendar_ids]
        }

        # Get busy periods from Google Calendar API
        free_busy_request = self.service.freebusy().query(body=body).execute()

        # Collect and merge busy periods
        all_busy_periods = []
        for calendar_id, calendar_info in free_busy_request['calendars'].items():
            for busy_period in calendar_info.get('busy', []):
                start = datetime.fromisoformat(busy_period['start']).astimezone(local_tz)
                end = datetime.fromisoformat(busy_period['end']).astimezone(local_tz)
                all_busy_periods.append((start, end))

        # Sort and merge overlapping periods
        all_busy_periods.sort(key=lambda x: x[0])
        merged_busy = []
        for period in all_busy_periods:
            if not merged_busy or period[0] > merged_busy[-1][1]:
                merged_busy.append(period)
            else:
                merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], period[1]))

        # Filter to remove periods outside our time range
        filtered_busy = [
            (max(start, time_min), min(end, time_max))
            for start, end in merged_busy
            if start < time_max and end > time_min
        ]

        return filtered_busy

    def get_monthly_event_summary(self, year, month, calendar_id=DEFAULT_CALENDAR_ID):
        """
        Get a summary of events for a specific month.
        
        Args:
            year: Year to summarize
            month: Month to summarize (1-12)
            calendar_id: Calendar ID to analyze (default from global setting)
            
        Returns:
            Dictionary with event summary statistics
        """
        # First day of the month
        start_date = self.tz.localize(datetime.datetime(year, month, 1))
        # First day of next month
        if month == 12:
            end_date = datetime.datetime(year + 1, 1, 1)
        else:
            end_date = datetime.datetime(year, month + 1, 1)
        
        # Get events
        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime').execute()
        
        events = events_result.get('items', [])
        
        # Categorize events
        event_types = {}
        total_duration = datetime.timedelta()
        
        for event in events:
            # Skip events without a summary
            if 'summary' not in event:
                continue
                
            # Calculate duration for non-all-day events
            if 'dateTime' in event['start']:
                start = datetime.datetime.fromisoformat(event['start']['dateTime'].astimezone(self.tz).replace('Z', '+00:00'))
                end = datetime.datetime.fromisoformat(event['end']['dateTime'].astimezone(self.tz).replace('Z', '+00:00'))
                duration = end - start
                total_duration += duration
                
                # Categorize by first word
                category = event['summary'].split()[0] if event['summary'] else 'Untitled'
                
                if category in event_types:
                    event_types[category]['count'] += 1
                    event_types[category]['duration'] += duration
                else:
                    event_types[category] = {'count': 1, 'duration': duration}
        
        # Print summary
        month_name = start_date.strftime('%B')
        print(f"Event Summary for {month_name} {year}:")
        print(f"Total events: {len(events)}")
        print(f"Total duration: {total_duration.total_seconds() / 3600:.2f} hours")
        print("\nEvents by category:")
        
        for category, data in event_types.items():
            hours = data['duration'].total_seconds() / 3600
            print(f"  {category}: {data['count']} events, {hours:.2f} hours")
        
        return {
            'total_events': len(events),
            'total_duration': total_duration,
            'categories': event_types
        }

    def calendar_to_dataframe(self, calendar_ids, time_min=None, time_max=None, max_results=100):
        """
        Convert Google Calendar events to a pandas DataFrame with time distance from now.
        
        Args:
            time_min: Datetime object for earliest time to include (default: now)
            time_max: Datetime object for latest time to include (default: 30 days from now)
            max_results: Maximum number of events to return per calendar (default: 100)
            calendar_ids: String or list of calendar IDs to get events from (default: ["primary"])
        
        Returns:
            pandas DataFrame with calendar events from all specified calendars
        """
        
        # Handle calendar_ids parameter
        if calendar_ids is None:
            calendar_ids = ["primary"]
        elif isinstance(calendar_ids, str):
            calendar_ids = [calendar_ids]
        
        # Set default time ranges if not provided
        now = datetime.now(self.tz)
        if time_min is None:
            time_min = now
        if time_max is None:
            time_max = now + timedelta(days=30)
        
        # Convert datetime objects to ISO format strings
        time_min_str = time_min.isoformat()
        time_max_str = time_max.isoformat()
        
        # Create empty list to collect events from all calendars
        all_events = []
        
        # Process each calendar
        for calendar_id in calendar_ids:
            # Get events using existing service
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                # Add calendar_id to each event for tracking source
                for event in events:
                    event['calendar_id'] = calendar_id
                
                all_events.extend(events)
        
        if not all_events:
            print('No upcoming events found in any of the calendars.')
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'event_id', 'summary', 'description', 'location', 
                'start_time', 'end_time', 'all_day', 'duration_minutes',
                'time_until_event', 'days_until_event', 'hours_until_event',
                'creator', 'attendees_count', 'status', 'created', 'updated',
                'calendar_id', 'calendar_name'
            ])
        
        # Get calendar names for better readability
        calendar_names = {}
        for calendar_id in calendar_ids:
            try:
                calendar_info = self.service.calendars().get(calendarId=calendar_id).execute()
                calendar_names[calendar_id] = calendar_info.get('summary', calendar_id)
            except Exception as e:
                # If we can't get the name, just use the ID
                calendar_names[calendar_id] = calendar_id
        
        # Process events to extract relevant information
        event_data = []
        
        for event in all_events:
            # Handle different start/end time formats (dateTime vs date for all-day events)
            all_day = 'date' in event['start']
            
            if all_day:
                # All-day event
                start_time = datetime.fromisoformat(event['start']['date'])
                start_time = self.tz.localize(start_time)
                if 'end' in event and 'date' in event['end']:
                    end_time = datetime.fromisoformat(event['end']['date'])
                    end_time = self.tz.localize(end_time)
                else:
                    end_time = start_time + timedelta(days=1)
            else:
                # Timed event
                start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                
                # Convert to local timezone if needed
                if start_time.tzinfo != self.tz:
                    start_time = start_time.astimezone(self.tz)
                if end_time.tzinfo != self.tz:
                    end_time = end_time.astimezone(self.tz)
                    
            # Calculate duration in minutes
            duration = end_time - start_time
            duration_minutes = duration.total_seconds() / 60
            
            # Calculate time until event
            time_until_event = start_time - now
            days_until_event = time_until_event.days
            hours_until_event = time_until_event.total_seconds() / 3600
            
            # Get attendees count if available
            attendees_count = len(event.get('attendees', [])) if 'attendees' in event else 0
            
            # Get the calendar ID and name
            cal_id = event.get('calendar_id', 'primary')
            cal_name = calendar_names.get(cal_id, cal_id)
            
            # Append data
            event_data.append({
                'event_id': event.get('id', ''),
                'summary': event.get('summary', '(No title)'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start_time': start_time,
                'end_time': end_time,
                'all_day': all_day,
                'duration_minutes': duration_minutes,
                'time_until_event': time_until_event,
                'days_until_event': days_until_event,
                'hours_until_event': hours_until_event,
                'creator': event.get('creator', {}).get('email', '') if 'creator' in event else '',
                'attendees_count': attendees_count,
                'status': event.get('status', ''),
                'created': datetime.fromisoformat(event['created'].replace('Z', '+00:00')).astimezone(self.tz) if 'created' in event else None,
                'updated': datetime.fromisoformat(event['updated'].replace('Z', '+00:00')).astimezone(self.tz) if 'updated' in event else None,
                'calendar_id': cal_id,
                'calendar_name': cal_name
            })
        
        # Create DataFrame
        df = pd.DataFrame(event_data)
        
        # Sort by start time
        if not df.empty:
            df = df.sort_values('start_time')
        
        return df