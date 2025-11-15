"""
Admin configuration for AI Implementation
"""

from django.contrib import admin
from .models import (
    TravelSearch, ConsolidatedResult, FlightResult, HotelResult,
    ActivityResult, GroupConsensus, AIGeneratedItinerary, SearchHistory,
    GroupItineraryOption, ItineraryVote
)


@admin.register(TravelSearch)
class TravelSearchAdmin(admin.ModelAdmin):
    list_display = ['destination', 'user', 'start_date', 'end_date', 'adults', 'is_completed', 'created_at']
    list_filter = ['is_completed', 'created_at', 'start_date']
    search_fields = ['destination', 'origin', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'group', 'destination', 'origin')
        }),
        ('Dates and Capacity', {
            'fields': ('start_date', 'end_date', 'adults', 'rooms')
        }),
        ('Preferences', {
            'fields': ('budget_min', 'budget_max', 'accommodation_type', 'activity_categories')
        }),
        ('Status', {
            'fields': ('is_completed', 'created_at', 'updated_at')
        }),
    )


@admin.register(ConsolidatedResult)
class ConsolidatedResultAdmin(admin.ModelAdmin):
    list_display = ['search', 'created_at']
    search_fields = ['search__destination', 'summary']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'search')
        }),
        ('AI-Generated Content', {
            'fields': ('summary', 'budget_analysis', 'itinerary_suggestions', 'warnings')
        }),
        ('Recommendations', {
            'fields': ('recommended_flight_ids', 'recommended_hotel_ids', 'recommended_activity_ids')
        }),
        ('Raw Data', {
            'fields': ('raw_openai_response',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(FlightResult)
class FlightResultAdmin(admin.ModelAdmin):
    list_display = ['airline', 'price', 'currency', 'stops', 'ai_score', 'departure_time', 'is_mock']
    list_filter = ['airline', 'booking_class', 'stops', 'is_mock', 'created_at']
    search_fields = ['airline', 'external_id', 'search__destination']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'search', 'external_id', 'airline')
        }),
        ('Pricing', {
            'fields': ('price', 'currency')
        }),
        ('Flight Details', {
            'fields': ('departure_time', 'arrival_time', 'duration', 'stops', 'booking_class', 'seats_available')
        }),
        ('AI Recommendation', {
            'fields': ('ai_score', 'ai_reason')
        }),
        ('Raw Data', {
            'fields': ('raw_data', 'is_mock'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )


@admin.register(HotelResult)
class HotelResultAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_price', 'currency', 'rating', 'ai_score', 'is_mock']
    list_filter = ['rating', 'breakfast_included', 'is_mock', 'created_at']
    search_fields = ['name', 'address', 'external_id', 'search__destination']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'search', 'external_id', 'name', 'address')
        }),
        ('Pricing', {
            'fields': ('price_per_night', 'total_price', 'currency')
        }),
        ('Hotel Details', {
            'fields': ('rating', 'review_count', 'room_type', 'amenities', 'distance_from_center',
                       'breakfast_included', 'cancellation_policy')
        }),
        ('AI Recommendation', {
            'fields': ('ai_score', 'ai_reason')
        }),
        ('Raw Data', {
            'fields': ('raw_data', 'is_mock'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ActivityResult)
class ActivityResultAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'duration_hours', 'rating', 'ai_score', 'is_mock']
    list_filter = ['category', 'is_mock', 'created_at']
    search_fields = ['name', 'category', 'description', 'external_id']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'search', 'external_id', 'name', 'category', 'description')
        }),
        ('Pricing and Duration', {
            'fields': ('price', 'currency', 'duration_hours')
        }),
        ('Activity Details', {
            'fields': ('rating', 'review_count', 'included', 'meeting_point',
                       'max_group_size', 'languages', 'cancellation_policy')
        }),
        ('AI Recommendation', {
            'fields': ('ai_score', 'ai_reason')
        }),
        ('Raw Data', {
            'fields': ('raw_data', 'is_mock'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )


@admin.register(GroupConsensus)
class GroupConsensusAdmin(admin.ModelAdmin):
    list_display = ['group', 'generated_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['group__name', 'generated_by__username']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'group', 'generated_by', 'is_active')
        }),
        ('Consensus Data', {
            'fields': ('consensus_preferences', 'compromise_areas', 'unanimous_preferences',
                       'conflicting_preferences', 'group_dynamics_notes')
        }),
        ('Raw Data', {
            'fields': ('raw_openai_response',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )


@admin.register(AIGeneratedItinerary)
class AIGeneratedItineraryAdmin(admin.ModelAdmin):
    list_display = ['title', 'destination', 'user', 'duration_days', 'estimated_total_cost', 'is_saved', 'created_at']
    list_filter = ['is_saved', 'created_at']
    search_fields = ['title', 'destination', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'search', 'title', 'destination', 'description', 'duration_days')
        }),
        ('Selected Options', {
            'fields': ('selected_flight', 'selected_hotel', 'selected_activities')
        }),
        ('Budget', {
            'fields': ('estimated_total_cost',)
        }),
        ('Status', {
            'fields': ('is_saved', 'created_at', 'updated_at')
        }),
    )


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'search', 'viewed_results', 'saved_itinerary', 'shared_with_group', 'was_helpful', 'created_at']
    list_filter = ['viewed_results', 'saved_itinerary', 'shared_with_group', 'was_helpful', 'created_at']
    search_fields = ['user__username', 'search__destination', 'feedback_text']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'search')
        }),
        ('Interaction Data', {
            'fields': ('viewed_results', 'saved_itinerary', 'shared_with_group')
        }),
        ('Feedback', {
            'fields': ('was_helpful', 'feedback_text')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )


@admin.register(GroupItineraryOption)
class GroupItineraryOptionAdmin(admin.ModelAdmin):
    list_display = ['option_letter', 'group', 'title', 'estimated_total_cost', 'vote_count', 'is_winner', 'created_at']
    list_filter = ['option_letter', 'is_winner', 'created_at']
    search_fields = ['title', 'group__name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'vote_count']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'group', 'consensus', 'option_letter', 'title', 'description')
        }),
        ('Selected Options', {
            'fields': ('search', 'selected_flight', 'selected_hotel', 'selected_activities')
        }),
        ('Pricing', {
            'fields': ('estimated_total_cost', 'cost_per_person')
        }),
        ('AI Analysis', {
            'fields': ('ai_reasoning', 'compromise_explanation')
        }),
        ('Voting', {
            'fields': ('vote_count', 'is_winner')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ItineraryVote)
class ItineraryVoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'option', 'group', 'voted_at']
    list_filter = ['voted_at', 'group']
    search_fields = ['user__username', 'group__name', 'option__title', 'comment']
    readonly_fields = ['id', 'voted_at']
    date_hierarchy = 'voted_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'option', 'user', 'group')
        }),
        ('Vote Details', {
            'fields': ('comment', 'voted_at')
        }),
    )
