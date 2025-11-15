from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class TravelGroup(models.Model):
    """Model representing a travel group"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='group_photos/', blank=True, null=True, help_text="Optional group photo")
    password = models.CharField(max_length=100, default='', help_text="Password required to join the group")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    max_members = models.PositiveIntegerField(default=10, help_text="Maximum number of members allowed in the group")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Travel Group"
        verbose_name_plural = "Travel Groups"

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        """Return the number of members in the group"""
        return self.members.count()

    @property
    def is_full(self):
        """Check if the group has reached maximum capacity"""
        return self.member_count >= self.max_members

    def get_unique_identifier(self):
        """Return a shorter, user-friendly identifier for the group"""
        return str(self.id)[:8].upper()

class GroupMember(models.Model):
    """Model representing a member of a travel group"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    group = models.ForeignKey(TravelGroup, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    has_travel_preferences = models.BooleanField(default=False, help_text="Whether the member has added their travel preferences")

    class Meta:
        unique_together = ['group', 'user']
        ordering = ['joined_at']
        verbose_name = "Group Member"
        verbose_name_plural = "Group Members"

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

    def is_admin(self):
        """Check if the member is an admin of the group"""
        return self.role == 'admin'

class GroupItinerary(models.Model):
    """Model linking groups to itineraries"""
    group = models.ForeignKey(TravelGroup, on_delete=models.CASCADE, related_name='group_itineraries')
    itinerary = models.ForeignKey('accounts.Itinerary', on_delete=models.CASCADE, related_name='group_links')
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False, help_text="Whether the itinerary is approved by group admins")

    class Meta:
        unique_together = ['group', 'itinerary']
        ordering = ['-added_at']
        verbose_name = "Group Itinerary"
        verbose_name_plural = "Group Itineraries"

    def __str__(self):
        return f"{self.itinerary.title} in {self.group.name}"

class TravelPreference(models.Model):
    """Model for storing member travel preferences"""
    member = models.OneToOneField(GroupMember, on_delete=models.CASCADE, related_name='travel_preferences')
    budget_range = models.CharField(max_length=50, blank=True, null=True, help_text="Budget range (e.g., $500-1000)")
    accommodation_preference = models.CharField(max_length=100, blank=True, null=True, help_text="Hotel, Airbnb, Hostel, etc.")
    activity_preferences = models.TextField(blank=True, null=True, help_text="Preferred activities")
    dietary_restrictions = models.TextField(blank=True, null=True, help_text="Any dietary restrictions or preferences")
    accessibility_needs = models.TextField(blank=True, null=True, help_text="Any accessibility requirements")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes or preferences")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Travel Preference"
        verbose_name_plural = "Travel Preferences"

    def __str__(self):
        return f"Preferences for {self.member.user.username} in {self.member.group.name}"

class TripPreference(models.Model):
    """Model for storing specific trip preferences for a group"""
    TRAVEL_METHOD_CHOICES = [
        ('flight', 'Flight'),
        ('car', 'Car'),
        ('train', 'Train'),
        ('bus', 'Bus'),
        ('other', 'Other'),
    ]

    group = models.ForeignKey(TravelGroup, on_delete=models.CASCADE, related_name='trip_preferences')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trip_preferences')
    start_date = models.DateField(help_text="Preferred start date for the trip")
    end_date = models.DateField(help_text="Preferred end date for the trip")
    destination = models.CharField(max_length=200, help_text="Preferred destination")
    budget = models.CharField(max_length=50, help_text="Budget for the trip (e.g., $1700)")
    travel_method = models.CharField(max_length=20, choices=TRAVEL_METHOD_CHOICES, help_text="Preferred method of travel")
    rental_car = models.BooleanField(default=False, help_text="Whether rental car is needed")
    accommodation_preference = models.CharField(max_length=100, blank=True, null=True, help_text="Preferred accommodation type")
    activity_preferences = models.TextField(blank=True, null=True, help_text="Preferred activities")
    dietary_restrictions = models.TextField(blank=True, null=True, help_text="Any dietary restrictions")
    accessibility_needs = models.TextField(blank=True, null=True, help_text="Any accessibility requirements")
    additional_notes = models.TextField(blank=True, null=True, help_text="Additional notes or preferences")
    is_completed = models.BooleanField(default=False, help_text="Whether user has completed entering preferences")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['group', 'user']
        ordering = ['-created_at']
        verbose_name = "Trip Preference"
        verbose_name_plural = "Trip Preferences"

    def __str__(self):
        return f"Trip preferences for {self.user.username} in {self.group.name}"
