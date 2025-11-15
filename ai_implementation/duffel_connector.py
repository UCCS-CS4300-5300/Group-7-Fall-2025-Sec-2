"""
Duffel API Connector
Official integration with Duffel API for flights and accommodations.
Documentation: https://duffel.com/docs/api
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings


class DuffelAPIConnector:
    """
    Main connector for Duffel API.
    Handles flights, hotels, and other travel services.
    """

    def __init__(self):
        """Initialize Duffel API client"""
        self.api_key = os.environ.get(
            "DUFFEL_API_KEY", getattr(settings, "DUFFEL_API_KEY", None)
        )
        self.base_url = "https://api.duffel.com"
        self.timeout = 30

        if not self.api_key:
            print("WARNING: Duffel API key not configured. Using mock data.")

        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Duffel-Version": "v2",  # Updated to v2 (v1 is deprecated)
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Make HTTP request to Duffel API with error handling"""
        url = f"{self.base_url}/{endpoint}"

        try:
            if method == "GET":
                response = requests.get(
                    url, headers=self.headers, params=params, timeout=self.timeout
                )
            elif method == "POST":
                response = requests.post(
                    url, headers=self.headers, json=data, timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Duffel API request error: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except Exception:
                    print(f"Response status: {e.response.status_code}")
            return None


class DuffelFlightSearch(DuffelAPIConnector):
    """Duffel Flight search functionality"""

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        cabin_class: str = "economy",
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search for flights using Duffel API.

        Args:
            origin: Origin airport IATA code (e.g., 'JFK', 'LAX')
            destination: Destination airport IATA code (e.g., 'LHR', 'CDG')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date for round trip (optional)
            adults: Number of adult passengers
            cabin_class: 'economy', 'premium_economy', 'business', or 'first'
            max_results: Maximum number of results to return

        Returns:
            List of flight offer dictionaries
        """

        if not self.api_key:
            print("Using mock flight data (Duffel API key not configured)")
            return self._get_mock_flight_data(
                origin, destination, departure_date, return_date, adults
            )

        # Create offer request
        slices = [
            {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
            }
        ]

        # Add return slice if round trip
        if return_date:
            slices.append(
                {
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date,
                }
            )

        # Build request data
        request_data = {
            "data": {
                "slices": slices,
                "passengers": [{"type": "adult"} for _ in range(adults)],
                "cabin_class": cabin_class,
                "max_connections": 2,  # Allow up to 2 stops
            }
        }

        # Create offer request
        print(f"Creating Duffel offer request for {origin} → {destination}")
        offer_request_response = self._make_request(
            "POST", "air/offer_requests", data=request_data
        )

        if not offer_request_response:
            print("Failed to create offer request, using mock data")
            return self._get_mock_flight_data(
                origin, destination, departure_date, return_date, adults
            )

        offer_request_id = offer_request_response.get("data", {}).get("id")

        if not offer_request_id:
            print("No offer request ID returned, using mock data")
            return self._get_mock_flight_data(
                origin, destination, departure_date, return_date, adults
            )

        # Wait a moment for offers to be generated
        import time

        time.sleep(2)

        # Get offers
        print(f"Fetching offers for request {offer_request_id}")
        offers_response = self._make_request(
            "GET", f"air/offers?offer_request_id={offer_request_id}"
        )

        if not offers_response:
            print("Failed to fetch offers, using mock data")
            return self._get_mock_flight_data(
                origin, destination, departure_date, return_date, adults
            )

        offers = offers_response.get("data", [])

        if not offers:
            print("No offers returned, using mock data")
            return self._get_mock_flight_data(
                origin, destination, departure_date, return_date, adults
            )

        # Parse and format offers
        formatted_flights = []
        for offer in offers[:max_results]:
            formatted = self._parse_duffel_offer(offer)
            if formatted:
                formatted_flights.append(formatted)

        print(
            f"Successfully retrieved {len(formatted_flights)} flight offers from Duffel"
        )
        return formatted_flights

    def _parse_duffel_offer(self, offer: Dict) -> Optional[Dict[str, Any]]:
        """Parse Duffel offer into standardized format"""
        try:
            # Get basic offer info
            offer_id = offer.get("id")
            total_amount = float(offer.get("total_amount", 0))
            currency = offer.get("total_currency", "USD")

            # Get slice information (flight segments)
            slices = offer.get("slices", [])
            if not slices:
                return None

            first_slice = slices[0]
            segments = first_slice.get("segments", [])

            if not segments:
                return None

            first_segment = segments[0]
            last_segment = segments[-1]

            # Get airline info
            operating_carrier = first_segment.get("operating_carrier", {})
            airline_code = operating_carrier.get("iata_code", "Unknown")
            airline_name = operating_carrier.get("name", "Unknown Airline")

            # Get departure and arrival info
            departure = first_segment.get("departing_at", "")
            arrival = last_segment.get("arriving_at", "")

            # Calculate total duration
            duration = first_slice.get("duration", "")

            # Count stops (segments - 1)
            stops = len(segments) - 1

            # Get cabin class
            cabin_class = first_segment.get("passengers", [{}])[0].get(
                "cabin_class_marketing_name", "Economy"
            )

            # Get aircraft info
            aircraft = first_segment.get("aircraft", {})
            aircraft_name = aircraft.get("name", "N/A")

            return {
                "id": offer_id,
                "price": total_amount,
                "currency": currency,
                "airline": airline_code,
                "airline_name": airline_name,
                "departure_time": departure,
                "arrival_time": arrival,
                "duration": duration,
                "stops": stops,
                "booking_class": cabin_class,
                "aircraft": aircraft_name,
                "seats_available": offer.get("available_services", "Limited"),
                "route": f"{first_segment.get('origin', {}).get('iata_code')} → {last_segment.get('destination', {}).get('iata_code')}",
                "is_mock": False,
                "raw_data": offer,  # Store full offer for booking later
            }

        except Exception as e:
            print(f"Error parsing Duffel offer: {str(e)}")
            return None

    def _get_mock_flight_data(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        adults: int,
    ) -> List[Dict[str, Any]]:
        """Generate mock flight data when Duffel API is unavailable"""
        import random

        airlines = [
            {"code": "AA", "name": "American Airlines"},
            {"code": "UA", "name": "United Airlines"},
            {"code": "DL", "name": "Delta Air Lines"},
            {"code": "SW", "name": "Southwest Airlines"},
            {"code": "B6", "name": "JetBlue Airways"},
            {"code": "AS", "name": "Alaska Airlines"},
        ]

        base_price = 250

        flights = []
        for i in range(5):
            airline = random.choice(airlines)
            price = (base_price + random.randint(-100, 300)) * adults
            stops = random.choice([0, 1, 2])

            flights.append(
                {
                    "id": f"MOCK-DUFFEL-FL-{i+1}",
                    "price": price,
                    "currency": "USD",
                    "airline": airline["code"],
                    "airline_name": airline["name"],
                    "departure_time": f"{departure_date}T{random.randint(6, 20):02d}:{random.choice([0, 30]):02d}:00",
                    "arrival_time": f"{departure_date}T{random.randint(10, 23):02d}:{random.choice([0, 30]):02d}:00",
                    "duration": f"PT{random.randint(2, 8)}H{random.randint(0, 59)}M",
                    "stops": stops,
                    "booking_class": random.choice(
                        ["Economy", "Premium Economy", "Business"]
                    ),
                    "aircraft": random.choice(
                        ["Boeing 737", "Airbus A320", "Boeing 787", "Airbus A350"]
                    ),
                    "seats_available": random.randint(1, 9),
                    "route": f"{origin} → {destination}",
                    "is_mock": True,
                }
            )

        return flights


class DuffelAccommodationSearch(DuffelAPIConnector):
    """
    Duffel Accommodation (Stays) search functionality.
    Note: Duffel Stays is a newer feature, check availability.
    """

    def search_accommodations(
        self,
        location: str,
        check_in: str,
        check_out: str,
        adults: int = 1,
        rooms: int = 1,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search for accommodations using Duffel Stays API.

        Args:
            location: City or destination name
            check_in: Check-in date in YYYY-MM-DD format
            check_out: Check-out date in YYYY-MM-DD format
            adults: Number of adults
            rooms: Number of rooms
            max_results: Maximum number of results

        Returns:
            List of accommodation options
        """

        if not self.api_key:
            print("Using mock hotel data (Duffel API key not configured)")
            return self._get_mock_hotel_data(
                location, check_in, check_out, adults, rooms
            )

        # Note: As of now, Duffel's Stays API might be in beta or require special access
        # Check Duffel documentation for current status
        # For now, we'll use mock data and prepare structure for when available

        print(
            "Duffel Stays API - using mock data (API may not be publicly available yet)"
        )
        return self._get_mock_hotel_data(location, check_in, check_out, adults, rooms)

    def _get_mock_hotel_data(
        self, location: str, check_in: str, check_out: str, adults: int, rooms: int
    ) -> List[Dict[str, Any]]:
        """Generate realistic mock hotel data"""
        import random

        hotel_chains = [
            "Hilton",
            "Marriott",
            "Hyatt",
            "InterContinental",
            "Radisson",
            "Best Western",
            "Holiday Inn",
            "Sheraton",
            "Courtyard",
        ]

        hotel_types = ["Hotel", "Resort", "Inn", "Suites", "Grand Hotel"]
        amenities_pool = [
            "WiFi",
            "Pool",
            "Gym",
            "Spa",
            "Restaurant",
            "Bar",
            "Room Service",
            "Parking",
            "Business Center",
            "Pet Friendly",
        ]

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

            hotels.append(
                {
                    "id": f"MOCK-DUFFEL-HT-{i+1}",
                    "name": f"{chain} {hotel_type} {location}",
                    "price_per_night": base_price,
                    "total_price": base_price * nights * rooms,
                    "currency": "USD",
                    "rating": rating,
                    "review_count": random.randint(50, 500),
                    "address": f'{random.randint(100, 9999)} {random.choice(["Main", "Central", "Park", "Ocean"])} St, {location}',
                    "amenities": amenities,
                    "room_type": random.choice(
                        [
                            "Standard Room",
                            "Deluxe Room",
                            "Suite",
                            "Family Room",
                            "Executive Suite",
                        ]
                    ),
                    "cancellation_policy": random.choice(
                        [
                            "Free cancellation up to 24h before",
                            "Non-refundable",
                            "Partially refundable",
                        ]
                    ),
                    "distance_from_center": f"{random.uniform(0.5, 10):.1f} km",
                    "breakfast_included": random.choice([True, False]),
                    "check_in": check_in,
                    "check_out": check_out,
                    "nights": nights,
                    "is_mock": True,
                }
            )

        return hotels

    def _calculate_nights(self, check_in: str, check_out: str) -> int:
        """Calculate number of nights between dates"""
        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
            return max(1, (check_out_date - check_in_date).days)
        except Exception:
            return 1


class DuffelPlaceSearch(DuffelAPIConnector):
    """Search for places/airports using Duffel API"""

    def search_places(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for airports or cities by name.
        Useful for autocomplete and location lookup.

        Args:
            query: Search query (e.g., 'New York', 'Paris', 'JFK')

        Returns:
            List of matching places with IATA codes
        """

        if not self.api_key:
            return self._get_mock_places(query)

        response = self._make_request(
            "GET", "places/suggestions", params={"query": query}
        )

        if not response:
            return self._get_mock_places(query)

        places = []
        for place in response.get("data", []):
            places.append(
                {
                    "id": place.get("id"),
                    "name": place.get("name"),
                    "iata_code": place.get("iata_code"),
                    "iata_country_code": place.get("iata_country_code"),
                    "city_name": place.get("city_name"),
                    "type": place.get("type"),  # 'airport' or 'city'
                }
            )

        return places

    def _get_mock_places(self, query: str) -> List[Dict[str, Any]]:
        """Mock place data for common airports/cities"""
        common_places = [
            {
                "id": "arp_jfk",
                "name": "John F. Kennedy International Airport",
                "iata_code": "JFK",
                "city_name": "New York",
                "type": "airport",
            },
            {
                "id": "arp_lax",
                "name": "Los Angeles International Airport",
                "iata_code": "LAX",
                "city_name": "Los Angeles",
                "type": "airport",
            },
            {
                "id": "arp_lhr",
                "name": "London Heathrow Airport",
                "iata_code": "LHR",
                "city_name": "London",
                "type": "airport",
            },
            {
                "id": "arp_cdg",
                "name": "Charles de Gaulle Airport",
                "iata_code": "CDG",
                "city_name": "Paris",
                "type": "airport",
            },
            {
                "id": "arp_nrt",
                "name": "Narita International Airport",
                "iata_code": "NRT",
                "city_name": "Tokyo",
                "type": "airport",
            },
            {
                "id": "arp_dxb",
                "name": "Dubai International Airport",
                "iata_code": "DXB",
                "city_name": "Dubai",
                "type": "airport",
            },
            {
                "id": "arp_sfo",
                "name": "San Francisco International Airport",
                "iata_code": "SFO",
                "city_name": "San Francisco",
                "type": "airport",
            },
            {
                "id": "arp_mia",
                "name": "Miami International Airport",
                "iata_code": "MIA",
                "city_name": "Miami",
                "type": "airport",
            },
        ]

        query_lower = query.lower()
        matches = [
            place
            for place in common_places
            if query_lower in place["name"].lower()
            or query_lower in place["city_name"].lower()
            or query_lower in place["iata_code"].lower()
        ]

        return matches if matches else common_places[:3]


class DuffelAggregator:
    """
    Aggregator that combines Duffel flight and accommodation searches
    with other travel APIs for a complete solution.
    """

    def __init__(self):
        self.flight_search = DuffelFlightSearch()
        self.accommodation_search = DuffelAccommodationSearch()
        self.place_search = DuffelPlaceSearch()

    def search_all(
        self,
        destination: str,
        origin: Optional[str] = None,
        start_date: str = None,
        end_date: str = None,
        adults: int = 1,
        rooms: int = 1,
        preferences: Optional[Dict] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across all travel services using Duffel API.

        Args:
            destination: Destination location or IATA code
            origin: Origin location or IATA code (for flights)
            start_date: Trip start date
            end_date: Trip end date
            adults: Number of adults
            rooms: Number of hotel rooms
            preferences: Additional search preferences

        Returns:
            Dictionary containing results from all services
        """

        results = {"flights": [], "hotels": [], "activities": [], "errors": []}

        # Convert city names to IATA codes if needed
        if origin and len(origin) > 3:
            origin_places = self.place_search.search_places(origin)
            origin = origin_places[0]["iata_code"] if origin_places else origin

        if destination and len(destination) > 3:
            dest_places = self.place_search.search_places(destination)
            destination_code = (
                dest_places[0]["iata_code"] if dest_places else destination
            )
            destination_name = (
                dest_places[0]["city_name"] if dest_places else destination
            )
        else:
            destination_code = destination
            destination_name = destination

        # Search flights with Duffel
        if origin and start_date:
            try:
                cabin_class = "economy"
                if preferences and preferences.get("cabin_class"):
                    cabin_class = preferences["cabin_class"]

                print(f"Searching Duffel flights: {origin} → {destination_code}")
                results["flights"] = self.flight_search.search_flights(
                    origin=origin,
                    destination=destination_code,
                    departure_date=start_date,
                    return_date=end_date,
                    adults=adults,
                    cabin_class=cabin_class,
                )
                print(f"Found {len(results['flights'])} flights")
            except Exception as e:
                error_msg = f"Duffel flight search error: {str(e)}"
                print(error_msg)
                results["errors"].append(error_msg)
                results["flights"] = self.flight_search._get_mock_flight_data(
                    origin, destination_code, start_date, end_date, adults
                )

        # Search hotels/accommodations
        if start_date and end_date:
            try:
                print(f"Searching accommodations in {destination_name}")
                results["hotels"] = self.accommodation_search.search_accommodations(
                    location=destination_name,
                    check_in=start_date,
                    check_out=end_date,
                    adults=adults,
                    rooms=rooms,
                )
                print(f"Found {len(results['hotels'])} hotels")
            except Exception as e:
                error_msg = f"Hotel search error: {str(e)}"
                print(error_msg)
                results["errors"].append(error_msg)

        # Activities - use existing connector (Duffel doesn't have activities yet)
        from .api_connectors import ActivityAPIConnector

        if start_date and end_date:
            try:
                activity_api = ActivityAPIConnector()
                categories = None
                if preferences and "activity_preferences" in preferences:
                    categories = preferences["activity_preferences"]

                print(f"Searching activities in {destination_name}")
                results["activities"] = activity_api.search_activities(
                    destination=destination_name,
                    start_date=start_date,
                    end_date=end_date,
                    categories=categories,
                )
                print(f"Found {len(results['activities'])} activities")
            except Exception as e:
                error_msg = f"Activity search error: {str(e)}"
                print(error_msg)
                results["errors"].append(error_msg)

        return results

    def get_airport_code(self, city_or_code: str) -> str:
        """
        Convert city name to IATA airport code.

        Args:
            city_or_code: City name or IATA code

        Returns:
            IATA code
        """
        if len(city_or_code) == 3 and city_or_code.isupper():
            return city_or_code

        places = self.place_search.search_places(city_or_code)
        return places[0]["iata_code"] if places else city_or_code
