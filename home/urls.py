from django.urls import path
from .views import index, trip_list, submission_status, submit_preferences

urlpatterns = [
    path("", index, name="index"),
    path("trips/", trip_list, name="trip_list"),
    path("trips/<int:trip_id>/status/", submission_status, name="submission_status"),
    path("trips/<int:trip_id>/submit/", submit_preferences, name="submit_preferences"),
]
