from geopy.geocoders import Nominatim
from geopy.location import Location
from typing import Optional, Tuple

# Use a specific user_agent to comply with OSM policy
geolocator = Nominatim(user_agent="TeamHubBot/1.0")

def get_location_by_query(query: str) -> Optional[Tuple[str, str, float, float]]:
    """
    Returns (State, City, Lat, Lon) or None
    """
    try:
        # Limit to USA for better accuracy
        loc: Location = geolocator.geocode(query, addressdetails=True, country_codes="us")
        if not loc:
            return None
        
        address = loc.raw.get('address', {})
        state = address.get('state')
        city = address.get('city') or address.get('town') or address.get('village') or address.get('county')
        
        if not state:
            return None
            
        return state, city, loc.latitude, loc.longitude
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

def get_location_by_coords(lat: float, lon: float) -> Optional[Tuple[str, str, float, float]]:
    """
    Reverse geocoding. Returns (State, City, Lat, Lon)
    """
    try:
        # Reverse geocode
        loc: Location = geolocator.reverse((lat, lon), exactly_one=True, addressdetails=True)
        if not loc:
            return "GPS", "Location", lat, lon
            
        address = loc.raw.get('address', {})
        state = address.get('state', 'GPS')
        city = address.get('city') or address.get('town') or address.get('village') or address.get('county') or 'Location'
        
        return state, city, lat, lon
    except Exception as e:
        print(f"Reverse Geocoding error: {e}")
        return "GPS", "Location", lat, lon

def calculate_distance(lat1, lon1, lat2, lon2) -> float:
    """
    Calculate distance in miles between two coordinates.
    """
    from geopy.distance import geodesic
    try:
        # geodesic expects (lat, lon) tuples
        # returns distance object, we want miles
        return geodesic((lat1, lon1), (lat2, lon2)).miles
    except Exception as e:
        print(f"Distance calc error: {e}")
        return float('inf')
