from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Trip, User, Submission, PreferenceSubmission
from django.utils import timezone
from decimal import Decimal

def index(request):
    return render(request, "index.html")

def trip_list(request):
    trips = Trip.objects.all()
    return render(request, 'trip_list.html', {'trips': trips})

def submission_status(request, trip_id):
    trip = Trip.objects.get(id=trip_id)
    users = User.objects.filter(trip=trip)
    
    submission_statuses = []
    for user in users:
        try:
            submission = Submission.objects.get(user=user, trip=trip)
            status = 'Submitted' if submission.submitted else 'Not Submitted'
            submitted_at = submission.submitted_at
        except Submission.DoesNotExist:
            status = 'Not Submitted'
            submitted_at = None
        
        submission_statuses.append({
            'user': user,
            'status': status,
            'submitted_at': submitted_at
        })
    
    return render(request, 'submission_status.html', {
        'trip': trip,
        'submission_statuses': submission_statuses
    })

def submit_preferences(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if not user_id:
            messages.error(request, 'Please select a user.')
            users = User.objects.filter(trip=trip)
            return render(request, 'submit_preferences.html', {
                'trip': trip,
                'users': users
            })
        
        user = get_object_or_404(User, id=user_id)
        
        # Create or update submission
        submission, created = Submission.objects.get_or_create(
            user=user,
            trip=trip,
            defaults={'submitted': True, 'submitted_at': timezone.now()}
        )
        
        if not created:
            submission.submitted = True
            submission.submitted_at = timezone.now()
            submission.save()
        
        # Create or update preference submission
        preference_data = {
            'budget_min': request.POST.get('budget_min') or None,
            'budget_max': request.POST.get('budget_max') or None,
            'preferred_activities': request.POST.get('preferred_activities', ''),
            'avoid_activities': request.POST.get('avoid_activities', ''),
            'accommodation_type': request.POST.get('accommodation_type', 'no_preference'),
            'dietary_restrictions': request.POST.get('dietary_restrictions', ''),
            'cuisine_preferences': request.POST.get('cuisine_preferences', ''),
            'transportation_preference': request.POST.get('transportation_preference', 'no_preference'),
            'additional_notes': request.POST.get('additional_notes', ''),
        }
        
        # Convert budget values to Decimal if provided
        if preference_data['budget_min']:
            try:
                preference_data['budget_min'] = Decimal(preference_data['budget_min'])
            except (ValueError, TypeError):
                preference_data['budget_min'] = None
        
        if preference_data['budget_max']:
            try:
                preference_data['budget_max'] = Decimal(preference_data['budget_max'])
            except (ValueError, TypeError):
                preference_data['budget_max'] = None
        
        # Create or update preference submission
        preference_submission, pref_created = PreferenceSubmission.objects.get_or_create(
            submission=submission,
            defaults=preference_data
        )
        
        if not pref_created:
            # Update existing preferences
            for key, value in preference_data.items():
                setattr(preference_submission, key, value)
            preference_submission.save()
        
        messages.success(request, f'Preferences submitted successfully for {user.name}!')
        return redirect('submission_status', trip_id=trip.id)
    
    users = User.objects.filter(trip=trip)
    return render(request, 'submit_preferences.html', {
        'trip': trip,
        'users': users
    })

def view_preferences(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    submissions = Submission.objects.filter(trip=trip, submitted=True).select_related('user', 'preferences')
    
    preference_data = []
    for submission in submissions:
        try:
            preferences = submission.preferences
            preference_data.append({
                'user': submission.user,
                'submission': submission,
                'preferences': preferences,
                'has_preferences': True
            })
        except PreferenceSubmission.DoesNotExist:
            preference_data.append({
                'user': submission.user,
                'submission': submission,
                'preferences': None,
                'has_preferences': False
            })
    
    return render(request, 'view_preferences.html', {
        'trip': trip,
        'preference_data': preference_data
    })