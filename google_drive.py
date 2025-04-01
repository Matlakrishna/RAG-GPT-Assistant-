from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import os
import io

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    creds = None
    if os.path.exists('token_drive.json'):
        creds = Credentials.from_authorized_user_file('token_drive.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        try:
            creds = flow.run_local_server(port=9090, access_type='offline', prompt='consent')
        except TypeError:
            creds = flow.run_local_server(port=9090)
        with open('token_drive.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def list_files(service, query=""):
    try:
        results = service.files().list(q=query, pageSize=100, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

def download_file(service, file_id, file_name):
    try:
        file_metadata = service.files().get(fileId=file_id, fields="mimeType, name").execute()
        mime_type = file_metadata.get('mimeType')
        original_name = file_metadata['name']
        if mime_type in ['application/vnd.google-apps.document', 'application/vnd.google-apps.spreadsheet']:
            request = service.files().export(fileId=file_id, mimeType='application/pdf')
            file_name = f"downloaded_{original_name}.pdf"
        else:
            request = service.files().get_media(fileId=file_id)
            file_name = f"downloaded_{original_name}"
        fh = io.BytesIO(request.execute())
        return fh, file_name
    except Exception as e:
        return None, f"Download error: {str(e)}"

def preview_file(service, file_id):
    try:
        file_metadata = service.files().get(fileId=file_id, fields="mimeType, name, webViewLink").execute()
        mime_type = file_metadata.get('mimeType')
        if mime_type.startswith('text/'):
            request = service.files().get_media(fileId=file_id)
            content = request.execute().decode('utf-8')
            return content[:500] + "..." if len(content) > 500 else content
        elif mime_type == 'application/pdf':
            return f"PDF Preview: Open in browser at {file_metadata['webViewLink']}"
        elif mime_type.startswith('image/'):
            return f"Image Preview: Open in browser at {file_metadata['webViewLink']}"
        else:
            return f"Preview not available. Mime Type: {mime_type} - Open in browser at {file_metadata.get('webViewLink')}"
    except Exception as e:
        return f"Preview error: {str(e)}"

def upload_file(service, file):
    try:
        file_metadata = {"name": file.name}
        media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type)
        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_id = uploaded_file.get("id")
        return f"Uploaded successfully! [View File](https://drive.google.com/file/d/{file_id}/view)"
    except Exception as e:
        return f"Upload error: {str(e)}"