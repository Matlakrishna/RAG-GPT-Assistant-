import google.generativeai as genai
import streamlit as st
import os
import string
import dateparser
import PyPDF2
import requests
from datetime import datetime, timedelta, timezone
import re
import html
import time
from google_drive import list_files, download_file, preview_file, get_drive_service
from google_calendar import list_events, create_task, list_tasks, schedule_event, get_calendar_service

# Initialize Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    raise ValueError("No GEMINI_API_KEY found!")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
last_request_time = 0

UPLOADS_DIR = "uploads"

def normalize_input(user_input):
    translator = str.maketrans('', '', string.punctuation)
    return user_input.translate(translator).lower()

def format_datetime(datetime_str):
    try:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except ValueError:
        return "Unknown Time"

def summarize_text(text):
    prompt = f"Summarize the following text concisely:\n\n{text}"
    try:
        summary = model.generate_content(prompt).text.strip()
        return summary
    except Exception as e:
        return f"Error summarizing text: {e}"

def generate_response(user_input, drive_service=None, calendar_service=None):
    global last_request_time
    normalized_input = normalize_input(user_input)
    words = normalized_input.split()

    # ---------------- RAG-Based File Search ----------------
    if "what files are available for search" in normalized_input:
        if not os.path.exists(UPLOADS_DIR):
            return "No files uploaded yet."

        files = os.listdir(UPLOADS_DIR)
        if not files:
            return "No files uploaded yet."

        return "**Available files for search:**\n" + "\n".join([f"- {file}" for file in files])

    # ---------------- Summarizing an Uploaded File ----------------
    elif "summarize" in words and "file" in words:
        query = " ".join(words[words.index("file") + 1:]).strip().lower()

        # ✅ Debugging: Print available files
        local_files = {f.lower().replace(".", "").replace(" ", ""): f for f in os.listdir(UPLOADS_DIR)}
        print(f"DEBUG: Available files for search → {list(local_files.keys())}")

        # ✅ Case-insensitive, punctuation-free matching
        target_file = local_files.get(query.replace(".", "").replace(" ", ""), None)

        if target_file:
            file_path = os.path.join(UPLOADS_DIR, target_file)
            content = ""

            # ✅ PDF Summarization
            if target_file.endswith(".pdf"):
                try:
                    with open(file_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                content += page_text + "\n"
                except Exception as ex:
                    return f"Error reading PDF: {str(ex)}"

            # ✅ TXT or DOCX Summarization
            elif target_file.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif target_file.endswith(".docx"):
                import docx
                doc = docx.Document(file_path)
                content = "\n".join([p.text for p in doc.paragraphs])

            else:
                return "File format not supported for summarization. Please use a PDF, TXT, or DOCX file."

            if not content.strip():
                return "No content available for summarization."

            summary = summarize_text(content)  # Uses LLM for summary
            return f"**Summary of '{target_file}'**:\n{summary}"

        return f"No file found matching '{query}'. Try checking the available files."




    # ---------------- Google Drive Features (Unchanged) ----------------
    elif drive_service and "list files" in normalized_input:
        try:
            limit_match = re.search(r"list files\s*[:\-]?\s*(\d+)", normalized_input)
            limit = int(limit_match.group(1)) if limit_match else None
            files = list_files(drive_service)
            if limit is not None:
                files = files[:limit]
            if files:
                file_list = "\n".join([f"{i+1}. {file.get('name', 'No Name')} (ID: {file.get('id', 'N/A')})"
                                        for i, file in enumerate(files)])
                return f"**Your Drive Files (showing {len(files)}):**\n{file_list}"
            return "No files found!"
        except Exception as e:
            return f"Drive error: {e}"

    # ---------------- Google Calendar Features (Unchanged) ----------------
    elif calendar_service and "list my upcoming events" in normalized_input:
        try:
            events = list_events(calendar_service)
            return "\n".join([f"- {e.get('summary', 'No Title')} at {format_datetime(e['start'].get('dateTime', ''))}" for e in events]) if events else "No upcoming events found!"
        except Exception as e:
            return f"Calendar error: {e}"

    elif calendar_service and "schedule event" in normalized_input:
        pattern = r"schedule event name\s*:\s*(.*?)\s*date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})\s*time\s*:\s*(\d{1,2}:\d{2}\s*(?:am|pm))"
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            event_name = match.group(1).strip()
            event_date = match.group(2).strip()
            event_time = match.group(3).strip()
            event_datetime_str = f"{event_date} {event_time}"
            event_datetime = dateparser.parse(event_datetime_str, settings={'DATE_ORDER': 'DMY'})
            if not event_datetime:
                return "Could not parse the date and time. Please check the format."
            response = schedule_event(calendar_service, event_name, event_datetime.isoformat(), (event_datetime + timedelta(hours=1)).isoformat())
            return response
        else:
            return "Invalid format. Please use: 'Schedule event name : <Event Name> date: <dd/mm/yyyy> time: <xx:yy AM/PM>'"

    # ---------------- Default LLM Chat Response ----------------
    if time.time() - last_request_time < 2:
        return "Hold on! Processing... 😅"

    last_request_time = time.time()
    try:
        prompt = f"You’re a chill, helpful buddy. Keep it simple and fun.\nUser: {user_input}"
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"LLM error: {e}"

# ---------------- Main Execution (Terminal Testing) ----------------
if __name__ == "__main__":
    drive_service = get_drive_service()
    calendar_service = get_calendar_service()

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = generate_response(user_input, drive_service, calendar_service)
        print("Chatbot:", response)
