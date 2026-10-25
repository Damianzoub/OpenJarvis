import asyncio
import os

import httpx
import yfinance as yf
from langchain.tools import tool

from memory.finance_store import log_expense as _log_expense
from memory.finance_store import list_expenses as _list_expenses
import feedparser

@tool(description="Log an expense with an amount and category.")
async def log_expense(amount: float, category: str, note: str = "") -> str:
    entry = _log_expense(amount, category, note)
    return f"Logged {entry['amount']} under {entry['category']}."


@tool(description="Read recent posts from a finance/market blog's RSS feed.")
async def read_rss_feed(feed_url:str,count:int=5) ->str:
    feed = await asyncio.to_thread(feedparser.parse,feed_url)
    entries = feed.entries[:count]
    if not entries:
        return f"No entries found: {feed_url}"
    return "\n".join(f"{e.title}\n   {e.link}" for e in entries)


@tool(description="Get a summary of logged expenses by category.")
async def get_budget_summary() -> str:
    expenses = _list_expenses()
    if not expenses:
        return "No expenses logged yet."
    totals: dict[str, float] = {}
    for e in expenses:
        totals[e["category"]] = totals.get(e["category"], 0) + e["amount"]
    lines = [f"{category}: {total:.2f}" for category, total in totals.items()]
    lines.append(f"Total: {sum(totals.values()):.2f}")
    return "\n".join(lines)


def _get_quote(symbol: str) -> str:
    ticker = yf.Ticker(symbol)
    info = ticker.fast_info
    price = info.get("last_price")
    if price is None:
        return f"No quote found for {symbol}."
    change = price - info.get("previous_close", price)
    return f"{symbol.upper()}: {price:.2f} ({change:+.2f})"


@tool(description="Get the current price quote for a stock ticker symbol.")
async def get_quote(symbol: str) -> str:
    return await asyncio.to_thread(_get_quote, symbol)


async def _summarize_market_news(topic: str, count: int = 5) -> str:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        raise ValueError("Missing NEWS_API_KEY in .env")
    url = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": api_key,
        "q": topic,
        "sortBy": "publishedAt",
        "pageSize": count,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    articles = data.get("articles", [])
    if not articles:
        return f"No recent coverage found for {topic}."

    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. {a['title']} ({a['source']['name']})\n   {a['url']}")
        if a.get("description"):
            lines.append(f"   {a['description']}")
    return "\n".join(lines)


@tool(description="Get recent news coverage about a market or finance topic, to summarize sentiment — not a prediction.")
async def summarize_market_news(topic: str) -> str:
    return await _summarize_market_news(topic)
