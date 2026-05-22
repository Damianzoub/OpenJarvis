import os
import httpx 
from dotenv import load_dotenv

from bu_agent_sdk.tools import tool

load_dotenv()

async def _get_news(category:str='technology',count:int=5,country:str='gr')->str:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        raise ValueError("Missing NEWS_API_KEY in .env")
    url = "https://newsapi.org/v2/top-headlines"
    params={
        "apiKey":api_key,
        "category":category,
        "pageSize":count,
        "country":country
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url,params=params)
        r.raise_for_status()
        data = r.json()
    
    articles = data.get("articles",[])
    
    if not articles:
        return f"No news found for this category:{category}"

    lines = []
    for i, a in enumerate(articles,1):
        lines.append(f"{i}. {a['title']} ({a['source']['name']})\n   {a['url']}")
        if a.get("description"):
            lines.append(f"   {a['description']}")
    return "\n".join(lines)


@tool("Get the latest news headlines. Call this when the user asks about news, headlines, or what's happening in the world.")
async def get_news(category: str = "general", count: int = 5) -> str:
    return await _get_news(category, count)