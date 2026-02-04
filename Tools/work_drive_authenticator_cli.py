#!/usr/bin/env python3
"""
Command-Line Google Drive Authenticator for Work Account
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def authenticate_work_drive():
    """
    CLI-friendly Google Drive authentication
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Drive service
    """
    # Scopes for Drive access
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    # Paths for credentials and token
    base_path = os.path.expanduser('~/Projects/Thanos/Tools')
    credential_path = os.path.join(base_path, 'credentials_work.json')
    token_path = os.path.join(base_path, 'token_work.json')
    
    creds = None
    
    # Try to load existing token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            # Validate credentials
            if creds and creds.valid:
                service = build('drive', 'v3', credentials=creds)
                return service
        except Exception as e:
            print(f"Error with existing token: {e}")
    
    # Start new OAuth flow
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credential_path, SCOPES)
        
        # Use console-based authorization
        print("Please visit this URL to authorize the application:")
        print(flow.authorization_url()[0])
        
        authorization_code = input("Enter the authorization code: ")
        
        # Exchange authorization code for credentials
        flow.fetch_token(code=authorization_code)
        creds = flow.credentials
        
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        return service
    
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

def list_drive_files(service, max_files=10):
    """
    List files in Google Drive
    
    Args:
        service (googleapiclient.discovery.Resource): Authenticated Drive service
        max_files (int, optional): Maximum number of files to list
    
    Returns:
        list: List of files
    """
    try:
        results = service.files().list(
            pageSize=max_files, 
            fields="files(id, name, mimeType, createdTime)"
        ).execute()
        files = results.get('files', [])
        
        print("\nRecent Drive Files:")
        for file in files:
            print(f"- {file['name']} (ID: {file['id']}, Type: {file.get('mimeType', 'Unknown')})")
        
        return files
    
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

def main():
    try:
        # Authenticate
        service = authenticate_work_drive()
        
        if service:
            # List recent files
            list_drive_files(service)
        else:
            print("Authentication failed.")
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()