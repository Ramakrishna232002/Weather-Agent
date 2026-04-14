import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings


class MarketService:
    def __init__(self):
        self.base_url = settings.MARKET_API_URL
        self.api_key = settings.MARKET_API_KEY

    async def get_commodity_price(
        self,
        commodity: str,
        state: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit
        }

        # loose filter
        if commodity:
            params["filters%5Bcommodity%5D"] = commodity

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

        records = data.get("records", [])

        # Dynamic filtering
        if commodity:
            records = [
                r for r in records
                if commodity.lower() in r.get("commodity", "").lower()
            ]

        if state:
            records = [
                r for r in records
                if state.lower() in r.get("state", "").lower()
            ]

        cleaned = []
        for r in records:
            modal = r.get("modal_price")

            if not modal or modal <= 0:
                continue

            # ⚠️ assuming per quintal → convert to kg
            price_per_kg = round(modal / 100, 2)

            r["modal_price_kg"] = price_per_kg
            r["price_unit"] = "kg"

            cleaned.append(r)

        return cleaned

    async def get_price_for_location(
        self,
        commodity: str,
        city: str,
        state: Optional[str],
        limit: int = 50
    ) -> List[Dict[str, Any]]:

        all_data = await self.get_commodity_price(
            commodity=commodity,
            state=state
        )

        if not all_data:
            return []

        city_lower = city.lower() if city else ""

        # 1. District match
        district_data = [
            r for r in all_data
            if city_lower in r.get("district", "").lower()
        ]

        if district_data:
            for r in district_data:
                r["data_source"] = "district"
            return district_data[:limit]

        # 2. State fallback
        if state:
            state_data = [
                r for r in all_data
                if state.lower() in r.get("state", "").lower()
            ]

            if state_data:
                for r in state_data:
                    r["data_source"] = "state"
                return state_data[:limit]

        #3. Final fallback
        for r in all_data:
            r["data_source"] = "fallback"

        return all_data[:limit]