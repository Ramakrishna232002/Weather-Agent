import re
from datetime import datetime
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from app.agents.base.base_agent import BaseAgent
from app.agents.state import SharedState
from app.services.market_service import MarketService
from app.services.geocoding_service import GeocodingService
from app.core.config import settings

class MarketAgent(BaseAgent):
    def __init__(self):
        super().__init__("MarketAgent")
        self.market_service = MarketService()
        self.geocoding_service = GeocodingService()
        self.llm = ChatOllama(  # Add LLM for response generation
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(SharedState)

        workflow.add_node("extract", self.extract)
        workflow.add_node("get_state", self.get_state_from_city)
        workflow.add_node("fetch", self.fetch_price)
        workflow.add_node("analyze", self.analyze_price)

        workflow.set_entry_point("extract")
        workflow.add_edge("extract", "get_state")
        workflow.add_edge("get_state", "fetch")
        workflow.add_edge("fetch", "analyze")
        workflow.add_edge("analyze", END)

        return workflow.compile()

    async def extract(self, state: SharedState):
        """Extract commodity and city from query"""
        query = state.get("user_query", "").lower()
        
        commodity = None
        city = None
        
        # Pattern 1: "cotton price in pune"
        patterns = [
            r'price\s+of\s+([a-z\s]+?)\s+in\s+([a-z\s]+)',
            r'([a-z\s]+?)\s+price\s+in\s+([a-z\s]+)',
            r'rate\s+of\s+([a-z\s]+?)\s+in\s+([a-z\s]+)',
            r'([a-z\s]+?)\s+rate\s+in\s+([a-z\s]+)',
            r'cost\s+of\s+([a-z\s]+?)\s+in\s+([a-z\s]+)',
            r'([a-z\s]+?)\s+cost\s+in\s+([a-z\s]+)',
            r'([a-z\s]+?)\s+per\s+kg\s+in\s+([a-z\s]+)',
            r'([a-z\s]+?)\s+per\s+quintal\s+in\s+([a-z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                commodity = match.group(1).strip()
                city = match.group(2).strip()
                break
        
        # Pattern 2: "cotton price pune" (without 'in')
        if not commodity or not city:
            pattern = r'([a-z\s]+?)\s+price\s+([a-z\s]+?)(?:\?|$)'
            match = re.search(pattern, query)
            if match:
                commodity = match.group(1).strip()
                city = match.group(2).strip()
        
        # Clean up commodity (remove extra words)
        if commodity:
            stop_words = ['what', 'is', 'the', 'of', 'for', 'to', 'and', 'a', 'an']
            words = commodity.split()
            cleaned = [w for w in words if w not in stop_words]
            commodity = ' '.join(cleaned[:2]) if cleaned else commodity
        
        # Clean up city
        if city:
            city = city.split()[0].strip()
        
        state["commodity"] = commodity
        state["city"] = city
        state["location"] = city
        
        print(f"📊 MarketAgent - Extracted: Commodity='{commodity}', City='{city}'")
        return state

    async def get_state_from_city(self, state: SharedState):
        """Get state using geocoding service"""
        city = state.get("city")
        
        if not city:
            print("⚠️ MarketAgent - No city to geocode")
            return state
        
        try:
            print(f"📍 MarketAgent - Geocoding city: {city}")
            coordinates = await self.geocoding_service.get_coordinates(city)
            
            if coordinates:
                lat, lon = coordinates
                print(f"📍 MarketAgent - Got coordinates: {lat}, {lon}")
                state_name = await self.geocoding_service.get_state_from_coordinates(lat, lon)
                
                if state_name:
                    state["state"] = state_name
                    print(f"📍 MarketAgent - Found state: {state_name} for city: {city}")
                else:
                    print(f"⚠️ MarketAgent - Could not get state for {city}")
            else:
                print(f"⚠️ MarketAgent - Could not get coordinates for {city}")
                
        except Exception as e:
            print(f"❌ MarketAgent - Geocoding error: {e}")
        
        return state

    async def fetch_price(self, state: SharedState):
        """Fetch price data from API"""
        try:
            commodity = state.get("commodity")
            city = state.get("city")
            state_name = state.get("state")
            
            if not commodity:
                print("⚠️ MarketAgent - No commodity extracted, skipping fetch")
                state["market_price_data"] = []
                return state
            
            print(f"🔍 MarketAgent - Fetching prices for: {commodity} in {city or state_name}")
            
            prices = await self.market_service.get_price_for_location(
                commodity=commodity,
                city=city,
                state=state_name
            )
            
            state["market_price_data"] = prices
            print(f"✅ MarketAgent - Fetched {len(prices)} price records")
            
        except Exception as e:
            print(f"❌ MarketAgent - Fetch error: {e}")
            state["market_price_data"] = []
        
        return state

    async def analyze_price(self, state: SharedState):
        """Analyze and format price data using LLM for intelligent response"""
        prices = state.get("market_price_data", [])
        commodity = state.get("commodity", "Requested commodity")
        city = state.get("city", "")
        state_name = state.get("state", "")
        user_query = state.get("user_query", "")
        
        if not prices:
            state["market_analysis"] = f"I searched for {commodity} prices in {city or state_name}, but couldn't find any data. Could you try a different commodity or location? I'm here to help! 🌾"
            return state
        
        # Extract valid prices
        valid_prices = []
        valid_markets = []
        for p in prices:
            price = p.get("modal_price_kg")
            if price and price > 0:
                valid_prices.append(price)
                valid_markets.append(p)
        
        if not valid_prices:
            state["market_analysis"] = f"I found some records for {commodity}, but the price data seems incomplete. Would you like me to check another commodity? 📊"
            return state
        
        # Calculate statistics
        min_price = min(valid_prices)
        max_price = max(valid_prices)
        avg_price = sum(valid_prices) / len(valid_prices)
        
        # Convert to quintal
        avg_price_quintal = avg_price * 100
        min_price_quintal = min_price * 100
        max_price_quintal = max_price * 100
        
        # Find best and worst markets
        best_market = min(valid_markets, key=lambda x: x["modal_price_kg"])
        highest_market = max(valid_markets, key=lambda x: x["modal_price_kg"])
        
        # Prepare market data for LLM
        market_details = []
        for p in valid_markets[:5]:
            market_details.append({
                "district": p.get("district", "Unknown"),
                "market": p.get("market", "Unknown"),
                "price_kg": p["modal_price_kg"],
                "price_quintal": p["modal_price_kg"] * 100
            })
        
        today = datetime.now().strftime("%B %d, %Y")
        current_month = datetime.now().strftime("%B")
        
        # Get season from current month
        if current_month in ["March", "April", "May", "June"]:
            season = "summer/crop harvesting"
        elif current_month in ["July", "August", "September", "October"]:
            season = "monsoon/planting"
        else:
            season = "post-harvest/winter"
        
        # Create prompt for LLM
        prompt = f"""You are an expert agricultural market advisor with deep knowledge of Indian commodity markets. 
Generate a professional, interactive, and helpful response about {commodity} prices.

**Query:** {user_query}
**Location:** {city or state_name}
**Date:** {today}

**Market Data:**
- Commodity: {commodity}
- State: {state_name}
- Price Range: ₹{min_price:.2f} - ₹{max_price:.2f} per kg (₹{min_price_quintal:.0f} - ₹{max_price_quintal:.0f} per quintal)
- Average Price: ₹{avg_price:.2f}/kg (₹{avg_price_quintal:.0f}/quintal)
- Best Market: {best_market.get('market', 'N/A')} in {best_market.get('district', 'N/A')} at ₹{best_market['modal_price_kg']}/kg
- Highest Price Market: {highest_market.get('market', 'N/A')} at ₹{highest_market['modal_price_kg']}/kg

**Nearby Markets Data:**
{market_details}

**Context:**
- Current Season: {season}
- Data Source: {'Nearby markets' if prices[0].get('data_source') == 'state' else 'Direct market data'}

**Instructions for Response:**
1. Start with a warm, professional 4-5 line paragraph and always mention the city mentioned in queray explaining the current price situation naturally and professionally
2. Include both per kg and per quintal prices in the conversation and mention kg and quantal after price and price must be in bold
3. Add practical recommendations for farmers (1-2 bullet points)
4. Add practical recommendations for buyers/traders (1-2 bullet points)
5. Include a market insight section with seasonal context and price 
6. Make entire result metricess in bottom Metrics Section Format:
- Location: <city and state>
-  Price Range: ₹X–₹Y/kg (₹X–₹Y/quintal)
-  Average Price: ₹X/kg (₹X/quintal)
-  Best Market: <city and market name> – ₹X/kg (₹X/quintal)
-  Highest Market: <city and market name> – ₹X/kg (₹X/quintal)
7. Use appropriate emojis (🌾, 📊, 💰, 🚛, 💡, etc.)
8. Keep the tone professional yet conversational and interactive
9. Mention the best market opportunity with price values
10. If data is from nearby locations (not exact city), mention that gracefully

Note: You do not just describe prices — you help farmers and traders make better selling and buying decisions.

**Format the response naturally** - No markdown, just clean text with line breaks and emojis. Make it sound like a friendly expert advisor."""

        try:
            # Generate response using LLM
            response = await self.llm.ainvoke([("user", prompt)])
            state["market_analysis"] = response.content
            print(f"✅ MarketAgent - LLM generated intelligent response")
            
        except Exception as e:
            print(f"❌ MarketAgent - LLM error: {e}, using fallback response")
            # Fallback response if LLM fails
            state["market_analysis"] = f"""As of {today}, {commodity} prices in {state_name} are averaging ₹{avg_price:.2f}/kg (₹{avg_price_quintal:.0f}/quintal), ranging from ₹{min_price:.2f} to ₹{max_price:.2f} per kg.

📍 **Best Price:** ₹{best_market['modal_price_kg']}/kg at {best_market.get('market', 'local market')}
🌾 **For Farmers:** Consider selling at the best market for maximum returns. Ensure quality grading for premium rates.
🛒 **For Buyers:** Current prices are {'stable' if min_price == max_price else 'competitive'}. Compare across markets.
Need more details? Feel free to ask! 🤝"""
        
        return state

    async def process(self, state: SharedState):
        result = await self.graph.ainvoke(state)
        if "completed_agents" not in result:
            result["completed_agents"] = []
        if "market" not in result["completed_agents"]:
            result["completed_agents"].append("market")
        return result