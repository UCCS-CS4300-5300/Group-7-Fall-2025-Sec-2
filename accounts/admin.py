from django.contrib import admin
from .models import UserProfile, Itinerary


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'phone_number')


@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'destination', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date', 'created_at')
    search_fields = ('title', 'destination', 'user__username')
    date_hierarchy = 'start_date'
