import asyncio,sys,os 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.email import read_emails

async def main():
    result = await read_emails.func(max_results=10)
    print(result)

asyncio.run(main())
