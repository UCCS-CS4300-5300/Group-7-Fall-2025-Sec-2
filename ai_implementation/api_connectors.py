"""
API Connectors Module
Handles connections to various travel APIs (flights, hotels, activities).
This module provides a unified interface for searching across multiple travel services.
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings


class BaseAPIConnector:
    """Base class for all API connectors"""
    
    def __init__(self):
        self.timeout = 30
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'GroupGo-TravelApp/1.0'
        }
    
    def _make_request(self, url: str, method: str = 'GET', params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with error handling"""
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=self.headers, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {str(e)}")
            return None


class FlightAPIConnector(BaseAPIConnector):
    """
    Connector for flight search APIs.
    This implementation uses Amadeus API as an example, but can be adapted for other services.
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get('AMADEUS_API_KEY', getattr(settings, 'AMADEUS_API_KEY', None))
        self.api_secret = os.environ.get('AMADEUS_API_SECRET', getattr(settings, 'AMADEUS_API_SECRET', None))
        self.base_url = "https://test.api.amadeus.com/v2"
        self.access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token for Amadeus API"""
        if not self.api_key or not self.api_secret:
            print("Amadeus API credentials not configured")
            return None
        
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.api_key,
            'client_secret': self.api_secret
        }
        
        try:
            response = requests.post(url, data=data, timeout=self.timeout)
            response.raise_for_status()
            self.access_token = response.json().get('access_token')
            return self.access_token
        except Exception as e:
            print(f"Error getting access token: {str(e)}")
            return None
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for flights.
        
        Args:
            origin: Origin airport code (e.g., 'LAX')
            destination: Destination airport code (e.g., 'JFK')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (for round trip)
            adults: Number of adult passengers
            max_results: Maximum number of results to return
            
        Returns:
            List of flight options
        """
        
        # If API credentials are not configured, return mock data
        if not self.api_key or not self.api_secret:
            return self._get_mock_flight_data(origin, destination, departure_date, return_date, adults)
        
        # Get access token
        if not self.access_token:
            if not self._get_access_token():
                return self._get_mock_flight_data(origin, destination, departure_date, return_date, adults)
        
        # Make API request
        url = f"{self.base_url}/shopping/flight-offers"
        params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': adults,
            'max': max_results
        }
        
        if return_date:
            params['returnDate'] = return_date
        
        self.headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Parse and format the results
            flights = []
            for offer in data.get('data', []):
                flight = self._parse_flight_offer(offer)
                flights.append(flight)
            
            return flights
        except Exception as e:
            print(f"Error searching flights: {str(e)}")
            return self._get_mock_flight_data(origin, destination, departure_date, return_date, adults)
    
    def _parse_flight_offer(self, offer: Dict) -> Dict[str, Any]:
        """Parse Amadeus flight offer into simplified format"""
        try:
            price = offer.get('price', {})
            itineraries = offer.get('itineraries', [])
            
            # Get first itinerary details
            first_itinerary = itineraries[0] if itineraries else {}
            segments = first_itinerary.get('segments', [])
            first_segment = segments[0] if segments else {}
            
            return {
                'id': offer.get('id', 'N/A'),
                'price': float(price.get('total', 0)),
                'currency': price.get('currency', 'USD'),
                'airline': first_segment.get('carrierCode', 'Unknown'),
                'departure_time': first_segment.get('departure', {}).get('at', 'N/A'),
                'arrival_time': first_segment.get('arrival', {}).get('at', 'N/A'),
                'duration': first_itinerary.get('duration', 'N/A'),
                'stops': len(segments) - 1,
                'booking_class': first_segment.get('cabin', 'Economy'),
                'seats_available': offer.get('numberOfBookableSeats', 'N/A')
            }
        except Exception as e:
            print(f"Error parsing flight offer: {str(e)}")
            return {'error': 'Failed to parse flight data'}
    
    def _get_mock_flight_data(self, origin: str, destination: str, departure_date: str, 
                              return_date: Optional[str], adults: int) -> List[Dict[str, Any]]:
        """Generate mock flight data for testing/development"""
        import random
        
        airlines = ['AA', 'UA', 'DL', 'SW', 'B6', 'AS']
        base_price = 250
        
        flights = []
        for i in range(5):
            price = base_price + random.randint(-100, 300)
            stops = random.choice([0, 1, 2])
            
            flights.append({
                'id': f'MOCK-FL-{i+1}',
                'price': price * adults,
                'currency': 'USD',
                'airline': random.choice(airlines),
                'departure_time': f'{departure_date}T{random.randint(6, 20):02d}:{random.choice([0, 30]):02d}:00',
                'arrival_time': f'{departure_date}T{random.randint(10, 23):02d}:{random.choice([0, 30]):02d}:00',
                'duration': f'PT{random.randint(2, 8)}H{random.randint(0, 59)}M',
                'stops': stops,
                'booking_class': random.choice(['Economy', 'Premium Economy', 'Business']),
                'seats_available': random.randint(1, 9),
                'route': f'{origin} → {destination}',
                'is_mock': True
            })
        
        return flights


class HotelAPIConnector(BaseAPIConnector):
    """
    Connector for hotel search APIs.
    This can integrate with services like Booking.com, Hotels.com, or Amadeus Hotels API.
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get('HOTEL_API_KEY', getattr(settings, 'HOTEL_API_KEY', None))
        # Add more configuration as needed
    
    def search_hotels(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        adults: int = 1,
        rooms: int = 1,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for hotels.
        
        Args:
            destination: Destination city or location
            check_in: Check-in date in YYYY-MM-DD format
            check_out: Check-out date in YYYY-MM-DD format
            adults: Number of adults
            rooms: Number of rooms
            max_results: Maximum number of results
            
        Returns:
            List of hotel options
        """
        
        # For now, return mock data (can be replaced with actual API calls)
        return self._get_mock_hotel_data(destination, check_in, check_out, adults, rooms)
    
    def _get_mock_hotel_data(self, destination: str, check_in: str, check_out: str,
                             adults: int, rooms: int) -> List[Dict[str, Any]]:
        """Generate mock hotel data for testing/development"""
        import random
        
        hotel_types = ['Hotel', 'Resort', 'Inn', 'Boutique Hotel', 'Apartment']
        amenities_pool = ['WiFi', 'Pool', 'Gym', 'Spa', 'Restaurant', 'Bar', 'Parking', 'Pet Friendly']
        
        hotels = []
        for i in range(8):
            base_price = random.randint(80, 400)
            rating = round(random.uniform(3.5, 5.0), 1)
            
            # Select random amenities
            num_amenities = random.randint(3, 6)
            amenities = random.sample(amenities_pool, num_amenities)
            
            hotels.append({
                'id': f'MOCK-HT-{i+1}',
                'name': f'{random.choice(["Grand", "Luxury", "Comfort", "Downtown", "Seaside"])} {random.choice(hotel_types)}',
                'price_per_night': base_price,
                'total_price': base_price * self._calculate_nights(check_in, check_out) * rooms,
                'currency': 'USD',
                'rating': rating,
                'review_count': random.randint(50, 500),
                'address': f'{random.randint(100, 9999)} Main St, {destination}',
                'amenities': amenities,
                'room_type': random.choice(['Standard Room', 'Deluxe Room', 'Suite', 'Family Room']),
                'cancellation_policy': random.choice(['Free cancellation', 'Non-refundable', 'Partially refundable']),
                'distance_from_center': f'{random.uniform(0.5, 10):.1f} km',
                'breakfast_included': random.choice([True, False]),
                'is_mock': True
            })
        
        return hotels
    
    def _calculate_nights(self, check_in: str, check_out: str) -> int:
        """Calculate number of nights between dates"""
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
            return (check_out_date - check_in_date).days
        except:
            return 1


class ActivityAPIConnector(BaseAPIConnector):
    """
    Connector for activity and tour search APIs.
    This can integrate with services like Viator, GetYourGuide, or TripAdvisor.
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get('ACTIVITY_API_KEY', getattr(settings, 'ACTIVITY_API_KEY', None))
    
    def search_activities(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        categories: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for activities and tours.
        
        Args:
            destination: Destination city or location
            start_date: Trip start date in YYYY-MM-DD format
            end_date: Trip end date in YYYY-MM-DD format
            categories: List of activity categories (e.g., ['museums', 'outdoor', 'food'])
            max_results: Maximum number of results
            
        Returns:
            List of activity options
        """
        
        # For now, return mock data
        return self._get_mock_activity_data(destination, categories or [])
    
    def _get_mock_activity_data(self, destination: str, categories: List[str]) -> List[Dict[str, Any]]:
        """Generate mock activity data for testing/development"""
        import random
        
        activity_types = {
            'museums': ['Museum Tour', 'Art Gallery Visit', 'Historical Site Tour'],
            'outdoor': ['Hiking Tour', 'Bike Rental', 'Beach Activities', 'Nature Walk'],
            'food': ['Food Tour', 'Cooking Class', 'Wine Tasting', 'Restaurant Tour'],
            'adventure': ['Zip Lining', 'Rock Climbing', 'Kayaking', 'Parasailing'],
            'culture': ['City Walking Tour', 'Theater Show', 'Music Concert', 'Local Market Visit'],
            'default': ['City Tour', 'Sightseeing', 'Local Experience']
        }
        
        activities = []
        for i in range(10):
            # Pick a category
            if categories:
                category = random.choice(categories)
                activity_list = activity_types.get(category, activity_types['default'])
            else:
                category = random.choice(list(activity_types.keys()))
                activity_list = activity_types[category]
            
            activity_name = random.choice(activity_list)
            price = random.randint(20, 200)
            duration_hours = random.choice([2, 3, 4, 6, 8])
            
            activities.append({
                'id': f'MOCK-ACT-{i+1}',
                'name': f'{activity_name} in {destination}',
                'category': category,
                'price': price,
                'currency': 'USD',
                'duration_hours': duration_hours,
                'rating': round(random.uniform(4.0, 5.0), 1),
                'review_count': random.randint(10, 300),
                'description': f'Experience an amazing {activity_name.lower()} in {destination}. Perfect for all ages!',
                'included': random.choice([
                    'Guide, Equipment',
                    'Tickets, Transportation',
                    'Meals, Guide',
                    'Equipment only'
                ]),
                'meeting_point': f'{destination} Central Location',
                'cancellation_policy': random.choice(['Free cancellation up to 24h', 'Non-refundable', '50% refund']),
                'max_group_size': random.randint(6, 20),
                'languages': random.sample(['English', 'Spanish', 'French', 'German'], random.randint(1, 3)),
                'is_mock': True
            })
        
        return activities


class TravelAPIAggregator:
    """
    Aggregator class that combines all travel API connectors.
    Provides a single interface for searching across all travel services.
    """
    
    def __init__(self):
        self.flight_api = FlightAPIConnector()
        self.hotel_api = HotelAPIConnector()
        self.activity_api = ActivityAPIConnector()
    
    def search_all(
        self,
        destination: str,
        origin: Optional[str] = None,
        start_date: str = None,
        end_date: str = None,
        adults: int = 1,
        rooms: int = 1,
        preferences: Optional[Dict] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across all travel services simultaneously.
        
        Args:
            destination: Destination location
            origin: Origin location (for flights)
            start_date: Trip start date
            end_date: Trip end date
            adults: Number of adults
            rooms: Number of hotel rooms
            preferences: Additional search preferences
            
        Returns:
            Dictionary containing results from all services
        """
        
        results = {
            'flights': [],
            'hotels': [],
            'activities': [],
            'errors': []
        }
        
        # Search flights
        if origin and start_date:
            try:
                results['flights'] = self.flight_api.search_flights(
                    origin=origin,
                    destination=destination,
                    departure_date=start_date,
                    return_date=end_date,
                    adults=adults
                )
            except Exception as e:
                results['errors'].append(f'Flight search error: {str(e)}')
        
        # Search hotels
        if start_date and end_date:
            try:
                results['hotels'] = self.hotel_api.search_hotels(
                    destination=destination,
                    check_in=start_date,
                    check_out=end_date,
                    adults=adults,
                    rooms=rooms
                )
            except Exception as e:
                results['errors'].append(f'Hotel search error: {str(e)}')
        
        # Search activities
        if start_date and end_date:
            try:
                categories = None
                if preferences and 'activity_preferences' in preferences:
                    categories = preferences['activity_preferences']
                
                results['activities'] = self.activity_api.search_activities(
                    destination=destination,
                    start_date=start_date,
                    end_date=end_date,
                    categories=categories
                )
            except Exception as e:
                results['errors'].append(f'Activity search error: {str(e)}')
        
        return results


