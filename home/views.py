from django.shortcuts import render
from django.http import HttpResponse
from .models import Trip, User, Submission
from django.utils import timezone

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
    trip = Trip.objects.get(id=trip_id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = User.objects.get(id=user_id)
        
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
        
        return HttpResponse("Preferences submitted successfully!")
    
    users = User.objects.filter(trip=trip)
    return render(request, 'submit_preferences.html', {
        'trip': trip,
        'users': users
    })