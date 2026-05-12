import asyncio 
from tools.weather import WeatherTool

async def main():
    weather = WeatherTool()

    while True:
        user_input = input("").lower()

        if user_input in {"exit","quit"}:
            break 

        if "weather" in user_input:
            location = user_input.replace("weather","").replace("in","").strip()

            if not location:
                location = "Athens"
            answer = await weather.get_current_weather(location)
            print(answer)
        else:
            print("I don't know")

asyncio.run(main())