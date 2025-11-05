# Email Notifications Setup Guide

## Overview

This feature implements email notifications for when users make changes to travel plans and important dates. All members of a travel group are notified when:
- Trip preferences are updated
- A new itinerary is added to the group
- An existing itinerary is updated

## Requirements

The notification system requires the following packages (already added to `requirements.txt`):
- `celery==5.3.4` - For async email sending
- `redis==5.0.1` - Message broker for Celery
- `django-celery-beat==2.5.0` - For scheduled tasks (if needed in future)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Email Configuration

In production, set the following environment variables:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com  # or your SMTP server
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@groupgo.com
```

For development/testing, emails will be printed to the console by default.

### 3. Celery Configuration (Optional but Recommended)

For async email sending (recommended for production):

#### Install and Start Redis

**On Windows:**
- Download and install Redis from: https://github.com/microsoftarchive/redis/releases
- Or use WSL with Redis

**On Linux/Mac:**
```bash
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # Mac
```

#### Start Redis Server

```bash
redis-server
```

#### Start Celery Worker

In a separate terminal:

```bash
cd Group-7-Fall-2025-Sec-2
celery -A groupgo worker --loglevel=info
```

#### Start Celery Beat (if using scheduled tasks)

```bash
celery -A groupgo beat --loglevel=info
```

### 4. Running Without Celery

If you don't want to use Celery, the system will automatically send emails synchronously. However, this is not recommended for production as it can slow down request handling.

Set this environment variable to disable async:
```bash
CELERY_TASK_ALWAYS_EAGER=True
```

## How It Works

1. **Django Signals**: The notification system uses Django signals to automatically detect when:
   - `TripPreference` objects are saved (and marked as completed)
   - `GroupItinerary` objects are created (new itinerary added to group)
   - `Itinerary` objects are updated (and linked to a group)

2. **Automatic Notifications**: When any of these events occur, all other members of the travel group (excluding the user who made the change) are automatically notified via email.

3. **Email Templates**: Three HTML email templates are included:
   - `email_trip_preference_update.html` - For trip preference updates
   - `email_itinerary_added.html` - For new itinerary additions
   - `email_itinerary_updated.html` - For itinerary updates

## Testing

To test the notification system:

1. Create a travel group with multiple members
2. Have one member update their trip preferences
3. Check the console output (in development) or email inboxes (in production)
4. Verify all other group members receive the notification

## Performance Considerations

- Notifications are sent asynchronously using Celery to avoid blocking request handling
- Emails are sent within 10 minutes of changes (usually much faster)
- Errors in email sending are logged but don't break the main application flow

## Troubleshooting

**Issue**: Celery import errors
**Solution**: The system gracefully falls back to synchronous email sending if Celery is not installed

**Issue**: Emails not being sent
**Solution**: 
1. Check email configuration in settings.py
2. Verify SMTP credentials are correct
3. Check Celery worker is running (if using async)
4. Check application logs for error messages

**Issue**: Too many emails
**Solution**: Notifications are only sent when preferences are marked as completed and only to other group members (not the person making the change)

## Notes

- The system respects user privacy - only group members receive notifications
- The person making the change does NOT receive a notification
- Notifications are sent only when preferences are completed (for trip preferences)
- The system handles missing emails gracefully

