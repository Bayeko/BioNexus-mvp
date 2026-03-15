#!/usr/bin/env python3
"""Upload BIONEXUS_BOX_ARCHITECTURE.docx to Google Drive using device-code OAuth.

Usage:
    python3 upload_to_drive.py

First run will prompt you to visit a URL and enter a code to authorize.
Credentials are cached in ~/.bionexus_drive_token.json for future use.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = Path.home() / ".bionexus_drive_token.json"
FILE_TO_UPLOAD = Path(__file__).parent / "BIONEXUS_BOX_ARCHITECTURE.docx"

# Minimal OAuth client config for a "Desktop" app.
# If you have your own Google Cloud project, replace client_id / client_secret.
# Otherwise, create one at https://console.cloud.google.com/apis/credentials
CLIENT_CONFIG = {
    "installed": {
        "client_id": "",
        "client_secret": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}


def get_credentials() -> Credentials:
    creds = None

    # Load cached token
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # Refresh or get new token
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CLIENT_CONFIG["installed"]["client_id"]:
            print(
                "\n"
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  Google Drive OAuth Setup Required                         ║\n"
                "╠══════════════════════════════════════════════════════════════╣\n"
                "║                                                            ║\n"
                "║  1. Go to: https://console.cloud.google.com/apis/credentials║\n"
                "║  2. Create an OAuth 2.0 Client ID (type: Desktop app)      ║\n"
                "║  3. Enable 'Google Drive API' in your project              ║\n"
                "║  4. Download the JSON credentials file                     ║\n"
                "║  5. Re-run this script:                                    ║\n"
                "║                                                            ║\n"
                "║     python3 upload_to_drive.py /path/to/credentials.json   ║\n"
                "║                                                            ║\n"
                "╚══════════════════════════════════════════════════════════════╝\n"
            )
            sys.exit(1)

        flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
        creds = flow.run_console()

    # Save for next time
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def get_credentials_from_file(creds_path: str) -> Credentials:
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_console()

    TOKEN_PATH.write_text(creds.to_json())
    return creds


def upload(creds: Credentials):
    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": "BioNexus Box — Hardware Gateway Architecture",
        "mimeType": "application/vnd.google-apps.document",  # Convert to Google Docs
    }

    media = MediaFileUpload(
        str(FILE_TO_UPLOAD),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        resumable=True,
    )

    print(f"\nUploading {FILE_TO_UPLOAD.name} to Google Drive...")
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
    ).execute()

    print(
        f"\n"
        f"  ✓ Uploaded successfully!\n"
        f"\n"
        f"  Name: {file['name']}\n"
        f"  Link: {file['webViewLink']}\n"
        f"\n"
        f"  The file has been converted to Google Docs format.\n"
        f"  Open the link above to view it.\n"
    )


def main():
    if len(sys.argv) > 1:
        creds_path = sys.argv[1]
        if not Path(creds_path).exists():
            print(f"Error: {creds_path} not found")
            sys.exit(1)
        creds = get_credentials_from_file(creds_path)
    else:
        creds = get_credentials()

    upload(creds)


if __name__ == "__main__":
    main()
