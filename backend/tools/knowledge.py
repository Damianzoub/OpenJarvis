import asyncio
from langchain.tools import tool
from rag.online import  run_online

@tool(description="Search the user's personal notes and documents for releveant passages.")
async def search_knowledge(query:str):
    result = await asyncio.to_thread(run_online,query)
    return str(result) 

# if function is synchronous use asyncio.to_thread 
# if function is asynchronous (run_online) use await