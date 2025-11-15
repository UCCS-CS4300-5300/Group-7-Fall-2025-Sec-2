"""
URL Configuration for AI Implementation
"""

from django.urls import path
from . import views

app_name = 'ai_implementation'

urlpatterns = [
    # Search pages
    path('', views.search_home, name='search_home'),
    path('search/advanced/', views.advanced_search, name='advanced_search'),
    path('search/<uuid:search_id>/results/', views.search_results, name='search_results'),
    path('search/<uuid:search_id>/perform/', views.perform_search, name='perform_search'),

    # Group consensus
    path('group/<uuid:group_id>/consensus/generate/', views.generate_group_consensus, name='generate_group_consensus'),
    path('group/<uuid:group_id>/consensus/view/', views.view_group_consensus, name='view_group_consensus'),

    # Group voting on itineraries (NEW)
    path('group/<uuid:group_id>/voting/generate/', views.generate_voting_options, name='generate_voting_options'),
    path('group/<uuid:group_id>/voting/options/', views.view_voting_options, name='view_voting_options'),
    path('group/<uuid:group_id>/voting/cast/<uuid:option_id>/', views.cast_vote, name='cast_vote'),
    path('group/<uuid:group_id>/voting/results/', views.voting_results, name='voting_results'),

    # Itinerary management
    path('search/<uuid:search_id>/save/', views.save_itinerary, name='save_itinerary'),
    path('itineraries/', views.my_itineraries, name='my_itineraries'),
    path('itinerary/<uuid:itinerary_id>/', views.view_itinerary, name='view_itinerary'),
]
