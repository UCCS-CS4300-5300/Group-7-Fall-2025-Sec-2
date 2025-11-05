from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Try to import Celery, fall back to direct execution if not available
try:
    from celery import shared_task
    USE_CELERY = True
except ImportError:
    # Celery not installed, use a no-op decorator
    def shared_task(func):
        return func
    USE_CELERY = False


@shared_task
def send_notification_email(recipient_email, recipient_name, notification_type, group_name, changed_by, change_details):
    """
    Send email notification about changes to travel plans
    
    Args:
        recipient_email: Email address of the recipient
        recipient_name: Name of the recipient
        notification_type: Type of notification (trip_preference_update, itinerary_added, itinerary_updated)
        group_name: Name of the travel group
        changed_by: Name of the user who made the change
        change_details: Dictionary with details about the change
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate email
    if not recipient_email:
        logger.warning(f"Cannot send notification: recipient_email is empty")
        return f"Error: recipient_email is empty"
    
    # Determine subject and template based on notification type
    templates = {
        'trip_preference_update': {
            'subject': f'Travel Plan Update: {group_name}',
            'template': 'notifications/email_trip_preference_update.html',
        },
        'itinerary_added': {
            'subject': f'New Itinerary Added: {group_name}',
            'template': 'notifications/email_itinerary_added.html',
        },
        'itinerary_updated': {
            'subject': f'Itinerary Updated: {group_name}',
            'template': 'notifications/email_itinerary_updated.html',
        },
    }
    
    template_info = templates.get(notification_type, templates['trip_preference_update'])
    
    try:
        # Render HTML email
        html_message = render_to_string(template_info['template'], {
            'recipient_name': recipient_name,
            'group_name': group_name,
            'changed_by': changed_by,
            'change_details': change_details,
            'notification_type': notification_type,
        })
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=template_info['subject'],
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email notification sent successfully to {recipient_email}")
        return f"Email sent successfully to {recipient_email}"
    except Exception as e:
        # Log error but don't raise - we don't want to break the main flow
        logger.error(f"Error sending email to {recipient_email}: {str(e)}")
        return f"Error sending email: {str(e)}"

