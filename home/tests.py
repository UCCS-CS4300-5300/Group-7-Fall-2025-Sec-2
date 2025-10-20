from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Trip, User, Submission, PreferenceSubmission


class PreferenceSubmissionTests(TestCase):
    def setUp(self) -> None:
        self.trip = Trip.objects.create(name="Test Trip", description="Testing")
        self.user = User.objects.create(name="Alice", email="alice@example.com", trip=self.trip)

    def test_submit_preferences_creates_submission_and_preferences(self):
        url = reverse("submit_preferences", args=[self.trip.id])
        payload = {
            "user_id": str(self.user.id),
            "budget_min": "100.00",
            "budget_max": "500.00",
            "preferred_activities": "hiking, museums",
            "avoid_activities": "skydiving",
            "accommodation_type": "hotel",
            "dietary_restrictions": "vegetarian",
            "cuisine_preferences": "italian, thai",
            "transportation_preference": "flight",
            "additional_notes": "ocean view preferred",
        }

        response = self.client.post(url, data=payload, follow=True)
        self.assertEqual(response.status_code, 200)

        submission = Submission.objects.get(user=self.user, trip=self.trip)
        self.assertTrue(submission.submitted)
        self.assertIsNotNone(submission.submitted_at)

        prefs = PreferenceSubmission.objects.get(submission=submission)
        self.assertEqual(str(prefs.budget_min), "100.00")
        self.assertEqual(str(prefs.budget_max), "500.00")
        self.assertEqual(prefs.preferred_activities, "hiking, museums")
        self.assertEqual(prefs.avoid_activities, "skydiving")
        self.assertEqual(prefs.accommodation_type, "hotel")
        self.assertEqual(prefs.dietary_restrictions, "vegetarian")
        self.assertEqual(prefs.cuisine_preferences, "italian, thai")
        self.assertEqual(prefs.transportation_preference, "flight")
        self.assertEqual(prefs.additional_notes, "ocean view preferred")

    def test_submit_preferences_updates_existing_preferences(self):
        # First submission
        first_url = reverse("submit_preferences", args=[self.trip.id])
        self.client.post(first_url, data={"user_id": str(self.user.id), "accommodation_type": "hotel"})

        # Update with new values
        update_payload = {
            "user_id": str(self.user.id),
            "accommodation_type": "airbnb",
            "budget_min": "50",
        }
        response = self.client.post(first_url, data=update_payload, follow=True)
        self.assertEqual(response.status_code, 200)

        submission = Submission.objects.get(user=self.user, trip=self.trip)
        prefs = PreferenceSubmission.objects.get(submission=submission)
        self.assertEqual(prefs.accommodation_type, "airbnb")
        self.assertEqual(str(prefs.budget_min), "50.00")

    def test_submission_status_page_loads(self):
        Submission.objects.create(user=self.user, trip=self.trip, submitted=False, submitted_at=None)
        url = reverse("submission_status", args=[self.trip.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.trip.name)
        self.assertContains(response, self.user.name)

    def test_view_preferences_page_handles_no_preferences(self):
        # No preferences created yet
        Submission.objects.create(user=self.user, trip=self.trip, submitted=True, submitted_at=timezone.now())
        url = reverse("view_preferences", args=[self.trip.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.trip.name)
