import httpx
from typing import Optional, Tuple, List

class GeocodingService:
    def __init__(self):
        # Open-Meteo Geocoding API endpoint
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
    
    async def get_coordinates(self, location_name: str) -> Optional[Tuple[float, float]]:
        """
        Convert location name to coordinates (latitude, longitude)
        
        Args:
            location_name: City name (e.g., "Pune", "New York", "London")
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        params = {
            "name": location_name,
            "count": 1,  
            "language": "en",
            "format": "json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.geocoding_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Check if we got any results
                if data and "results" in data and len(data["results"]) > 0:
                    # Get the first (best) match
                    result = data["results"][0]
                    latitude = result["latitude"]
                    longitude = result["longitude"]
                    return (latitude, longitude)
                else:
                    return None
                    
            except Exception as e:
                print(f"Geocoding error for {location_name}: {e}")
                return None
    
    async def search_locations(self, query: str) -> List[dict]:
        """
        Search for locations and return all matches
        
        Args:
            query: Search term (e.g., "Pune")
            
        Returns:
            List of location dictionaries with name, country, coordinates
        """
        params = {
            "name": query,
            "count": 5,
            "language": "en",
            "format": "json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.geocoding_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data and "results" in data:
                    results = []
                    for result in data["results"]:
                        results.append({
                            "name": result.get("name", ""),
                            "country": result.get("country", ""),
                            "admin1": result.get("admin1", ""),  # State/Province
                            "latitude": result.get("latitude"),
                            "longitude": result.get("longitude")
                        })
                    return results
                return []
                
            except Exception as e:
                print(f"Location search error: {e}")
                return []