"""
Models for AI Implementation
Stores travel search results, consolidated recommendations, and AI-generated content.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class TravelSearch(models.Model):
    """Model to store travel search queries and parameters"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='travel_searches')
    group = models.ForeignKey('travel_groups.TravelGroup', on_delete=models.CASCADE,
                              null=True, blank=True, related_name='ai_searches')

    # Search parameters
    destination = models.CharField(max_length=200)
    origin = models.CharField(max_length=200, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    adults = models.PositiveIntegerField(default=1)
    rooms = models.PositiveIntegerField(default=1)

    # Preferences
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    accommodation_type = models.CharField(max_length=100, blank=True, null=True)
    activity_categories = models.TextField(blank=True, null=True, help_text="Comma-separated list")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Travel Search"
        verbose_name_plural = "Travel Searches"

    def __str__(self):
        return f"Search: {self.destination} ({self.start_date} to {self.end_date})"


class ConsolidatedResult(models.Model):
    """Model to store AI-consolidated search results"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search = models.OneToOneField(TravelSearch, on_delete=models.CASCADE, related_name='consolidated_result')

    # AI-generated content
    summary = models.TextField(help_text="AI-generated summary of recommendations")
    budget_analysis = models.TextField(blank=True, null=True)
    itinerary_suggestions = models.TextField(blank=True, null=True)
    warnings = models.TextField(blank=True, null=True)

    # Rankings and scores
    recommended_flight_ids = models.TextField(blank=True, null=True, help_text="JSON list of recommended flight IDs with scores")
    recommended_hotel_ids = models.TextField(blank=True, null=True, help_text="JSON list of recommended hotel IDs with scores")
    recommended_activity_ids = models.TextField(blank=True, null=True, help_text="JSON list of recommended activity IDs with scores")

    # Raw data storage
    raw_openai_response = models.TextField(blank=True, null=True, help_text="Full OpenAI API response")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consolidated Result"
        verbose_name_plural = "Consolidated Results"

    def __str__(self):
        return f"Results for {self.search.destination}"


class FlightResult(models.Model):
    """Model to store individual flight search results"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search = models.ForeignKey(TravelSearch, on_delete=models.CASCADE, related_name='flight_results')

    # Flight details
    external_id = models.CharField(max_length=200, help_text="ID from external API")
    airline = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')

    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    duration = models.CharField(max_length=50)
    stops = models.PositiveIntegerField(default=0)
    booking_class = models.CharField(max_length=50, default='Economy')
    seats_available = models.CharField(max_length=50, blank=True, null=True)

    # AI recommendation data
    ai_score = models.PositiveIntegerField(null=True, blank=True, help_text="AI-generated score (0-100)")
    ai_reason = models.TextField(blank=True, null=True, help_text="AI-generated reason for recommendation")

    # Raw data
    raw_data = models.TextField(blank=True, null=True, help_text="Full API response as JSON")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_mock = models.BooleanField(default=False, help_text="Whether this is mock data")

    class Meta:
        ordering = ['-ai_score', 'price']
        verbose_name = "Flight Result"
        verbose_name_plural = "Flight Results"

    def __str__(self):
        return f"{self.airline} - ${self.price} ({self.stops} stops)"


class HotelResult(models.Model):
    """Model to store individual hotel search results"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search = models.ForeignKey(TravelSearch, on_delete=models.CASCADE, related_name='hotel_results')

    # Hotel details
    external_id = models.CharField(max_length=200, help_text="ID from external API")
    name = models.CharField(max_length=300)
    address = models.CharField(max_length=500, blank=True, null=True)

    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')

    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)

    room_type = models.CharField(max_length=200, blank=True, null=True)
    amenities = models.TextField(blank=True, null=True, help_text="Comma-separated list")
    distance_from_center = models.CharField(max_length=50, blank=True, null=True)
    breakfast_included = models.BooleanField(default=False)
    cancellation_policy = models.CharField(max_length=200, blank=True, null=True)

    # AI recommendation data
    ai_score = models.PositiveIntegerField(null=True, blank=True, help_text="AI-generated score (0-100)")
    ai_reason = models.TextField(blank=True, null=True, help_text="AI-generated reason for recommendation")

    # Raw data
    raw_data = models.TextField(blank=True, null=True, help_text="Full API response as JSON")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_mock = models.BooleanField(default=False, help_text="Whether this is mock data")

    class Meta:
        ordering = ['-ai_score', 'total_price']
        verbose_name = "Hotel Result"
        verbose_name_plural = "Hotel Results"

    def __str__(self):
        return f"{self.name} - ${self.total_price}"


class ActivityResult(models.Model):
    """Model to store individual activity/tour search results"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search = models.ForeignKey(TravelSearch, on_delete=models.CASCADE, related_name='activity_results')

    # Activity details
    external_id = models.CharField(max_length=200, help_text="ID from external API")
    name = models.CharField(max_length=300)
    category = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    duration_hours = models.PositiveIntegerField(default=2)

    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)

    included = models.TextField(blank=True, null=True, help_text="What's included")
    meeting_point = models.CharField(max_length=300, blank=True, null=True)
    max_group_size = models.PositiveIntegerField(null=True, blank=True)
    languages = models.CharField(max_length=200, blank=True, null=True)
    cancellation_policy = models.CharField(max_length=200, blank=True, null=True)

    # AI recommendation data
    ai_score = models.PositiveIntegerField(null=True, blank=True, help_text="AI-generated score (0-100)")
    ai_reason = models.TextField(blank=True, null=True, help_text="AI-generated reason for recommendation")

    # Raw data
    raw_data = models.TextField(blank=True, null=True, help_text="Full API response as JSON")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_mock = models.BooleanField(default=False, help_text="Whether this is mock data")

    class Meta:
        ordering = ['-ai_score', '-rating']
        verbose_name = "Activity Result"
        verbose_name_plural = "Activity Results"

    def __str__(self):
        return f"{self.name} - ${self.price}"


class GroupConsensus(models.Model):
    """Model to store AI-generated group consensus preferences"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey('travel_groups.TravelGroup', on_delete=models.CASCADE,
                              related_name='ai_consensus')
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)

    # Consensus data
    consensus_preferences = models.TextField(help_text="JSON object with consensus preferences")
    compromise_areas = models.TextField(blank=True, null=True, help_text="JSON list of compromise areas")
    unanimous_preferences = models.TextField(blank=True, null=True, help_text="JSON list")
    conflicting_preferences = models.TextField(blank=True, null=True, help_text="JSON list")
    group_dynamics_notes = models.TextField(blank=True, null=True)

    # Raw OpenAI response
    raw_openai_response = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Group Consensus"
        verbose_name_plural = "Group Consensuses"

    def __str__(self):
        return f"Consensus for {self.group.name}"


class AIGeneratedItinerary(models.Model):
    """Model to store AI-generated itinerary descriptions"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_itineraries')
    search = models.ForeignKey(TravelSearch, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='ai_itineraries')

    # Itinerary content
    title = models.CharField(max_length=300)
    destination = models.CharField(max_length=200)
    description = models.TextField(help_text="AI-generated description")
    duration_days = models.PositiveIntegerField()

    # Selected options
    selected_flight = models.ForeignKey(FlightResult, on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='itineraries')
    selected_hotel = models.ForeignKey(HotelResult, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='itineraries')
    selected_activities = models.TextField(blank=True, null=True, help_text="JSON list of activity IDs")

    # Budget
    estimated_total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_saved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "AI Generated Itinerary"
        verbose_name_plural = "AI Generated Itineraries"

    def __str__(self):
        return f"{self.title} - {self.destination}"


class SearchHistory(models.Model):
    """Model to track user search history for analytics and improvements"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    search = models.ForeignKey(TravelSearch, on_delete=models.CASCADE, related_name='history_entries')

    # User interaction data
    viewed_results = models.BooleanField(default=False)
    saved_itinerary = models.BooleanField(default=False)
    shared_with_group = models.BooleanField(default=False)

    # Feedback
    was_helpful = models.BooleanField(null=True, blank=True)
    feedback_text = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Search History"
        verbose_name_plural = "Search Histories"

    def __str__(self):
        return f"{self.user.username} - {self.search.destination}"


class GroupItineraryOption(models.Model):
    """Model for storing multiple itinerary options for group voting"""

    OPTION_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey('travel_groups.TravelGroup', on_delete=models.CASCADE, related_name='itinerary_options')
    consensus = models.ForeignKey(GroupConsensus, on_delete=models.CASCADE, related_name='itinerary_options')

    # Option identifier
    option_letter = models.CharField(max_length=1, choices=OPTION_CHOICES)

    # Itinerary details
    title = models.CharField(max_length=300)
    description = models.TextField(help_text="AI-generated description of this option")
    destination = models.CharField(max_length=200, blank=True, null=True, help_text="Primary destination for this option")

    # Search results
    search = models.ForeignKey(TravelSearch, on_delete=models.SET_NULL, null=True, blank=True, related_name='group_options')

    # Selected travel options
    selected_flight = models.ForeignKey(FlightResult, on_delete=models.SET_NULL, null=True, blank=True)
    selected_hotel = models.ForeignKey(HotelResult, on_delete=models.SET_NULL, null=True, blank=True)
    selected_activities = models.TextField(blank=True, null=True, help_text="JSON list of activity IDs")

    # Pricing
    estimated_total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_person = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # AI rationale
    ai_reasoning = models.TextField(help_text="Why AI chose this combination for the group")
    compromise_explanation = models.TextField(blank=True, null=True, help_text="Which preferences this option balances")

    # Voting
    vote_count = models.PositiveIntegerField(default=0)
    is_winner = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['option_letter']
        unique_together = ['group', 'consensus', 'option_letter']
        verbose_name = "Group Itinerary Option"
        verbose_name_plural = "Group Itinerary Options"

    def __str__(self):
        return f"Option {self.option_letter} for {self.group.name} - {self.vote_count} votes"

    def update_vote_count(self):
        """Update the vote count from related votes"""
        self.vote_count = self.votes.count()
        self.save()


class ItineraryVote(models.Model):
    """Model for tracking group member votes on itinerary options"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    option = models.ForeignKey(GroupItineraryOption, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='itinerary_votes')
    group = models.ForeignKey('travel_groups.TravelGroup', on_delete=models.CASCADE, related_name='member_votes')

    # Vote details
    voted_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True, help_text="Optional comment about their choice")

    class Meta:
        unique_together = ['group', 'user']  # One vote per user per voting session
        ordering = ['-voted_at']
        verbose_name = "Itinerary Vote"
        verbose_name_plural = "Itinerary Votes"

    def __str__(self):
        return f"{self.user.username} voted for Option {self.option.option_letter}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update vote count on the option
        self.option.update_vote_count()
