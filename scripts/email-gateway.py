#!/usr/bin/env python3
"""
Email Gateway for Thanos
Monitors jkimble1983+thanos@gmail.com and routes messages through OpenClaw.
"""

import subprocess
import json
import sys
import os
import re
import requests
from pathlib import Path
from datetime import datetime
from html import unescape

STATE_FILE = Path("/Users/jeremy/Projects/Thanos/memory/email-gateway-state.json")
ACCOUNT = "jkimble1983@gmail.com"
TARGET_ADDRESS = "jkimble1983+thanos@gmail.com"

# OpenClaw config
OPENCLAW_URL = os.environ.get("OPENCLAW_URL", "https://ashleys-macbook-air.taildf96dd.ts.net")
OPENCLAW_TOKEN = os.environ.get("OPENCLAW_TOKEN", "71d632f95e9c08ade4dfe00bd841a860f2025e98286827ef")

def run_gog(args: list) -> dict | None:
    """Run gog command and return JSON output."""
    cmd = ["gog", "gmail", "--account", ACCOUNT, "--json"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout.strip() else None
        else:
            print(f"gog error: {result.stderr}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error running gog: {e}", file=sys.stderr)
        return None

def load_state() -> dict:
    """Load processed message IDs."""
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        # Ensure processed_messages list exists
        if "processed_messages" not in state:
            state["processed_messages"] = []
        return state
    return {"processed": [], "processed_messages": [], "last_check": None}

def save_state(state: dict):
    """Save state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_check"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_unread_thanos_emails() -> list:
    """Get unread emails to +thanos address."""
    result = run_gog(["search", f"to:{TARGET_ADDRESS} is:unread", "--max", "10"])
    if not result or not result.get("threads"):
        return []
    return result["threads"]

def get_message_details(thread_id: str) -> dict | None:
    """Get full message details from a thread."""
    result = run_gog(["get", thread_id])
    return result

def extract_text_from_html(html: str) -> str:
    """Extract plain text from HTML email."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Unescape HTML entities
    text = unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def call_openclaw(message: str) -> str:
    """Send message to OpenClaw and get response."""
    try:
        response = requests.post(
            f"{OPENCLAW_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openclaw:main",
                "messages": [
                    {"role": "user", "content": f"[Email Gateway] {message}"}
                ]
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
    except Exception as e:
        return f"Error calling OpenClaw: {e}"

def send_reply(to: str, subject: str, body: str, thread_id: str = None, message_id: str = None):
    """Send reply email."""
    # Clean up the subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    
    cmd = [
        "gog", "gmail", "send",
        "--account", ACCOUNT,
        "--to", to,
        "--subject", subject,
        "--body", body
    ]
    if thread_id:
        cmd.extend(["--thread-id", thread_id])
    if message_id:
        cmd.extend(["--reply-to-message-id", message_id])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.returncode == 0

def mark_as_read(message_id: str):
    """Mark message as read."""
    # Use gog to modify labels if available, or just track in state
    cmd = ["gog", "gmail", "modify", message_id, "--remove-label", "UNREAD", "--account", ACCOUNT]
    subprocess.run(cmd, capture_output=True, text=True, timeout=30)

def download_attachment(message_id: str, attachment_id: str, filename: str) -> str | None:
    """Download an attachment and save to temp file."""
    import base64
    import tempfile
    
    cmd = ["gog", "gmail", "attachment", message_id, attachment_id, "--account", ACCOUNT, "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("data"):
                # Decode and save
                content = base64.urlsafe_b64decode(data["data"])
                ext = Path(filename).suffix or ".bin"
                tmp_path = Path(tempfile.gettempdir()) / f"email_attachment_{message_id[:8]}{ext}"
                tmp_path.write_bytes(content)
                return str(tmp_path)
    except Exception as e:
        print(f"Error downloading attachment: {e}", file=sys.stderr)
    return None

def main():
    state = load_state()
    threads = get_unread_thanos_emails()
    
    if not threads:
        print("No new Thanos emails")
        save_state(state)
        return
    
    for thread in threads:
        thread_id = thread.get("id")
        if not thread_id or thread_id in state["processed"]:
            continue
        
        # Get full thread details
        details = get_message_details(thread_id)
        if not details:
            print(f"Could not get details for thread {thread_id}")
            continue
        
        # Extract message content
        messages = details.get("messages", [details])
        if not messages:
            continue
        
        # Get the latest message (most recent in thread)
        latest = messages[-1] if isinstance(messages, list) else messages
        latest_id = latest.get("id", "")
        
        # Skip if we've already processed this specific message
        if latest_id in state.get("processed_messages", []):
            print(f"Already processed message {latest_id}, skipping")
            state["processed"].append(thread_id)
            continue
        
        # Extract headers
        headers = {h["name"].lower(): h["value"] for h in latest.get("payload", {}).get("headers", [])}
        from_addr = headers.get("from", "")
        subject = headers.get("subject", "No Subject")
        message_id = latest.get("id", thread_id)
        
        # Extract sender email
        email_match = re.search(r'<([^>]+)>', from_addr) or re.search(r'[\w\.-]+@[\w\.-]+', from_addr)
        sender_email = email_match.group(1) if email_match and email_match.lastindex else (email_match.group(0) if email_match else from_addr)
        
        # Extract body
        body = ""
        payload = latest.get("payload", {})
        
        # Try to get body from parts
        parts = payload.get("parts", [])
        if parts:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    import base64
                    body_data = part.get("body", {}).get("data", "")
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                        break
                elif part.get("mimeType") == "text/html":
                    import base64
                    body_data = part.get("body", {}).get("data", "")
                    if body_data:
                        html = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                        body = extract_text_from_html(html)
        
        # Fallback to snippet
        if not body:
            body = thread.get("snippet", "")
        
        print(f"\n📧 Processing email from {sender_email}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:200]}...")
        
        # Call OpenClaw
        print("   🤖 Calling Thanos...")
        response = call_openclaw(f"Subject: {subject}\n\nFrom: {sender_email}\n\n{body}")
        
        # Clean response (remove model prefix if present)
        response = re.sub(r'^\[H\]\s*|\[S\]\s*|\[O\]\s*', '', response).strip()
        
        print(f"   📤 Sending reply...")
        
        # Send reply
        success = send_reply(
            to=sender_email,
            subject=subject,
            body=response,
            thread_id=thread_id,
            message_id=message_id
        )
        
        if success:
            print(f"   ✅ Reply sent!")
            # Mark as read
            mark_as_read(message_id)
        else:
            print(f"   ❌ Failed to send reply")
        
        # Mark thread AND specific message as processed
        state["processed"].append(thread_id)
        state["processed_messages"].append(latest_id)
        
        # Keep only last 100 processed IDs
        state["processed"] = state["processed"][-100:]
        state["processed_messages"] = state["processed_messages"][-200:]
    
    save_state(state)
    print(f"\n✅ Processed {len([t for t in threads if t.get('id') not in state['processed']])} email(s)")

if __name__ == "__main__":
    main()
