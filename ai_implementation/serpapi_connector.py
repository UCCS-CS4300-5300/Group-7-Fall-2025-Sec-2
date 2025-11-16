"""
SerpApi Connector for Google Flights
Uses SerpApi to search for flights via Google Flights API.
Documentation: https://serpapi.com/google-flights-api
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings


class SerpApiFlightsConnector:
    """
    Connector for SerpApi Google Flights search.
    """
    
    def __init__(self):
        """Initialize SerpApi client"""
        # Get API key from environment variable first
        self.api_key = os.environ.get('SERP_API_KEY', None)
        
        # Try to get from Django settings if available
        if not self.api_key:
            try:
                self.api_key = getattr(settings, 'SERP_API_KEY', None)
            except Exception:
                # Django settings not configured yet, that's okay
                pass
        
        self.base_url = "https://serpapi.com/search.json"
        self.timeout = 30
        
        # Note: API key is now set, but if it becomes empty somehow, warn
        if not self.api_key:
            print("WARNING: SerpApi API key not configured. Using mock data.")
        
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'GroupGo-TravelApp/1.0'
        }
    
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
        Search for flights using SerpApi Google Flights.
        
        Args:
            origin: Origin location (city name or IATA code)
            destination: Destination location (city name or IATA code)
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (optional, for round trip)
            adults: Number of adult passengers
            max_results: Maximum number of results to return
            
        Returns:
            List of flight options in the format expected by the application
        """
        
        if not self.api_key:
            print("Using mock flight data (SerpApi API key not configured)")
            return self._get_mock_flight_data(origin, destination, departure_date, return_date, adults, max_results)
        
        try:
            # Format dates for SerpApi (YYYY-MM-DD format)
            # SerpApi Google Flights uses departure_id and arrival_id for airport codes or city names
            origin_code = self._get_airport_code(origin)
            dest_code = self._get_airport_code(destination)
            
            params = {
                'engine': 'google_flights',
                'api_key': self.api_key,
                'departure_id': origin_code,
                'arrival_id': dest_code,
                'outbound_date': departure_date,
                'adults': adults,
                'currency': 'USD',
                'hl': 'en',
                'gl': 'us'
            }
            
            # Add return date if provided (round trip)
            if return_date:
                params['return_date'] = return_date
            
            # Debug: print params (without API key)
            debug_params = {k: v for k, v in params.items() if k != 'api_key'}
            print(f"SerpApi request params: {debug_params}")
            
            print(f"Searching SerpApi Google Flights: {origin} -> {destination} on {departure_date}")
            # Note: Do not log API key, even masked, for security compliance
            
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=self.timeout)
            
            # Check for API errors in response
            if response.status_code != 200:
                print(f"  [ERROR] SerpApi returned status code {response.status_code}")
                error_text = response.text[:1000] if hasattr(response, 'text') else str(response)
                print(f"  [ERROR] Error response: {error_text}")
                print(f"  [ERROR] Request URL: {response.url if hasattr(response, 'url') else 'N/A'}")
                # DO NOT use mock data - raise error so user knows API is failing
                raise Exception(f"SerpApi returned status {response.status_code}: {error_text[:200]}")
            
            data = response.json()
            
            # Log response structure for debugging
            print(f"  [DEBUG] SerpApi response keys: {list(data.keys())[:10]}")
            
            # Check for errors in the JSON response
            if 'error' in data:
                error_msg = data.get('error', 'Unknown error')
                print(f"  [ERROR] SerpApi API error: {error_msg}")
                # DO NOT use mock data - raise error so user knows API is failing
                raise Exception(f"SerpApi API error: {error_msg}")
            
            flights = self._parse_serpapi_response(data, origin, destination, departure_date, return_date, adults)
            
            if not flights:
                print(f"  [ERROR] No flights found in SerpApi response")
                print(f"  [DEBUG] Response structure: {json.dumps({k: str(type(v).__name__) for k, v in list(data.items())[:10]}, indent=2)}")
                # DO NOT use mock data - raise error so user knows parsing failed
                raise Exception(f"No flights found in SerpApi response for {origin} -> {destination}")
            
            print(f"  [SUCCESS] Found {len(flights)} flights from SerpApi")
            return flights[:max_results]
            
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] SerpApi request error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Re-raise to see actual error - don't hide it with mock data
            raise Exception(f"SerpApi request failed: {str(e)}")
        except Exception as e:
            # Check if this is an exception we raised (don't re-raise those)
            if "SerpApi" in str(e) or "No flights found" in str(e):
                raise
            print(f"  [ERROR] SerpApi Google Flights search error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Re-raise to see actual error
            raise Exception(f"SerpApi search failed: {str(e)}")
    
    def _parse_serpapi_response(
        self,
        data: Dict[str, Any],
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        adults: int
    ) -> List[Dict[str, Any]]:
        """
        Parse SerpApi Google Flights response into our standard format.
        
        Args:
            data: Raw JSON response from SerpApi
            origin: Origin location
            destination: Destination location
            departure_date: Departure date
            return_date: Return date (optional)
            adults: Number of adults
            
        Returns:
            List of flight dictionaries in our standard format
        """
        flights = []
        
        try:
            # SerpApi Google Flights response structure
            # Check for best_flights, other_flights, or flights array
            flight_options = []
            
            if 'best_flights' in data:
                flight_options.extend(data['best_flights'])
            
            if 'other_flights' in data:
                flight_options.extend(data['other_flights'])
            
            # Alternative structure
            if 'flights' in data:
                if isinstance(data['flights'], list):
                    flight_options.extend(data['flights'])
                elif isinstance(data['flights'], dict):
                    if 'best_flights' in data['flights']:
                        flight_options.extend(data['flights']['best_flights'])
                    if 'other_flights' in data['flights']:
                        flight_options.extend(data['flights']['other_flights'])
            
            for flight_option in flight_options:
                try:
                    # Extract flight information
                    flight_id = flight_option.get('flight_id', f'SERP-{len(flights) + 1}')
                    
                    # Get price (per person or total)
                    price_info = flight_option.get('price', {})
                    if isinstance(price_info, dict):
                        total_price = price_info.get('total', 0)
                        if total_price == 0:
                            # Try alternative price fields
                            total_price = price_info.get('value', 0) or price_info.get('amount', 0)
                    else:
                        total_price = float(price_info) if price_info else 0
                    
                    # If price is per person, multiply by adults
                    if total_price > 0 and adults > 1:
                        # Check if price is per person (common in SerpApi)
                        price_per_person = flight_option.get('price_per_person', {})
                        if price_per_person and isinstance(price_per_person, dict):
                            per_person = price_per_person.get('total', 0) or price_per_person.get('value', 0)
                            if per_person > 0:
                                total_price = per_person * adults
                    
                    # Extract flight details
                    flights_data = flight_option.get('flights', [])
                    if not flights_data:
                        continue
                    
                    # Get first flight leg
                    first_flight = flights_data[0] if flights_data else {}
                    last_flight = flights_data[-1] if flights_data else {}
                    
                    # Extract times - SerpApi returns time in various formats
                    dep_airport = first_flight.get('departure_airport', {})
                    arr_airport = last_flight.get('arrival_airport', {})
                    
                    departure_time_str = dep_airport.get('time', '') or dep_airport.get('datetime', '')
                    arrival_time_str = arr_airport.get('time', '') or arr_airport.get('datetime', '')
                    
                    print(f"  [DEBUG] Raw departure_time_str: {departure_time_str}")
                    print(f"  [DEBUG] Raw arrival_time_str: {arrival_time_str}")
                    
                    # Extract airline
                    airline_info = first_flight.get('airline', '')
                    if isinstance(airline_info, dict):
                        airline = airline_info.get('name', 'Unknown')
                    else:
                        airline = str(airline_info) if airline_info else 'Unknown'
                    
                    # Calculate stops
                    stops = max(0, len(flights_data) - 1)
                    
                    # Extract booking class/cabin class - try multiple possible fields
                    booking_class = 'Economy'  # Default
                    # Check flight_option level
                    if 'cabin_class' in flight_option:
                        booking_class = flight_option['cabin_class']
                    elif 'class' in flight_option:
                        booking_class = flight_option['class']
                    elif 'booking_class' in flight_option:
                        booking_class = flight_option['booking_class']
                    # Check first flight segment level
                    elif 'cabin_class' in first_flight:
                        booking_class = first_flight['cabin_class']
                    elif 'class' in first_flight:
                        booking_class = first_flight['class']
                    elif 'booking_class' in first_flight:
                        booking_class = first_flight['booking_class']
                    # Check price_info for class
                    elif isinstance(price_info, dict) and 'cabin_class' in price_info:
                        booking_class = price_info['cabin_class']
                    
                    # Normalize booking class name
                    if booking_class:
                        booking_class = booking_class.title()  # Capitalize first letter of each word
                        # Map common variations
                        booking_class_map = {
                            'Economy': 'Economy',
                            'Premium Economy': 'Premium Economy',
                            'Business': 'Business',
                            'First': 'First',
                            'First Class': 'First',
                            'Business Class': 'Business',
                            'Premium': 'Premium Economy',
                            'Coach': 'Economy'
                        }
                        booking_class = booking_class_map.get(booking_class, booking_class)
                    
                    # Extract duration - try multiple sources
                    duration = flight_option.get('total_duration', 0)
                    duration_seconds = 0
                    
                    # If total_duration is provided and seems reasonable (at least 30 minutes)
                    if duration and duration >= 1800:  # At least 30 minutes
                        duration_seconds = duration
                    else:
                        # Calculate duration from departure and arrival times
                        try:
                            dep_time_str = departure_time_str
                            arr_time_str = arrival_time_str
                            
                            if dep_time_str and arr_time_str:
                                # Parse times using _parse_time which handles all formats
                                from datetime import datetime as dt
                                
                                try:
                                    # Use _parse_time to get properly formatted datetime strings
                                    dep_parsed = self._parse_time(dep_time_str, departure_date)
                                    arr_parsed = self._parse_time(arr_time_str, departure_date)
                                    
                                    # Parse the formatted strings to datetime objects
                                    # Remove timezone if present for calculation
                                    dep_clean = dep_parsed.replace('+00:00', '').replace('Z', '')
                                    arr_clean = arr_parsed.replace('+00:00', '').replace('Z', '')
                                    
                                    # Try parsing ISO format
                                    try:
                                        dep_dt = dt.fromisoformat(dep_clean)
                                    except ValueError:
                                        # Fallback to strptime
                                        if 'T' in dep_clean:
                                            dep_dt = dt.strptime(dep_clean.split('T')[0] + ' ' + dep_clean.split('T')[1], "%Y-%m-%d %H:%M:%S")
                                        else:
                                            dep_dt = dt.strptime(dep_clean, "%Y-%m-%d %H:%M:%S")
                                    
                                    try:
                                        arr_dt = dt.fromisoformat(arr_clean)
                                    except ValueError:
                                        # Fallback to strptime
                                        if 'T' in arr_clean:
                                            arr_dt = dt.strptime(arr_clean.split('T')[0] + ' ' + arr_clean.split('T')[1], "%Y-%m-%d %H:%M:%S")
                                        else:
                                            arr_dt = dt.strptime(arr_clean, "%Y-%m-%d %H:%M:%S")
                                    
                                    # Check if arrival is before departure (next day arrival)
                                    if arr_dt <= dep_dt:
                                        # Arrival is likely next day - add 1 day
                                        from datetime import timedelta
                                        arr_dt += timedelta(days=1)
                                    
                                    # Calculate duration in seconds
                                    duration_delta = arr_dt - dep_dt
                                    duration_seconds = int(duration_delta.total_seconds())
                                    
                                    # Validate duration is reasonable (at least 30 minutes, at most 30 hours)
                                    if duration_seconds < 1800:
                                        print(f"  [WARNING] Calculated duration ({duration_seconds}s) too short, using minimum 30 minutes")
                                        duration_seconds = 1800
                                    elif duration_seconds > 108000:  # 30 hours
                                        print(f"  [WARNING] Calculated duration ({duration_seconds}s) too long, capping at 30 hours")
                                        duration_seconds = 108000
                                    
                                    print(f"  [DEBUG] Parsed times - Dep: {dep_dt}, Arr: {arr_dt}, Duration: {duration_seconds}s ({duration_seconds//3600}h {(duration_seconds%3600)//60}m)")
                                        
                                except (ValueError, AttributeError) as e:
                                    print(f"  [WARNING] Could not parse flight times: '{dep_time_str}' -> '{dep_parsed}', '{arr_time_str}' -> '{arr_parsed}', error: {str(e)}")
                                    # Fallback: estimate based on typical flight times
                                    if stops == 0:
                                        duration_seconds = 7200  # 2 hours for direct flights
                                    else:
                                        duration_seconds = 14400  # 4 hours for flights with stops
                        except Exception as e:
                            print(f"  [WARNING] Error calculating duration from times: {str(e)}")
                            # Fallback: estimate based on typical flight times
                            if stops == 0:
                                duration_seconds = 7200  # 2 hours for direct flights
                            else:
                                duration_seconds = 14400  # 4 hours for flights with stops
                    
                    # Convert seconds to hours and minutes
                    if duration_seconds > 0:
                        hours = duration_seconds // 3600
                        minutes = (duration_seconds % 3600) // 60
                        duration_str = f'{hours}h {minutes}m'
                    else:
                        # Final fallback
                        if stops == 0:
                            duration_str = '2h 0m'  # Default 2 hours for direct flights
                        else:
                            duration_str = '4h 0m'  # Default 4 hours for flights with stops
                    
                    # Parse times properly first
                    parsed_dep_time = self._parse_time(departure_time_str, departure_date)
                    parsed_arr_time = self._parse_time(arrival_time_str, departure_date)
                    
                    # If arrival appears to be before departure (next day), fix it
                    from datetime import datetime as dt
                    try:
                        dep_dt_check = dt.fromisoformat(parsed_dep_time.replace('+00:00', '').replace('Z', ''))
                        arr_dt_check = dt.fromisoformat(parsed_arr_time.replace('+00:00', '').replace('Z', ''))
                        
                        # If arrival is earlier or same as departure, it's next day
                        if arr_dt_check <= dep_dt_check:
                            from datetime import timedelta
                            arr_dt_check += timedelta(days=1)
                            parsed_arr_time = arr_dt_check.strftime("%Y-%m-%dT%H:%M:%S")
                    except:
                        pass
                    
                    # Create flight dictionary in our format
                    flight = {
                        'id': f'SERP-{flight_id}',
                        'price': float(total_price),
                        'currency': 'USD',
                        'airline': airline[:50],  # Limit airline name length
                        'airline_name': airline,
                        'departure_time': parsed_dep_time,
                        'arrival_time': parsed_arr_time,
                        'duration': duration_str,
                        'stops': stops,
                        'booking_class': booking_class,
                        'seats_available': str(adults),  # Assume seats available match adults
                        'route': f'{origin} -> {destination}',
                        'is_mock': False,
                        'total_amount': float(total_price),  # For compatibility
                        'owner': {}  # For compatibility
                    }
                    
                    flights.append(flight)
                    
                except Exception as e:
                    print(f"  [WARNING] Error parsing flight option {len(flights) + 1}: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    continue
            
            print(f"  [DEBUG] Successfully parsed {len(flights)} flights from {len(flight_options)} flight options")
            return flights
            
        except Exception as e:
            print(f"  [ERROR] Error parsing SerpApi response: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if 'data' in locals():
                print(f"  [DEBUG] Response data structure: {json.dumps({k: str(type(v).__name__) + (' (len=' + str(len(v)) + ')' if hasattr(v, '__len__') else '') for k, v in list(data.items())[:15]}, indent=2)}")
            raise
    
    def _parse_time(self, time_str: str, date_str: str) -> str:
        """
        Parse time string and combine with date.
        Handles multiple formats from SerpApi:
        - "HH:MM" (just time)
        - "YYYY-MM-DD HH:MM" (date and time)
        - "YYYY-MM-DDTHH:MM:SS" (ISO format)
        - "YYYY-MM-DDTHH:MM" (ISO without seconds)
        """
        if not time_str:
            return f'{date_str}T12:00:00'
        
        from datetime import datetime as dt
        
        try:
            # If already in ISO format with 'T', return as-is (might need timezone fix)
            if 'T' in time_str:
                # Check if it has timezone
                if time_str.endswith('Z'):
                    return time_str.replace('Z', '+00:00')
                elif '+' in time_str or time_str.count('-') >= 3:
                    # Has timezone info
                    return time_str
                else:
                    # ISO format without timezone - return as-is
                    return time_str
            
            # Check if it's "YYYY-MM-DD HH:MM" format (date + time)
            if ' ' in time_str and len(time_str) > 10:
                # It's "YYYY-MM-DD HH:MM" or "YYYY-MM-DD HH:MM:SS"
                try:
                    # Try with seconds first
                    if len(time_str.split()[-1].split(':')) == 3:
                        parsed_dt = dt.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    else:
                        # No seconds
                        parsed_dt = dt.strptime(time_str, "%Y-%m-%d %H:%M")
                    return parsed_dt.strftime("%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    pass
            
            # Check if it's just "HH:MM" format (time only)
            if ':' in time_str and len(time_str) <= 5:
                # It's just time - combine with date
                time_parts = time_str.split(':')
                if len(time_parts) == 2:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    return f'{date_str}T{hours:02d}:{minutes:02d}:00'
            
            # Try parsing as full datetime
            try:
                parsed_dt = dt.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                return parsed_dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                try:
                    parsed_dt = dt.strptime(time_str, "%Y-%m-%d %H:%M")
                    return parsed_dt.strftime("%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    pass
            
            # If all else fails, return default
            print(f"  [WARNING] Could not parse time format: '{time_str}', using default")
            return f'{date_str}T12:00:00'
            
        except Exception as e:
            print(f"  [WARNING] Error parsing time '{time_str}': {str(e)}")
            return f'{date_str}T12:00:00'
    
    def _get_airport_code(self, location: str) -> str:
        """
        Convert location name to airport code for SerpApi.
        SerpApi can accept city names or IATA codes.
        Handles formats like "City, Country" and extracts just the city.
        """
        # If it's already a 3-letter uppercase code, return as-is
        if len(location) == 3 and location.isupper():
            return location
        
        # Extract city name if it's in "City, Country" format
        location_clean = location.strip()
        if ',' in location_clean:
            # Take the part before the comma (the city/region)
            location_clean = location_clean.split(',')[0].strip()
        
        location_lower = location_clean.lower().strip()
        
        # Expanded airport code mapping
        # Includes major cities and regions
        common_codes = {
            # US Cities
            'new york': 'JFK',
            'los angeles': 'LAX',
            'chicago': 'ORD',
            'miami': 'MIA',
            'san francisco': 'SFO',
            'las vegas': 'LAS',
            'boston': 'BOS',
            'seattle': 'SEA',
            'atlanta': 'ATL',
            'dallas': 'DFW',
            'denver': 'DEN',
            'houston': 'IAH',
            'phoenix': 'PHX',
            'philadelphia': 'PHL',
            'san diego': 'SAN',
            'minneapolis': 'MSP',
            'detroit': 'DTW',
            'portland': 'PDX',
            
            # European Cities
            'london': 'LHR',
            'paris': 'CDG',
            'rome': 'FCO',
            'madrid': 'MAD',
            'barcelona': 'BCN',
            'amsterdam': 'AMS',
            'berlin': 'BER',
            'munich': 'MUC',
            'frankfurt': 'FRA',
            'vienna': 'VIE',
            'zurich': 'ZRH',
            'milan': 'MXP',
            'istanbul': 'IST',
            'dublin': 'DUB',
            'lisbon': 'LIS',
            'athens': 'ATH',
            'prague': 'PRG',
            
            # Italian regions/cities - map regions to major airports
            'sicily': 'PMO',  # Palermo - main airport in Sicily
            'sicilia': 'PMO',
            'tuscany': 'FLR',  # Florence
            'toscana': 'FLR',
            'venice': 'VCE',
            'venezia': 'VCE',
            'naples': 'NAP',
            'napoli': 'NAP',
            'bologna': 'BLQ',
            
            # Canadian provinces/cities
            'alberta': 'YYC',  # Calgary - major airport in Alberta
            'calgary': 'YYC',
            'edmonton': 'YEG',
            'toronto': 'YYZ',
            'vancouver': 'YVR',
            'montreal': 'YUL',
            'ottawa': 'YOW',
            'quebec': 'YQB',
            'winnipeg': 'YWG',
            
            # Asian Cities
            'tokyo': 'NRT',
            'beijing': 'PEK',
            'shanghai': 'PVG',
            'hong kong': 'HKG',
            'singapore': 'SIN',
            'bangkok': 'BKK',
            'seoul': 'ICN',
            'delhi': 'DEL',
            'mumbai': 'BOM',
            'dubai': 'DXB',
            'doha': 'DOH',
            'abu dhabi': 'AUH',
            
            # Other Major Cities
            'sydney': 'SYD',
            'melbourne': 'MEL',
            'auckland': 'AKL',
            'cairo': 'CAI',
            'johannesburg': 'JNB',
            'cape town': 'CPT',
            'mexico city': 'MEX',
            'sao paulo': 'GRU',
            'rio de janeiro': 'GIG',
            'buenos aires': 'EZE',
            'lima': 'LIM',
        }
        
        # Check if we have a mapping
        airport_code = common_codes.get(location_lower)
        
        if airport_code:
            return airport_code
        
        # If no mapping found, return the cleaned city name
        # SerpApi can accept city names directly, so this might work
        return location_clean
    
    def _get_mock_flight_data(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        adults: int,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Generate mock flight data when SerpApi is unavailable"""
        import random
        
        airlines = [
            {'code': 'AA', 'name': 'American Airlines'},
            {'code': 'UA', 'name': 'United Airlines'},
            {'code': 'DL', 'name': 'Delta Air Lines'},
            {'code': 'SW', 'name': 'Southwest Airlines'},
            {'code': 'B6', 'name': 'JetBlue Airways'},
            {'code': 'AS', 'name': 'Alaska Airlines'},
            {'code': 'WN', 'name': 'Southwest Airlines'},
            {'code': 'NK', 'name': 'Spirit Airlines'},
        ]
        
        base_price = 250
        
        flights = []
        for i in range(min(max_results, 8)):
            airline = random.choice(airlines)
            price = (base_price + random.randint(-100, 300)) * adults
            stops = random.choice([0, 1, 2])
            
            # Generate reasonable departure and arrival times
            dep_hour = random.randint(6, 16)  # Departures between 6 AM and 4 PM
            dep_minute = random.choice([0, 15, 30, 45])
            
            # Duration: 1-3 hours for short domestic flights, 2-8 hours for longer flights
            # For Denver to Alberta: ~2-3 hours, for Denver to Sicily: ~10-12 hours
            if 'alberta' in destination.lower() or 'canada' in destination.lower():
                flight_hours = random.randint(2, 4)  # 2-4 hours
            elif 'italy' in destination.lower() or 'europe' in destination.lower():
                flight_hours = random.randint(10, 14)  # 10-14 hours for transatlantic
            else:
                flight_hours = random.randint(2, 8)  # Default 2-8 hours
            
            flight_minutes = random.randint(0, 59)
            
            # Calculate arrival time
            arr_hour = dep_hour + flight_hours
            arr_minute = dep_minute + flight_minutes
            if arr_minute >= 60:
                arr_hour += 1
                arr_minute -= 60
            if arr_hour >= 24:
                arr_hour -= 24
                # Next day arrival - format accordingly
                from datetime import datetime, timedelta
                dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
                arr_date = dep_date + timedelta(days=1)
                arrival_date_str = arr_date.strftime("%Y-%m-%d")
            else:
                arrival_date_str = departure_date
            
            flights.append({
                'id': f'MOCK-SERP-FL-{i+1}',
                'price': price,
                'currency': 'USD',
                'airline': airline['code'],
                'airline_name': airline['name'],
                'departure_time': f'{departure_date}T{dep_hour:02d}:{dep_minute:02d}:00',
                'arrival_time': f'{arrival_date_str}T{arr_hour:02d}:{arr_minute:02d}:00',
                'duration': f'{flight_hours}h {flight_minutes}m',
                'stops': stops,
                'booking_class': random.choice(['Economy', 'Premium Economy', 'Business']),
                'seats_available': str(adults),
                'route': f'{origin} → {destination}',
                'is_mock': True,
                'total_amount': price,
                'owner': {}
            })
        
        return flights

