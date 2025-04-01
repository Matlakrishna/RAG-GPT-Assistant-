from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth
from datetime import datetime, timedelta, timezone
import os
import pytz
from dateutil import parser
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']
TIMEZONE = 'Asia/Kolkata'
TASK_IDENTIFIER = "[CHATBOT_TASK]"

def get_calendar_service():
    creds = None
    if os.path.exists('token_calendar.json'):
        creds = Credentials.from_authorized_user_file('token_calendar.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            try:
                creds = flow.run_local_server(port=9090)
            except TypeError:
                creds = flow.run_local_server(port=9090)
        with open('token_calendar.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def create_task(service, task_title, due_date=None, priority=None, categories=None):
    try:
        print(f"Creating task: {task_title}, due: {due_date}") #Debug
        if due_date:
            due_datetime = datetime.fromisoformat(due_date).astimezone(timezone.utc)
        else:
            due_datetime = datetime.now(timezone.utc)
        event_body = {
            'summary': f"{TASK_IDENTIFIER} {task_title}",
            'start': {'dateTime': due_datetime.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': (due_datetime + timedelta(hours=1)).isoformat(), 'timeZone': 'UTC'},
            'description': f'Task created from chatbot. Priority: {priority or "None"}, Categories: {categories or "None"}'
        }
        print(f"Event body: {event_body}") #Debug
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        print(f"Task created: {event}") #Debug
        return f"Task '{task_title}' added successfully!"
    except HttpError as e:
        print(f"HTTP Error adding task: {e.content}")
        return f"Error adding task: {str(e)}"
    except Exception as e:
        print(f"Error adding task: {e}") #Debug
        return f"Error adding task: {str(e)}"

def list_tasks(service):
    try:
        events = list_events(service)
        tasks = [event for event in events if event.get('summary', '').startswith(TASK_IDENTIFIER)]
        return tasks
    except Exception as e:
        print(f"Error fetching tasks: {str(e)}")
        return []

def list_events(service, date_str=None):
    try:
        events_result = service.events().list(calendarId='primary',
                                              timeMin=datetime.utcnow().isoformat() + 'Z',
                                              maxResults=250,
                                              singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return []

        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                filtered_events = []
                local_timezone = pytz.timezone(TIMEZONE)
                for event in events:
                    start = event.get('start', {}).get('dateTime')
                    if start:
                        try:
                            event_datetime = parser.parse(start)
                            event_datetime_local = event_datetime.astimezone(local_timezone)
                            event_date = event_datetime_local.date()
                            if event_date == target_date:
                                filtered_events.append(event)
                        except ValueError:
                            # Handle invalid datetime strings
                            pass
                return filtered_events
            except ValueError as ve:
                print(f"Date parsing error: {ve}")
                return []
            except IndexError as ie:
                print(f"Index error: {ie}")
                return []
        else:
            return events

    except Exception as e:
        print(f"Calendar error: {e}")
        return []

def schedule_event(service, event_name, event_start, event_end):
    try:
        print(f"Scheduling event: {event_name}, start: {event_start}, end: {event_end}") #Debug
        start_datetime = datetime.fromisoformat(event_start).astimezone(timezone.utc)
        end_datetime = datetime.fromisoformat(event_end).astimezone(timezone.utc)
        event_body = {
            'summary': event_name,
            'start': {'dateTime': start_datetime.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end_datetime.isoformat(), 'timeZone': 'UTC'},
            'description': 'Event scheduled from chatbot'
        }
        print(f"Event body: {event_body}") #Debug
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        print(f"Event scheduled: {event}") #Debug

        return f"Event '{event_name}' scheduled successfully on {start_datetime.astimezone(pytz.timezone(TIMEZONE)).strftime('%d-%m-%Y %I:%M %p')}!"
    except HttpError as e:
        print(f"HTTP Error scheduling event: {e.content}")
        return f"Error scheduling event: {str(e)}"
    except Exception as e:
        print(f"Error scheduling event: {e}")
        return f"Error scheduling event: {e}"

def update_event(service, event_id, updated_event):
    try:
        print(f"Updating event: {event_id}, update: {updated_event}") #Debug
        updated_event = service.events().update(calendarId='primary', eventId=event_id, body=updated_event).execute()
        print(f"Event updated: {updated_event}") #Debug
        return updated_event
    except HttpError as e:
        print(f"HTTP Error updating event: {e.content}")
        return None
    except Exception as e:
        print(f"Error updating event: {str(e)}")
        return None

def delete_event(service, event_id):
    try:
        print(f"Deleting event: {event_id}") #Debug
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        print(f"Event deleted: {event_id}") #Debug
        return True
    except HttpError as e:
        print(f"HTTP Error deleting event: {e.content}")
        return False
    except Exception as e:
        print(f"Error deleting event: {str(e)}")
        return False

# Testing function
def test_calendar_functions():
    service = get_calendar_service()

    # Test create_task
    task_result = create_task(service, "Test Task from Terminal", datetime.now().isoformat())
    print(f"Task creation: {task_result}")

    # Test schedule_event
    future_time = datetime.now(pytz.timezone(TIMEZONE)) + timedelta(hours=1)
    future_time_plus_one_hour = future_time + timedelta(hours=1)
    event_result = schedule_event(service, "Test Event from Terminal", future_time.isoformat(), future_time_plus_one_hour.isoformat())
    print(f"Event creation : {event_result}")

    # Test list_tasks
    tasks = list_tasks(service)
    print(f"Tasks: {tasks}")

    # Test list_events
    events = list_events(service)
    print(f"Events: {events}")

    # Test Delete event
    if events:
        if len(events)>0:
            delete_result = delete_event(service, events[0].get('id'))
            print(f"Event deletion : {delete_result}")

if __name__ == "__main__":
    test_calendar_functions()