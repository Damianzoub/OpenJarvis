import httpx
from langchain.tools import tool

_WMO_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


async def _geocode(location: str) -> tuple[float, float, str, str]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1},
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results")
    if not results:
        raise ValueError(f"Could not find a location matching '{location}'")

    place = results[0]
    return place["latitude"], place["longitude"], place["name"], place.get("country", "")


async def _get_weather(location: str) -> str:
    lat, lon, place, country = await _geocode(location)

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            },
        )
        response.raise_for_status()
        data = response.json()

    current = data["current"]
    condition = _WMO_CODES.get(current["weather_code"], "unknown conditions")
    temp = current["temperature_2m"]
    feels = current["apparent_temperature"]
    humidity = current["relative_humidity_2m"]
    wind = current["wind_speed_10m"]

    return (
        f"The weather in {place}, {country} is {condition}. "
        f"It is {temp}°C, feels like {feels}°C. "
        f"Humidity is {humidity}% and wind speed is {wind} km/h."
    )


@tool(description="Get the current weather for a given location.")
async def get_weather(location: str) -> str:
    return await _get_weather(location)
