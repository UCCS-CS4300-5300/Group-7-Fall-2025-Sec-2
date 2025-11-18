"""
Makcorps Hotel API Connector
Integration with Makcorps free hotel search API.
API Documentation: https://api.makcorps.com/free
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings


class MakcorpsHotelConnector:
    """
    Connector for Makcorps Hotel API.
    Provides hotel search functionality using the Makcorps free API.
    """
    
    def __init__(self):
        """Initialize Makcorps API client"""
        self.api_key = os.environ.get('HOTEL_API_KEY', getattr(settings, 'HOTEL_API_KEY', None))
        self.base_url = "https://api.makcorps.com"
        self.timeout = 30
        
        if not self.api_key:
            print("WARNING: Makcorps Hotel API key not configured. Using mock data.")
        
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
        }
    
    def search_hotels(
        self,
        location: str,
        check_in: str,
        check_out: str,
        adults: int = 1,
        rooms: int = 1,
        max_results: int = 20,
        currency: str = 'USD',
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search for hotels using Makcorps API.
        
        Args:
            location: City or destination name
            check_in: Check-in date in YYYY-MM-DD format
            check_out: Check-out date in YYYY-MM-DD format
            adults: Number of adults
            rooms: Number of rooms
            max_results: Maximum number of results to return
            currency: Currency code (default: USD)
            page: Page number for pagination (default: 1)
            
        Returns:
            List of hotel options in standardized format
        """
        
        if not self.api_key:
            print("Using mock hotel data (Makcorps API key not configured)")
            return self._get_mock_hotel_data(location, check_in, check_out, adults, rooms)
        
        try:
            # Clean location name (remove country if present, use city name)
            city_name = self._extract_city_name(location)
            
            # Build endpoint URL
            # Format: /citysearch/{city_name}/{page}/{currency}/{num_of_rooms}/{num_of_adults}/{check_in_date}/{check_out_date}
            endpoint = f"/citysearch/{city_name}/{page}/{currency}/{rooms}/{adults}/{check_in}/{check_out}"
            url = f"{self.base_url}{endpoint}"
            
            print(f"Searching Makcorps hotels: {city_name} from {check_in} to {check_out}")
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                hotels = self._parse_makcorps_response(data, location, check_in, check_out, rooms)
                print(f"Successfully retrieved {len(hotels)} hotels from Makcorps")
                return hotels[:max_results]
            else:
                print(f"Makcorps API returned status code {response.status_code}")
                if response.status_code == 401:
                    print("  [ERROR] Invalid API key - check your HOTEL_API_KEY")
                elif response.status_code == 404:
                    print(f"  [ERROR] City '{city_name}' not found")
                else:
                    print(f"  [ERROR] Response: {response.text[:200]}")
                # Fall back to mock data
                return self._get_mock_hotel_data(location, check_in, check_out, adults, rooms)
                
        except requests.exceptions.RequestException as e:
            print(f"Makcorps API request error: {str(e)}")
            return self._get_mock_hotel_data(location, check_in, check_out, adults, rooms)
        except Exception as e:
            print(f"Error searching Makcorps hotels: {str(e)}")
            return self._get_mock_hotel_data(location, check_in, check_out, adults, rooms)
    
    def _extract_city_name(self, location: str) -> str:
        """
        Extract city name from location string.
        Handles formats like "Alberta, Canada" -> "Alberta" or "Sicily, Italy" -> "Sicily"
        """
        # Remove country if present (after comma)
        if ',' in location:
            city_name = location.split(',')[0].strip()
        else:
            city_name = location.strip()
        
        # URL encode spaces as needed (API might handle this, but be safe)
        return city_name.replace(' ', '%20')
    
    def _parse_makcorps_response(
        self,
        data: Dict[str, Any],
        location: str,
        check_in: str,
        check_out: str,
        rooms: int
    ) -> List[Dict[str, Any]]:
        """
        Parse Makcorps API response into standardized format.
        
        Args:
            data: Raw JSON response from Makcorps API
            location: Original location string
            check_in: Check-in date
            check_out: Check-out date
            rooms: Number of rooms
            
        Returns:
            List of hotel dictionaries in our standard format
        """
        hotels = []
        nights = self._calculate_nights(check_in, check_out)
        
        try:
            # Makcorps API response structure may vary
            # Common structures: data.hotels, data.results, data.data, or direct array
            hotel_list = []
            
            if isinstance(data, list):
                hotel_list = data
            elif isinstance(data, dict):
                if 'hotels' in data:
                    hotel_list = data['hotels']
                elif 'results' in data:
                    hotel_list = data['results']
                elif 'data' in data:
                    hotel_list = data['data']
                elif 'items' in data:
                    hotel_list = data['items']
            
            for hotel_data in hotel_list:
                try:
                    # Extract hotel information (field names may vary)
                    hotel_id = hotel_data.get('id') or hotel_data.get('hotel_id') or hotel_data.get('_id', f'MAKCORPS-{len(hotels) + 1}')
                    name = hotel_data.get('name') or hotel_data.get('hotel_name') or hotel_data.get('title', 'Unknown Hotel')
                    
                    # Extract pricing
                    price_per_night = 0
                    if 'price_per_night' in hotel_data:
                        price_per_night = float(hotel_data['price_per_night'])
                    elif 'price' in hotel_data:
                        price_per_night = float(hotel_data['price'])
                    elif 'rate' in hotel_data:
                        price_per_night = float(hotel_data['rate'])
                    elif 'nightly_rate' in hotel_data:
                        price_per_night = float(hotel_data['nightly_rate'])
                    
                    # If price is total, divide by nights
                    if 'total_price' in hotel_data and price_per_night == 0:
                        total = float(hotel_data['total_price'])
                        price_per_night = total / nights if nights > 0 else total
                    
                    total_price = price_per_night * nights * rooms if price_per_night > 0 else 0
                    
                    # Extract rating
                    rating = None
                    if 'rating' in hotel_data:
                        rating = float(hotel_data['rating'])
                    elif 'star_rating' in hotel_data:
                        rating = float(hotel_data['star_rating'])
                    elif 'stars' in hotel_data:
                        rating = float(hotel_data['stars'])
                    
                    # Extract address
                    address = hotel_data.get('address') or hotel_data.get('location') or hotel_data.get('address_line', '')
                    
                    # Extract amenities
                    amenities = []
                    if 'amenities' in hotel_data:
                        if isinstance(hotel_data['amenities'], list):
                            amenities = hotel_data['amenities']
                        elif isinstance(hotel_data['amenities'], str):
                            amenities = hotel_data['amenities'].split(',')
                    elif 'facilities' in hotel_data:
                        if isinstance(hotel_data['facilities'], list):
                            amenities = hotel_data['facilities']
                    
                    # Extract room type
                    room_type = hotel_data.get('room_type') or hotel_data.get('room') or 'Standard Room'
                    
                    # Extract review count
                    review_count = hotel_data.get('review_count') or hotel_data.get('reviews') or hotel_data.get('num_reviews', 0)
                    
                    # Create standardized hotel dictionary
                    hotel = {
                        'id': str(hotel_id),
                        'name': name,
                        'price_per_night': price_per_night,
                        'total_price': total_price,
                        'currency': hotel_data.get('currency', 'USD'),
                        'rating': rating,
                        'review_count': int(review_count) if review_count else 0,
                        'address': address,
                        'amenities': amenities if isinstance(amenities, list) else [],
                        'room_type': room_type,
                        'cancellation_policy': hotel_data.get('cancellation_policy', ''),
                        'distance_from_center': hotel_data.get('distance', '') or hotel_data.get('distance_from_center', ''),
                        'breakfast_included': hotel_data.get('breakfast_included', False) or hotel_data.get('breakfast', False),
                        'check_in': check_in,
                        'check_out': check_out,
                        'nights': nights,
                        'is_mock': False
                    }
                    
                    hotels.append(hotel)
                    
                except Exception as e:
                    print(f"  [WARNING] Error parsing hotel: {str(e)}")
                    continue
            
            return hotels
            
        except Exception as e:
            print(f"Error parsing Makcorps response: {str(e)}")
            print(f"Response structure: {json.dumps({k: str(type(v).__name__) for k, v in list(data.items())[:10]}, indent=2)}")
            return []
    
    def _calculate_nights(self, check_in: str, check_out: str) -> int:
        """Calculate number of nights between dates"""
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
            return max(0, (check_out_date - check_in_date).days)
        except:
            return 0
    
    def _get_mock_hotel_data(
        self,
        location: str,
        check_in: str,
        check_out: str,
        adults: int,
        rooms: int
    ) -> List[Dict[str, Any]]:
        """Generate mock hotel data when Makcorps API is unavailable"""
        import random
        
        hotel_chains = [
            'Hilton', 'Marriott', 'Hyatt', 'InterContinental', 'Radisson',
            'Best Western', 'Holiday Inn', 'Sheraton', 'Courtyard'
        ]
        
        hotel_types = ['Hotel', 'Resort', 'Inn', 'Suites', 'Grand Hotel']
        amenities_pool = ['WiFi', 'Pool', 'Gym', 'Spa', 'Restaurant', 'Bar', 
                         'Room Service', 'Parking', 'Business Center', 'Pet Friendly']
        
        hotels = []
        nights = self._calculate_nights(check_in, check_out)
        
        for i in range(8):
            base_price = random.randint(80, 400)
            rating = round(random.uniform(3.5, 5.0), 1)
            chain = random.choice(hotel_chains)
            hotel_type = random.choice(hotel_types)
            
            # Select random amenities
            num_amenities = random.randint(4, 7)
            amenities = random.sample(amenities_pool, num_amenities)
            
            hotels.append({
                'id': f'MOCK-MAKCORPS-HT-{i+1}',
                'name': f'{chain} {hotel_type} {location}',
                'price_per_night': base_price,
                'total_price': base_price * nights * rooms,
                'currency': 'USD',
                'rating': rating,
                'review_count': random.randint(50, 500),
                'address': f'{random.randint(100, 9999)} {random.choice(["Main", "Central", "Park", "Ocean"])} St, {location}',
                'amenities': amenities,
                'room_type': random.choice(['Standard Room', 'Deluxe Room', 'Suite', 'Family Room', 'Executive Suite']),
                'cancellation_policy': random.choice(['Free cancellation up to 24h before', 'Non-refundable', 'Partially refundable']),
                'distance_from_center': f'{random.uniform(0.5, 10):.1f} km',
                'breakfast_included': random.choice([True, False]),
                'check_in': check_in,
                'check_out': check_out,
                'nights': nights,
                'is_mock': True
            })
        
        return hotels

