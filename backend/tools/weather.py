import os
import httpx 
from dotenv import load_dotenv

load_dotenv()

class WeatherTool:
    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")

        if not self.api_key:
            raise ValueError("Missing WEATHER_API_KEY in .env")
    
    async def get_current_weather(self,location:str)->str:
        url = os.getenv("URL_WEATHER_API")

        params = {
            "key":self.api_key,
            "q":location,
            "aqi":"no"
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url,params=params)
            response.raise_for_status()
            data = response.json()

        place = data["location"]["name"]
        country = data["location"]["country"]
        temp = data["current"]["temp_c"]
        feels = data["current"]["feelslike_c"]
        condition = data["current"]["condition"]["text"]
        humidity = data["current"]["humidity"]
        wind = data["current"]["wind_kph"]

        return (
            f"The weather in {place}, {country} is {condition}. "
            f"It is {temp}°C, feels like {feels}°C. "
            f"Humidity is {humidity}% and wind speed is {wind} km/h."
        )