import redis.asyncio as redis
import json
r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

MAX_MESSAGES = 40
TTL_SECONDS = 60*60

async def add_message(session_id:str,role:str,content:str):
    key = f"session:{session_id}"
    await r.rpush(key,json.dumps({"role":role,"content":content}))
    await r.ltrim(key,-MAX_MESSAGES,-1)
    await r.expire(key,TTL_SECONDS)

async def get_history(session_id:str)->list[dict]:
    return [json.loads(m) for m in await r.lrange(f"session:{session_id}", 0, -1)]

async def clear_history(session_id:str):
    return await r.delete(f"session:{session_id}")