from django.db import models

class Trip(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.name} - {self.trip.name} ({'Submitted' if self.submitted else 'Not Submitted'})"

class PreferenceSubmission(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='preferences')
    
    # Travel preferences
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Minimum budget")
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum budget")
    
    # Activity preferences
    preferred_activities = models.TextField(blank=True, help_text="Activities you'd like to do (comma-separated)")
    avoid_activities = models.TextField(blank=True, help_text="Activities you'd like to avoid (comma-separated)")
    
    # Accommodation preferences
    accommodation_type = models.CharField(
        max_length=50,
        choices=[
            ('hotel', 'Hotel'),
            ('airbnb', 'Airbnb'),
            ('hostel', 'Hostel'),
            ('resort', 'Resort'),
            ('camping', 'Camping'),
            ('no_preference', 'No Preference')
        ],
        default='no_preference'
    )
    
    # Food preferences
    dietary_restrictions = models.TextField(blank=True, help_text="Any dietary restrictions or preferences")
    cuisine_preferences = models.TextField(blank=True, help_text="Preferred cuisines (comma-separated)")
    
    # Transportation preferences
    transportation_preference = models.CharField(
        max_length=50,
        choices=[
            ('flight', 'Flight'),
            ('car', 'Car'),
            ('train', 'Train'),
            ('bus', 'Bus'),
            ('no_preference', 'No Preference')
        ],
        default='no_preference'
    )
    
    # Additional notes
    additional_notes = models.TextField(blank=True, help_text="Any other preferences or requirements")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.submission.user.name} - {self.submission.trip.name}"