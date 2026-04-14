from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Weather Agent"

    # Weather API Settings
    WEATHER_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    
    # Ollama Settings
    OLLAMA_MODEL: str = "llama3.2:1b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    MARKET_API_URL: str = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    MARKET_API_KEY: str = "579b464db66ec23bdd00000121140f34e78442bc7a6300bc6632847f"
 
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()