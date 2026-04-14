import httpx
from typing import Optional, Tuple

class GeocodingService:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
    
    async def get_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
        """Get latitude and longitude for a location name"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "q": location,
                        "format": "json",
                        "limit": 1
                    },
                    headers={"User-Agent": "WeatherAgent/1.0"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        return (lat, lon)
                
                return None
                
        except Exception as e:
            print(f"Geocoding error for {location}: {e}")
            return None
    
    async def get_state_from_coordinates(self, lat: float, lon: float) -> Optional[str]:
        """Get state name from coordinates using reverse geocoding"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/reverse",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "format": "json",
                        "addressdetails": 1
                    },
                    headers={"User-Agent": "WeatherAgent/1.0"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    address = data.get("address", {})
                    # Try to get state from different possible fields
                    state = address.get("state") or address.get("region") or address.get("province") or address.get("state_district")
                    if state:
                        return state
                
                return None
                
        except Exception as e:
            print(f"Reverse geocoding error: {e}")
            return None