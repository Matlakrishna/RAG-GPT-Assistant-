import streamlit as st
import pandas as pd
from google_calendar import list_events, create_task, schedule_event, list_tasks, get_calendar_service, update_event, delete_event, TASK_IDENTIFIER
from google_drive import get_drive_service, upload_file, list_files, download_file
from llm_chat import generate_response, format_datetime
from rag_utils import add_document, search_documents  # ✅ Import RAG functions
from datetime import datetime, timedelta
import os

# ✅ Set Page Configuration
st.set_page_config(page_title="Personal Chatbot", layout="wide", initial_sidebar_state="expanded")

# ✅ Ensure Upload Directory Exists
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ✅ Initialize Session State
if "page" not in st.session_state:
    st.session_state.page = "Chat"  # Default to Chat

if "messages" not in st.session_state:
    st.session_state.messages = []

# ✅ Sidebar Navigation
with st.sidebar:
    st.markdown("""
        <style>
            .sidebar-title {
                font-size: 20px;
                font-weight: bold;
                text-align: center;
                padding: 10px 0;
                background-color: #1E1E1E;
                color: white;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            .sidebar-button {
                text-align: center;
                font-size: 16px;
                font-weight: 500;
            }
            .sidebar-line {
                margin: 15px 0;
                border: 0.5px solid #444;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-title">Navigation</div>', unsafe_allow_html=True)
    
    if st.button("Chat", key="chat_btn", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()

    if st.button("Dashboard", key="dashboard_btn", use_container_width=True):
        st.session_state.page = "Dashboard"
        st.rerun()

    st.markdown('<hr class="sidebar-line">', unsafe_allow_html=True)

    if st.button("Delete Chat History", key="clear_chat", use_container_width=True):
        st.session_state.messages = []
        st.success("Chat history cleared!")
        st.rerun()

# ✅ Load Google Services
drive_service = get_drive_service()
calendar_service = get_calendar_service()

try:
    events = list_events(calendar_service)
    tasks = list_tasks(calendar_service)
except Exception as e:
    st.error(f"Error fetching events or tasks: {e}")
    events, tasks = [], []

today = datetime.now().date()
todays_events = [event for event in events if event.get("start", {}).get("dateTime", "").startswith(str(today)) and not event.get("summary", "").startswith(TASK_IDENTIFIER)]
upcoming_events = [event for event in events if not event.get("start", {}).get("dateTime", "").startswith(str(today)) and not event.get("summary", "").startswith(TASK_IDENTIFIER)][:5]

# ✅ Chat Page
if st.session_state.page == "Chat":
    st.title("Chatbot")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Type a message..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            response = generate_response(prompt, drive_service, calendar_service)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ✅ Dashboard Page
elif st.session_state.page == "Dashboard":
    st.title("Dashboard")

    col1, col2, col3 = st.columns(3)

    # ✅ Task Management
    with col1:
        st.subheader("Task Management")
        for task in tasks:
            task_title = task.get("summary").replace(TASK_IDENTIFIER, "")
            due_date = format_datetime(task.get("start", {}).get("dateTime"))
            task_id = task.get("id")

            with st.expander(f"{task_title} (Due: {due_date})"):
                st.markdown(f"**Due:** {due_date}")

                if st.button(f"✅ Mark '{task_title}' as Complete", key=f"complete_{task_id}"):
                    try:
                        event = calendar_service.events().get(calendarId="primary", eventId=task_id).execute()
                        event["summary"] = f"✔️ {event['summary']} (Completed)"
                        updated_event = calendar_service.events().update(calendarId="primary", eventId=task_id, body=event).execute()

                        st.success(f"Task '{task_title}' marked as complete!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error: {e}")

    # ✅ Today's Events
    with col2:
        st.subheader("Today's Events")
        for event in todays_events:
            with st.expander(f"{event.get('summary')} at {format_datetime(event.get('start', {}).get('dateTime'))}"):
                st.markdown(f"**Description:** {event.get('description', 'No description')}")
                st.markdown(f"**Location:** {event.get('location', 'No location')}")

    # ✅ Upcoming Events
    with col3:
        st.subheader("Upcoming Events")
        for event in upcoming_events:
            event_summary = event.get("summary", "")

            if not event_summary.startswith("✔️") and not event_summary.startswith("[CHATBOT_TASK]"):
                with st.expander(f"{event_summary} at {format_datetime(event.get('start', {}).get('dateTime'))}"):
                    st.markdown(f"**Description:** {event.get('description', 'No description')}")
                    st.markdown(f"**Location:** {event.get('location', 'No location')}")

    # ✅ Quick Actions
    st.subheader("Quick Actions")

    with st.expander("➕ Create New Task"):
        task_title = st.text_input("Task Title")
        task_due_date = st.date_input("Due Date", min_value=today)
        task_due_time = st.time_input("Due Time")

        if st.button("✅ Add Task"):
            if task_title:
                due_datetime = datetime.combine(task_due_date, task_due_time).isoformat()
                create_task(calendar_service, task_title, due_datetime, "Medium", "")
                st.success("Task Created Successfully!")
                st.rerun()
            else:
                st.error("Task title is required!")

    with st.expander("📅 Schedule Event"):
        event_title = st.text_input("Event Title")
        event_date = st.date_input("Event Date", min_value=today)
        start_time = st.time_input("Start Time")
        end_time = st.time_input("End Time")
        event_description = st.text_area("Description")

        if st.button("📌 Schedule Event"):
            if event_title and end_time > start_time:
                start_datetime = datetime.combine(event_date, start_time).isoformat()
                end_datetime = datetime.combine(event_date, end_time).isoformat()
                schedule_event(calendar_service, event_title, start_datetime, end_datetime)
                st.success("Event Scheduled Successfully!")
                st.rerun()
            else:
                st.error("Please enter a valid event title and time.")

    with st.expander("📂 Upload File to Google Drive"):
        uploaded_file = st.file_uploader("Choose a file to upload")
        if uploaded_file and st.button("🚀 Upload Now"):
            upload_file(drive_service, uploaded_file)
            st.success("File Uploaded Successfully!")
            st.rerun()

    # ✅ FILE UPLOAD & RAG SEARCH
    UPLOADS_DIR = "uploads"
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

st.subheader("📂 Upload File for RAG-based Search")

uploaded_file = st.file_uploader("Upload a document for search", type=["pdf", "txt", "docx"])

if uploaded_file is not None:
    file_path = os.path.join(UPLOADS_DIR, uploaded_file.name)

    try:
        # ✅ Save the file properly
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # ✅ Confirm the file exists before processing
        if os.path.exists(file_path):
            st.success(f"File '{uploaded_file.name}' uploaded successfully!")

            # ✅ Debugging: Check stored path
            st.write("Debug: File path stored →", file_path)

            # ✅ Try adding document to RAG
            result = add_document(file_path)
            st.success(result)

        else:
            st.error("File saving failed. Please try again.")

    except Exception as e:
        st.error(f"Error saving file: {e}")

    st.write("Uploaded files in 'uploads' folder:", os.listdir("uploads"))

    st.write("Debug: File path stored →", file_path)
    st.write("Trying to add document to RAG...")
    result = add_document(file_path)
    st.write("RAG Response:", result)