"""
Airport and city data for autocomplete functionality.
Contains major airports with IATA codes, city names, and full names.
"""

MAJOR_AIRPORTS = [
    # US Airports
    {'code': 'ATL', 'name': 'Hartsfield-Jackson Atlanta International Airport', 'city': 'Atlanta', 'country': 'USA'},
    {'code': 'LAX', 'name': 'Los Angeles International Airport', 'city': 'Los Angeles', 'country': 'USA'},
    {'code': 'ORD', 'name': "O'Hare International Airport", 'city': 'Chicago', 'country': 'USA'},
    {'code': 'DFW', 'name': 'Dallas/Fort Worth International Airport', 'city': 'Dallas', 'country': 'USA'},
    {'code': 'DEN', 'name': 'Denver International Airport', 'city': 'Denver', 'country': 'USA'},
    {'code': 'JFK', 'name': 'John F. Kennedy International Airport', 'city': 'New York', 'country': 'USA'},
    {'code': 'SFO', 'name': 'San Francisco International Airport', 'city': 'San Francisco', 'country': 'USA'},
    {'code': 'SEA', 'name': 'Seattle-Tacoma International Airport', 'city': 'Seattle', 'country': 'USA'},
    {'code': 'LAS', 'name': 'McCarran International Airport', 'city': 'Las Vegas', 'country': 'USA'},
    {'code': 'MIA', 'name': 'Miami International Airport', 'city': 'Miami', 'country': 'USA'},
    {'code': 'MCO', 'name': 'Orlando International Airport', 'city': 'Orlando', 'country': 'USA'},
    {'code': 'PHX', 'name': 'Phoenix Sky Harbor International Airport', 'city': 'Phoenix', 'country': 'USA'},
    {'code': 'IAH', 'name': 'George Bush Intercontinental Airport', 'city': 'Houston', 'country': 'USA'},
    {'code': 'CLT', 'name': 'Charlotte Douglas International Airport', 'city': 'Charlotte', 'country': 'USA'},
    {'code': 'EWR', 'name': 'Newark Liberty International Airport', 'city': 'Newark', 'country': 'USA'},
    {'code': 'BOS', 'name': 'Logan International Airport', 'city': 'Boston', 'country': 'USA'},
    {'code': 'DTW', 'name': 'Detroit Metropolitan Airport', 'city': 'Detroit', 'country': 'USA'},
    {'code': 'PHL', 'name': 'Philadelphia International Airport', 'city': 'Philadelphia', 'country': 'USA'},
    {'code': 'LGA', 'name': 'LaGuardia Airport', 'city': 'New York', 'country': 'USA'},
    {'code': 'BWI', 'name': 'Baltimore/Washington International Airport', 'city': 'Baltimore', 'country': 'USA'},
    {'code': 'DCA', 'name': 'Ronald Reagan Washington National Airport', 'city': 'Washington', 'country': 'USA'},
    {'code': 'IAD', 'name': 'Washington Dulles International Airport', 'city': 'Washington', 'country': 'USA'},
    {'code': 'SLC', 'name': 'Salt Lake City International Airport', 'city': 'Salt Lake City', 'country': 'USA'},
    {'code': 'MDW', 'name': 'Chicago Midway International Airport', 'city': 'Chicago', 'country': 'USA'},
    {'code': 'HNL', 'name': 'Daniel K. Inouye International Airport', 'city': 'Honolulu', 'country': 'USA'},
    
    # International Airports
    {'code': 'LHR', 'name': 'London Heathrow Airport', 'city': 'London', 'country': 'UK'},
    {'code': 'CDG', 'name': 'Charles de Gaulle Airport', 'city': 'Paris', 'country': 'France'},
    {'code': 'AMS', 'name': 'Amsterdam Airport Schiphol', 'city': 'Amsterdam', 'country': 'Netherlands'},
    {'code': 'FRA', 'name': 'Frankfurt Airport', 'city': 'Frankfurt', 'country': 'Germany'},
    {'code': 'MAD', 'name': 'Adolfo Suárez Madrid-Barajas Airport', 'city': 'Madrid', 'country': 'Spain'},
    {'code': 'FCO', 'name': 'Leonardo da Vinci-Fiumicino Airport', 'city': 'Rome', 'country': 'Italy'},
    {'code': 'BCN', 'name': 'Barcelona-El Prat Airport', 'city': 'Barcelona', 'country': 'Spain'},
    {'code': 'LGW', 'name': 'London Gatwick Airport', 'city': 'London', 'country': 'UK'},
    {'code': 'MUC', 'name': 'Munich Airport', 'city': 'Munich', 'country': 'Germany'},
    {'code': 'ZUR', 'name': 'Zurich Airport', 'city': 'Zurich', 'country': 'Switzerland'},
    {'code': 'VIE', 'name': 'Vienna International Airport', 'city': 'Vienna', 'country': 'Austria'},
    {'code': 'DUB', 'name': 'Dublin Airport', 'city': 'Dublin', 'country': 'Ireland'},
    {'code': 'CPH', 'name': 'Copenhagen Airport', 'city': 'Copenhagen', 'country': 'Denmark'},
    {'code': 'ARN', 'name': 'Stockholm Arlanda Airport', 'city': 'Stockholm', 'country': 'Sweden'},
    {'code': 'OSL', 'name': 'Oslo Airport', 'city': 'Oslo', 'country': 'Norway'},
    {'code': 'HEL', 'name': 'Helsinki Airport', 'city': 'Helsinki', 'country': 'Finland'},
    {'code': 'ATH', 'name': 'Athens International Airport', 'city': 'Athens', 'country': 'Greece'},
    {'code': 'LIS', 'name': 'Lisbon Airport', 'city': 'Lisbon', 'country': 'Portugal'},
    {'code': 'PRG', 'name': 'Václav Havel Airport Prague', 'city': 'Prague', 'country': 'Czech Republic'},
    {'code': 'BUD', 'name': 'Budapest Ferenc Liszt International Airport', 'city': 'Budapest', 'country': 'Hungary'},
    {'code': 'WAW', 'name': 'Warsaw Chopin Airport', 'city': 'Warsaw', 'country': 'Poland'},
    
    # Asia Pacific
    {'code': 'NRT', 'name': 'Narita International Airport', 'city': 'Tokyo', 'country': 'Japan'},
    {'code': 'HND', 'name': 'Haneda Airport', 'city': 'Tokyo', 'country': 'Japan'},
    {'code': 'ICN', 'name': 'Incheon International Airport', 'city': 'Seoul', 'country': 'South Korea'},
    {'code': 'PEK', 'name': 'Beijing Capital International Airport', 'city': 'Beijing', 'country': 'China'},
    {'code': 'PVG', 'name': 'Shanghai Pudong International Airport', 'city': 'Shanghai', 'country': 'China'},
    {'code': 'HKG', 'name': 'Hong Kong International Airport', 'city': 'Hong Kong', 'country': 'China'},
    {'code': 'SIN', 'name': 'Singapore Changi Airport', 'city': 'Singapore', 'country': 'Singapore'},
    {'code': 'BKK', 'name': 'Suvarnabhumi Airport', 'city': 'Bangkok', 'country': 'Thailand'},
    {'code': 'DXB', 'name': 'Dubai International Airport', 'city': 'Dubai', 'country': 'UAE'},
    {'code': 'DOH', 'name': 'Hamad International Airport', 'city': 'Doha', 'country': 'Qatar'},
    {'code': 'SYD', 'name': 'Sydney Kingsford Smith Airport', 'city': 'Sydney', 'country': 'Australia'},
    {'code': 'MEL', 'name': 'Melbourne Airport', 'city': 'Melbourne', 'country': 'Australia'},
    {'code': 'BNE', 'name': 'Brisbane Airport', 'city': 'Brisbane', 'country': 'Australia'},
    {'code': 'AKL', 'name': 'Auckland Airport', 'city': 'Auckland', 'country': 'New Zealand'},
    
    # Canada
    {'code': 'YYZ', 'name': 'Toronto Pearson International Airport', 'city': 'Toronto', 'country': 'Canada'},
    {'code': 'YVR', 'name': 'Vancouver International Airport', 'city': 'Vancouver', 'country': 'Canada'},
    {'code': 'YUL', 'name': 'Montréal-Pierre Elliott Trudeau International Airport', 'city': 'Montreal', 'country': 'Canada'},
    {'code': 'YYC', 'name': 'Calgary International Airport', 'city': 'Calgary', 'country': 'Canada'},
    {'code': 'YEG', 'name': 'Edmonton International Airport', 'city': 'Edmonton', 'country': 'Canada'},
    
    # Latin America
    {'code': 'MEX', 'name': 'Mexico City International Airport', 'city': 'Mexico City', 'country': 'Mexico'},
    {'code': 'GIG', 'name': 'Rio de Janeiro-Galeão International Airport', 'city': 'Rio de Janeiro', 'country': 'Brazil'},
    {'code': 'GRU', 'name': 'São Paulo-Guarulhos International Airport', 'city': 'São Paulo', 'country': 'Brazil'},
    {'code': 'EZE', 'name': 'Ministro Pistarini International Airport', 'city': 'Buenos Aires', 'country': 'Argentina'},
]


def search_airports(query: str, limit: int = 10) -> list:
    """
    Search airports by code, city name, or airport name.
    
    Args:
        query: Search query (can be airport code, city name, or airport name)
        limit: Maximum number of results to return
        
    Returns:
        List of matching airports
    """
    if not query:
        return []
    
    query_lower = query.lower().strip()
    matches = []
    
    for airport in MAJOR_AIRPORTS:
        score = 0
        
        # Exact code match (highest priority)
        if airport['code'].lower() == query_lower:
            score = 100
        # Code starts with query
        elif airport['code'].lower().startswith(query_lower):
            score = 80
        # Code contains query
        elif query_lower in airport['code'].lower():
            score = 60
        # City name match
        elif query_lower in airport['city'].lower():
            score = 50
        # Airport name match
        elif query_lower in airport['name'].lower():
            score = 40
        # Country match
        elif query_lower in airport['country'].lower():
            score = 20
        
        if score > 0:
            matches.append({
                'code': airport['code'],
                'name': airport['name'],
                'city': airport['city'],
                'country': airport['country'],
                'display': f"{airport['code']} - {airport['city']}, {airport['country']}",
                'full_display': f"{airport['name']} ({airport['code']})",
                'score': score
            })
    
    # Sort by score (highest first), then by city name
    matches.sort(key=lambda x: (-x['score'], x['city']))
    
    return matches[:limit]

