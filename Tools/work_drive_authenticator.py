#!/usr/bin/env python3
"""
Google Drive Authenticator for Work Account (jeremy@kimbleconsultancy.com)

Comprehensive authentication script for Google Drive API.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def authenticate_work_drive():
    """
    Authenticate Google Drive for jeremy@kimbleconsultancy.com
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Drive service
    """
    # Scopes for Drive access
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    # Paths for credentials and token
    base_path = os.path.expanduser('~/Projects/Thanos/Tools')
    
    # Credential file paths to try
    credential_paths = [
        os.path.join(base_path, 'credentials_jeremy_kimbleconsultancy_com.json'),
        os.path.join(base_path, 'credentials_work.json'),
        os.path.join(base_path, 'credentials.json')
    ]
    
    # Token file paths to try
    token_paths = [
        os.path.join(base_path, 'token_jeremy_kimbleconsultancy_com.json'),
        os.path.join(base_path, 'token_work.json'),
        os.path.join(base_path, 'token.json')
    ]
    
    creds = None
    
    # Try to load existing token
    for token_path in token_paths:
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                
                # Refresh if expired
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                
                # Validate credentials
                if creds and creds.valid:
                    service = build('drive', 'v3', credentials=creds)
                    
                    # Quick test to ensure drive access
                    try:
                        service.files().list(pageSize=10, fields='files(id, name)').execute()
                        print(f"Successfully authenticated using {token_path}")
                        return service
                    except Exception as test_error:
                        print(f"Token test failed for {token_path}: {test_error}")
            except Exception as e:
                print(f"Error with token {token_path}: {e}")
    
    # If no existing token works, start new OAuth flow
    for cred_path in credential_paths:
        if os.path.exists(cred_path):
            try:
                # Run OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save new token
                new_token_path = os.path.join(base_path, 'token_jeremy_kimbleconsultancy_com.json')
                with open(new_token_path, 'w') as token:
                    token.write(creds.to_json())
                
                # Build service
                service = build('drive', 'v3', credentials=creds)
                print(f"Generated new token at {new_token_path}")
                return service
            
            except Exception as e:
                print(f"OAuth flow error with {cred_path}: {e}")
    
    raise ValueError("Unable to authenticate Google Drive for work account. Please set up credentials.")

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
        
        # List recent files
        list_drive_files(service)
    
    except Exception as e:
        print(f"Authentication failed: {e}")

if __name__ == '__main__':
    main()