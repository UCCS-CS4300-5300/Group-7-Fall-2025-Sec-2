from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from travel_groups.models import TripPreference, GroupItinerary
from accounts.models import Itinerary

try:
    from .tasks import send_notification_email
    NOTIFICATIONS_ENABLED = True
except ImportError:
    NOTIFICATIONS_ENABLED = False


@receiver(post_save, sender=TripPreference)
def notify_trip_preference_changes(sender, instance, created, **kwargs):
    """Send email notifications when trip preferences are created or updated"""
    group = instance.group
    user = instance.user
    
    # Get all other members of the group
    from travel_groups.models import GroupMember
    other_members = GroupMember.objects.filter(
        group=group
    ).exclude(user=user).select_related('user')
    
    # Only notify if preferences are completed
    if instance.is_completed and NOTIFICATIONS_ENABLED:
        for member in other_members:
            # Only send if user has an email
            if member.user.email:
                try:
                    # Send async email notification (or sync if Celery not available)
                    if hasattr(send_notification_email, 'delay'):
                        send_notification_email.delay(
                            recipient_email=member.user.email,
                            recipient_name=member.user.get_full_name() or member.user.username,
                            notification_type='trip_preference_update',
                            group_name=group.name,
                            changed_by=user.get_full_name() or user.username,
                            change_details={
                                'type': 'Trip Preferences',
                                'destination': instance.destination,
                                'start_date': str(instance.start_date),
                                'end_date': str(instance.end_date),
                            }
                        )
                    else:
                        # Celery not available, send synchronously
                        send_notification_email(
                            recipient_email=member.user.email,
                            recipient_name=member.user.get_full_name() or member.user.username,
                            notification_type='trip_preference_update',
                            group_name=group.name,
                            changed_by=user.get_full_name() or user.username,
                            change_details={
                                'type': 'Trip Preferences',
                                'destination': instance.destination,
                                'start_date': str(instance.start_date),
                                'end_date': str(instance.end_date),
                            }
                        )
                except Exception as e:
                    # Log error but don't break the main flow
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error queuing email notification: {str(e)}")


@receiver(post_save, sender=GroupItinerary)
def notify_itinerary_added_to_group(sender, instance, created, **kwargs):
    """Send email notifications when an itinerary is added to a group"""
    if created and NOTIFICATIONS_ENABLED:
        group = instance.group
        user = instance.added_by
        
        # Get all other members of the group
        from travel_groups.models import GroupMember
        other_members = GroupMember.objects.filter(
            group=group
        ).exclude(user=user).select_related('user')
        
        for member in other_members:
            # Only send if user has an email
            if member.user.email:
                try:
                    # Send async email notification (or sync if Celery not available)
                    if hasattr(send_notification_email, 'delay'):
                        send_notification_email.delay(
                            recipient_email=member.user.email,
                            recipient_name=member.user.get_full_name() or member.user.username,
                            notification_type='itinerary_added',
                            group_name=group.name,
                            changed_by=user.get_full_name() or user.username,
                            change_details={
                                'type': 'Itinerary',
                                'title': instance.itinerary.title,
                                'destination': instance.itinerary.destination,
                                'start_date': str(instance.itinerary.start_date),
                                'end_date': str(instance.itinerary.end_date),
                            }
                        )
                    else:
                        # Celery not available, send synchronously
                        send_notification_email(
                            recipient_email=member.user.email,
                            recipient_name=member.user.get_full_name() or member.user.username,
                            notification_type='itinerary_added',
                            group_name=group.name,
                            changed_by=user.get_full_name() or user.username,
                            change_details={
                                'type': 'Itinerary',
                                'title': instance.itinerary.title,
                                'destination': instance.itinerary.destination,
                                'start_date': str(instance.itinerary.start_date),
                                'end_date': str(instance.itinerary.end_date),
                            }
                        )
                except Exception as e:
                    # Log error but don't break the main flow
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error queuing email notification: {str(e)}")


@receiver(post_save, sender=Itinerary)
def notify_itinerary_changes(sender, instance, created, **kwargs):
    """Send email notifications when an itinerary linked to a group is updated"""
    # Only notify on updates, not creation
    if not created and NOTIFICATIONS_ENABLED:
        # Find all groups this itinerary is linked to
        group_links = GroupItinerary.objects.filter(itinerary=instance).select_related('group')
        
        for link in group_links:
            group = link.group
            user = instance.user
            
            # Get all other members of the group
            from travel_groups.models import GroupMember
            other_members = GroupMember.objects.filter(
                group=group
            ).exclude(user=user).select_related('user')
            
            for member in other_members:
                # Only send if user has an email
                if member.user.email:
                    try:
                        # Send async email notification (or sync if Celery not available)
                        if hasattr(send_notification_email, 'delay'):
                            send_notification_email.delay(
                                recipient_email=member.user.email,
                                recipient_name=member.user.get_full_name() or member.user.username,
                                notification_type='itinerary_updated',
                                group_name=group.name,
                                changed_by=user.get_full_name() or user.username,
                                change_details={
                                    'type': 'Itinerary Update',
                                    'title': instance.title,
                                    'destination': instance.destination,
                                    'start_date': str(instance.start_date),
                                    'end_date': str(instance.end_date),
                                }
                            )
                        else:
                            # Celery not available, send synchronously
                            send_notification_email(
                                recipient_email=member.user.email,
                                recipient_name=member.user.get_full_name() or member.user.username,
                                notification_type='itinerary_updated',
                                group_name=group.name,
                                changed_by=user.get_full_name() or user.username,
                                change_details={
                                    'type': 'Itinerary Update',
                                    'title': instance.title,
                                    'destination': instance.destination,
                                    'start_date': str(instance.start_date),
                                    'end_date': str(instance.end_date),
                                }
                            )
                    except Exception as e:
                        # Log error but don't break the main flow
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Error queuing email notification: {str(e)}")

