from fastapi import APIRouter,WebSocket,WebSocketDisconnect
import json
from dotenv import load_dotenv
import os
import uuid
load_dotenv()


DEVICE_TOKEN = os.getenv("DEVICE_TOKEN","dev")

router = APIRouter(tags=['voice_chat'])


@router.websocket("/ws/voice")
async def websocket_endpoint(websocket:WebSocket):
    await websocket.accept()
    try:
        device_id = websocket.query_params.get("device_id")
        token = websocket.query_params.get("token")
        if token != DEVICE_TOKEN:
             await websocket.close(code=4001)
             return 
        hello = await websocket.receive_json()
        if hello.get("type") != "hello":
             await websocket.close(code=4003)
             return 
        session_id = uuid.uuid4().hex[:8]
        await websocket.send_json({"type": "ready", "session_id": session_id, "v": 1})
        print(f"[voice] session {session_id} started")

        while True:
             msg = await websocket.receive()
             if msg["type"] == "websocket.disconnect":
                break
             if msg.get("bytes"):
                await websocket.send_bytes(msg["bytes"])
             elif msg.get("text"):
                print(f"[voice] {session_id}: {json.loads(msg['text'])}")
   
    except WebSocketDisconnect as e:
            return f"Error: {e}"