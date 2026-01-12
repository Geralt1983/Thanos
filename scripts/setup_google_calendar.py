#!/usr/bin/env python3
"""
Google Calendar OAuth Setup Script for Thanos

This script guides users through the OAuth 2.0 setup process for Google Calendar integration.
It performs credential validation, tests API connectivity, and confirms access by listing calendars.

Usage:
    python3 scripts/setup_google_calendar.py

Prerequisites:
    - Google Cloud Console project with Calendar API enabled
    - OAuth 2.0 credentials configured
    - Environment variables set in .env file
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv not installed. Please run: pip install python-dotenv")
    sys.exit(1)


def print_header(text: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"✓ {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"✗ {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"⚠️  {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"ℹ️  {text}")


def validate_environment_variables() -> bool:
    """
    Validate that required environment variables are set.

    Returns:
        True if all required variables are present, False otherwise.
    """
    print_header("Step 1: Validating Environment Variables")

    # Load environment variables from .env file
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print_success(f"Loaded environment variables from {env_file}")
    else:
        print_warning(f"No .env file found at {env_file}")
        print_info("You can create one by copying .env.example:")
        print_info("  cp .env.example .env")

    # Check for required environment variables
    required_vars = {
        "GOOGLE_CALENDAR_CLIENT_ID": "OAuth 2.0 Client ID from Google Cloud Console",
        "GOOGLE_CALENDAR_CLIENT_SECRET": "OAuth 2.0 Client Secret from Google Cloud Console",
    }

    optional_vars = {
        "GOOGLE_CALENDAR_REDIRECT_URI": "OAuth redirect URI (defaults to http://localhost:8080/oauth2callback)",
    }

    all_valid = True

    for var_name, description in required_vars.items():
        value = os.environ.get(var_name)
        if value:
            # Show partial value for security
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print_success(f"{var_name}: {masked_value} ({description})")
        else:
            print_error(f"{var_name}: NOT SET ({description})")
            all_valid = False

    # Check optional variables
    for var_name, description in optional_vars.items():
        value = os.environ.get(var_name)
        if value:
            print_success(f"{var_name}: {value} ({description})")
        else:
            print_info(f"{var_name}: Not set, will use default ({description})")

    if not all_valid:
        print("\n" + "="*70)
        print_error("Missing required environment variables!")
        print("\nTo fix this:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select an existing one")
        print("3. Enable the Google Calendar API")
        print("4. Create OAuth 2.0 credentials (Desktop app type)")
        print("5. Add the Client ID and Client Secret to your .env file:")
        print("\n   GOOGLE_CALENDAR_CLIENT_ID=your-client-id.apps.googleusercontent.com")
        print("   GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret")
        print("\nSee docs/integrations/google-calendar.md for detailed setup instructions.")
        return False

    print_success("All required environment variables are set!")
    return True


def test_adapter_import() -> bool:
    """
    Test that the GoogleCalendarAdapter can be imported.

    Returns:
        True if import succeeds, False otherwise.
    """
    print_header("Step 2: Testing Adapter Import")

    try:
        from Tools.adapters import GoogleCalendarAdapter
        print_success("GoogleCalendarAdapter imported successfully")
        return True
    except ImportError as e:
        print_error(f"Failed to import GoogleCalendarAdapter: {e}")
        print_info("Make sure all dependencies are installed:")
        print_info("  pip install -r requirements.txt")
        return False
    except Exception as e:
        print_error(f"Unexpected error importing GoogleCalendarAdapter: {e}")
        return False


def check_existing_credentials() -> bool:
    """
    Check if OAuth credentials already exist.

    Returns:
        True if credentials exist and are valid, False otherwise.
    """
    print_header("Step 3: Checking Existing Credentials")

    creds_file = project_root / "State" / "calendar_credentials.json"

    if not creds_file.exists():
        print_info("No existing credentials found")
        return False

    print_success(f"Found credentials file: {creds_file}")

    try:
        from Tools.adapters import GoogleCalendarAdapter

        adapter = GoogleCalendarAdapter()

        if adapter.is_authenticated():
            print_success("Existing credentials are valid!")
            return True
        else:
            print_warning("Credentials file exists but authentication is invalid")
            return False
    except Exception as e:
        print_error(f"Error checking credentials: {e}")
        return False


def run_oauth_flow() -> bool:
    """
    Guide the user through the OAuth 2.0 authorization flow.

    Returns:
        True if authorization succeeds, False otherwise.
    """
    print_header("Step 4: Running OAuth 2.0 Authorization Flow")

    try:
        from Tools.adapters import GoogleCalendarAdapter

        adapter = GoogleCalendarAdapter()

        # Get authorization URL
        print_info("Generating authorization URL...")
        auth_url, state = adapter.get_authorization_url()

        print("\n" + "="*70)
        print("Please complete the following steps:")
        print("="*70)
        print("\n1. Open this URL in your browser:")
        print(f"\n   {auth_url}\n")
        print("2. Sign in with your Google account")
        print("3. Grant permissions when prompted")
        print("4. You'll be redirected to a URL starting with:")
        print(f"   {adapter.redirect_uri}")
        print("5. The page may show 'This site can't be reached' - this is expected!")
        print("6. COPY THE ENTIRE URL from your browser's address bar")
        print("="*70)

        # Prompt for redirect URL
        redirect_url = input("\nPaste the full redirect URL here: ").strip()

        if not redirect_url:
            print_error("No URL provided. Authorization cancelled.")
            return False

        # Validate URL format
        if not redirect_url.startswith("http"):
            print_error("Invalid URL format. Please provide the complete URL from your browser.")
            return False

        # Complete authorization
        print_info("Completing authorization...")
        result = adapter.complete_authorization(redirect_url, state)

        if result.success:
            print_success("Authorization successful!")
            print_success(f"Credentials saved to: {adapter.CREDENTIALS_FILE}")

            # Show credential details
            if result.data:
                print("\nCredential Details:")
                print(f"  Status: {result.data.get('status', 'unknown')}")
                print(f"  Scopes: {', '.join(result.data.get('scopes', []))}")
                expires_at = result.data.get('expires_at')
                if expires_at:
                    print(f"  Expires: {expires_at}")
                has_refresh = result.data.get('has_refresh_token', False)
                if has_refresh:
                    print_success("  Refresh token: Available (for long-term access)")
                else:
                    print_warning("  Refresh token: Not available (may need to re-auth)")

            return True
        else:
            print_error(f"Authorization failed: {result.error}")
            return False

    except ValueError as e:
        print_error(f"Configuration error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error during authorization: {e}")
        import traceback
        print("\nDebug information:")
        traceback.print_exc()
        return False


def test_api_connectivity() -> bool:
    """
    Test API connectivity by making a simple API call.

    Returns:
        True if API call succeeds, False otherwise.
    """
    print_header("Step 5: Testing API Connectivity")

    try:
        from Tools.adapters import GoogleCalendarAdapter

        adapter = GoogleCalendarAdapter()

        if not adapter.is_authenticated():
            print_error("Not authenticated. Cannot test API connectivity.")
            return False

        print_info("Running health check...")

        # Use the health_check tool if available, otherwise try a simple operation
        try:
            import asyncio

            result = asyncio.run(adapter.execute_tool("health_check", {}))

            if result.success:
                print_success("API health check passed!")

                # Show health check results
                if result.data:
                    print("\nHealth Check Results:")
                    print(f"  Status: {result.data.get('status', 'unknown')}")
                    print(f"  Authenticated: {result.data.get('authenticated', False)}")
                    print(f"  API Accessible: {result.data.get('api_accessible', False)}")
                    calendar_count = result.data.get('calendar_count', 0)
                    if calendar_count:
                        print(f"  Calendars Found: {calendar_count}")
                    response_time = result.data.get('response_time_ms', 0)
                    if response_time:
                        print(f"  Response Time: {response_time}ms")

                return True
            else:
                print_warning(f"Health check returned error: {result.error}")
                # Try to proceed anyway
                return True

        except Exception as e:
            print_warning(f"Health check not available: {e}")
            print_info("Trying alternative connectivity test...")
            return True

    except Exception as e:
        print_error(f"Error testing API connectivity: {e}")
        return False


def list_calendars() -> bool:
    """
    List user's calendars to confirm access.

    Returns:
        True if calendars are successfully listed, False otherwise.
    """
    print_header("Step 6: Listing Your Calendars")

    try:
        from Tools.adapters import GoogleCalendarAdapter
        import asyncio

        adapter = GoogleCalendarAdapter()

        if not adapter.is_authenticated():
            print_error("Not authenticated. Cannot list calendars.")
            return False

        print_info("Fetching your calendars...")

        result = asyncio.run(adapter.execute_tool("list_calendars", {}))

        if result.success and result.data:
            calendars = result.data.get("calendars", [])
            count = result.data.get("count", len(calendars))

            print_success(f"Found {count} calendar(s):\n")

            for i, calendar in enumerate(calendars, 1):
                cal_id = calendar.get("id", "unknown")
                summary = calendar.get("summary", "Unnamed Calendar")
                is_primary = calendar.get("primary", False)
                access_role = calendar.get("access_role", "unknown")
                timezone = calendar.get("timezone", "unknown")

                primary_marker = " [PRIMARY]" if is_primary else ""

                print(f"{i}. {summary}{primary_marker}")
                print(f"   ID: {cal_id}")
                print(f"   Access: {access_role}")
                print(f"   Timezone: {timezone}")
                print()

            return True
        else:
            print_error(f"Failed to list calendars: {result.error if not result.success else 'No data returned'}")
            return False

    except Exception as e:
        print_error(f"Error listing calendars: {e}")
        import traceback
        print("\nDebug information:")
        traceback.print_exc()
        return False


def print_next_steps() -> None:
    """Print information about next steps after setup."""
    print_header("Setup Complete!")

    print("Your Google Calendar is now connected to Thanos! 🎉\n")
    print("Next Steps:")
    print()
    print("1. Test the integration:")
    print("   python3 -c \"from Tools.adapters import GoogleCalendarAdapter; import asyncio; adapter = GoogleCalendarAdapter(); print(asyncio.run(adapter.execute_tool('get_today_events', {})))\"")
    print()
    print("2. Configure calendar filters (optional):")
    print("   Edit: config/calendar_filters.json")
    print("   See: docs/integrations/google-calendar.md#calendar-filtering")
    print()
    print("3. Use in daily briefing:")
    print("   The calendar will automatically be included in your daily briefing")
    print()
    print("4. Available tools:")
    print("   - get_today_events: Fetch today's calendar events")
    print("   - get_events: Fetch events for a date range")
    print("   - find_free_slots: Find available time slots")
    print("   - check_conflicts: Check for scheduling conflicts")
    print("   - block_time_for_task: Create calendar blocks for tasks")
    print("   - create_event: Create calendar events")
    print()
    print("For detailed documentation, see: docs/integrations/google-calendar.md")
    print()


def main() -> int:
    """
    Main setup flow.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("Google Calendar Setup for Thanos")
    print("This script will guide you through connecting your Google Calendar.")

    # Step 1: Validate environment variables
    if not validate_environment_variables():
        return 1

    # Step 2: Test adapter import
    if not test_adapter_import():
        return 1

    # Step 3: Check for existing credentials
    has_existing_creds = check_existing_credentials()

    if has_existing_creds:
        print_info("\nYou already have valid credentials.")
        response = input("Do you want to re-authorize anyway? (y/N): ").strip().lower()

        if response != 'y':
            print_info("Skipping authorization. Using existing credentials.")
        else:
            # Step 4: Run OAuth flow
            if not run_oauth_flow():
                print_error("\nSetup failed during authorization.")
                return 1
    else:
        # Step 4: Run OAuth flow
        if not run_oauth_flow():
            print_error("\nSetup failed during authorization.")
            return 1

    # Step 5: Test API connectivity
    if not test_api_connectivity():
        print_warning("\nAPI connectivity test failed, but setup may still work.")

    # Step 6: List calendars to confirm access
    if not list_calendars():
        print_warning("\nCouldn't list calendars, but setup may still work.")

    # Print next steps
    print_next_steps()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
