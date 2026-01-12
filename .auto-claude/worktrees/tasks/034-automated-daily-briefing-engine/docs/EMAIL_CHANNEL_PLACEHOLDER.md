# EmailChannel - Future Email Delivery Integration

## Overview

The `EmailChannel` class is a **placeholder** for future email delivery functionality. It provides the structure and configuration schema needed to integrate email delivery of briefings, but the actual email sending functionality is not yet implemented.

## Status

🚧 **NOT IMPLEMENTED** - This is a placeholder for future development.

Attempting to use the EmailChannel will raise a `NotImplementedError` with a helpful message explaining that this feature is planned but not yet available.

## Purpose

This placeholder serves several important purposes:

1. **Configuration Schema**: Defines the expected configuration structure for email delivery
2. **API Contract**: Establishes the interface that future implementations must follow
3. **Documentation**: Provides clear guidance for developers who will implement this feature
4. **User Awareness**: Makes users aware that email delivery is planned but not available

## Configuration Structure

The EmailChannel supports the following configuration in `config/briefing_schedule.json`:

```json
{
  "delivery": {
    "email": {
      "enabled": false,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "use_tls": true,
      "from_address": "briefings@example.com",
      "to_address": "user@example.com",
      "subject_pattern": "{type} Briefing - {date}",
      "format": "html",
      "service": "smtp"
    }
  }
}
```

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable email delivery (must be false until implemented) |
| `smtp_server` | string | `"smtp.gmail.com"` | SMTP server hostname |
| `smtp_port` | integer | `587` | SMTP server port |
| `use_tls` | boolean | `true` | Use TLS encryption for SMTP |
| `from_address` | string | `""` | Email address to send from |
| `to_address` | string | `""` | Email address to send to |
| `subject_pattern` | string | `"{type} Briefing - {date}"` | Email subject template |
| `format` | string | `"html"` | Email format: 'html' or 'text' |
| `service` | string | `"smtp"` | Email service: 'smtp', 'sendgrid', 'mailgun', 'ses' |

## Planned Features

When implemented, the EmailChannel will support:

### Core Features
- ✉️ **SMTP Integration**: Direct SMTP server support via Python's `smtplib`
- 🔐 **Authentication**: Username/password and OAuth authentication
- 🔒 **TLS/SSL**: Secure email transmission
- 📧 **Multiple Recipients**: Support for to, cc, and bcc fields

### Email Service APIs
- **SendGrid**: API-based email delivery
- **Mailgun**: API-based email delivery
- **AWS SES**: Amazon Simple Email Service integration
- **Custom SMTP**: Support for any SMTP server

### Email Formatting
- 📝 **HTML Emails**: Rich formatting with CSS styling
- 📄 **Plain Text**: Simple text-only emails
- 🎨 **Templates**: Customizable email templates
- 📎 **Attachments**: Optional PDF/markdown attachments

### Advanced Features
- 👥 **Multiple Recipients**: Send to multiple addresses
- 📋 **CC/BCC Support**: Carbon copy and blind carbon copy
- 🔄 **Retry Logic**: Handle temporary failures gracefully
- 📊 **Delivery Tracking**: Log email delivery status

## Implementation Guide

For developers implementing this feature:

### Step 1: Choose Email Backend

**Option A: SMTP (smtplib)**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def deliver(self, content, briefing_type, metadata=None):
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = self.subject_pattern.format(
        type=briefing_type,
        date=metadata.get('date', datetime.now().strftime('%Y-%m-%d'))
    )
    msg['From'] = self.from_address
    msg['To'] = self.to_address

    # Attach content
    if self.email_format == 'html':
        html_content = self._convert_markdown_to_html(content)
        msg.attach(MIMEText(html_content, 'html'))
    else:
        msg.attach(MIMEText(content, 'plain'))

    # Send via SMTP
    with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
        if self.config.get('use_tls', True):
            server.starttls()
        server.login(username, password)
        server.send_message(msg)

    return True
```

**Option B: SendGrid API**
```python
import sendgrid
from sendgrid.helpers.mail import Mail

def deliver(self, content, briefing_type, metadata=None):
    sg = sendgrid.SendGridAPIClient(api_key=self.config['api_key'])

    message = Mail(
        from_email=self.from_address,
        to_emails=self.to_address,
        subject=self.subject_pattern.format(type=briefing_type, date='...'),
        html_content=self._convert_markdown_to_html(content)
    )

    response = sg.send(message)
    return response.status_code == 202
```

### Step 2: Add Markdown to HTML Conversion

Use a library like `markdown` or `mistune`:

```python
import markdown

def _convert_markdown_to_html(self, content):
    """Convert markdown briefing to HTML email."""
    html = markdown.markdown(content, extensions=['tables', 'fenced_code'])

    # Wrap in email template with styling
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
            h2 {{ color: #34495e; }}
            ul {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """
```

### Step 3: Handle Authentication

```python
def _get_credentials(self):
    """Get email credentials securely."""
    # Option 1: Environment variables (recommended)
    import os
    username = os.getenv('EMAIL_USERNAME') or self.config.get('username')
    password = os.getenv('EMAIL_PASSWORD') or self.config.get('password')

    # Option 2: OAuth token (for Gmail/Outlook)
    if self.config.get('use_oauth'):
        token = self._get_oauth_token()
        return token

    return username, password
```

### Step 4: Add Error Handling

```python
def deliver(self, content, briefing_type, metadata=None):
    try:
        # Send email logic here
        self.log_delivery(briefing_type, True, f"Sent to {self.to_address}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        self.log_delivery(briefing_type, False, f"Authentication failed: {e}")
        return False
    except smtplib.SMTPException as e:
        self.log_delivery(briefing_type, False, f"SMTP error: {e}")
        return False
    except Exception as e:
        self.log_delivery(briefing_type, False, f"Unexpected error: {e}")
        return False
```

### Step 5: Update Tests

Remove the `test_deliver_raises_not_implemented` test and add real delivery tests:

```python
@patch('smtplib.SMTP')
def test_deliver_success(self, mock_smtp):
    """Test successful email delivery."""
    channel = EmailChannel(config=self.config)
    result = channel.deliver(self.test_content, self.test_type)

    self.assertTrue(result)
    mock_smtp.assert_called_once()
```

### Step 6: Update Configuration Schema

Add validation for email addresses and server settings in `config/briefing_schedule.schema.json`.

## Security Considerations

When implementing email delivery:

1. **Never Store Passwords in Config**: Use environment variables or secure credential storage
2. **Use TLS/SSL**: Always encrypt email transmission
3. **Validate Email Addresses**: Prevent email injection attacks
4. **Rate Limiting**: Prevent sending too many emails
5. **OAuth When Possible**: Prefer OAuth over password authentication
6. **Sensitive Content**: Consider what information is sent via email

## Testing Email Integration

### Local Testing with MailHog

Use [MailHog](https://github.com/mailhog/MailHog) for local email testing:

```bash
# Install and run MailHog
brew install mailhog  # macOS
mailhog

# Configure briefing to use MailHog
# SMTP server: localhost
# SMTP port: 1025
# Web UI: http://localhost:8025
```

### Testing with Real Services

- **Gmail**: Requires app-specific password or OAuth
- **SendGrid**: Free tier available for testing
- **Mailgun**: Free sandbox for testing

## Current Usage

Since the EmailChannel is not implemented, attempting to use it will fail:

```python
from Tools.delivery_channels import EmailChannel

channel = EmailChannel(config={'from_address': 'test@example.com'})
channel.deliver("Test content", "morning")  # Raises NotImplementedError
```

**Error message:**
```
NotImplementedError: EmailChannel is not yet implemented. This is a placeholder
for future email delivery integration. To implement, add email sending logic
using smtplib or an email service API. See the class docstring for planned
features and configuration structure.
```

## Timeline

This feature is planned for future development. Priority will depend on:
- User demand for email delivery
- Availability of developer resources
- Security review completion
- Integration testing requirements

## Alternatives

Until email delivery is implemented, users can:

1. **File Delivery**: Use FileChannel to save briefings to disk
2. **CLI Output**: Use CLIChannel to print briefings to terminal
3. **State Sync**: Use StateSyncChannel to update State/Today.md
4. **Notifications**: Use NotificationChannel for desktop alerts
5. **Manual Email**: Copy file output and email manually

## Related Documentation

- [Delivery Channels Guide](./DELIVERY_CHANNELS.md)
- [State Sync Channel](./STATE_SYNC_CHANNEL.md)
- [Briefing Configuration](../config/README.md)

## Questions?

For questions about email delivery implementation or to express interest in this feature, please open an issue on the project repository.
