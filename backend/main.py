from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.system import system_router
from routes.reminders import reminders_router
from routes.roadmap import roadmap_router
from routes.voice_chat import router
from routes.today import today_router
from dotenv import load_dotenv
from agent.laya_router import load_router
import asyncio 
from contextlib import asynccontextmanager
from sync.worker import start_background_tasks
from graph.workflow_creation import agent_workflow
from rag.online import load_index
from long_memory.init_db import init_db
load_dotenv()



@asynccontextmanager
async def lifespan(app:FastAPI):
    global graph
    init_db()
    await asyncio.to_thread(load_router)
    asyncio.create_task(start_background_tasks())
    app.state.index = load_index()
    graph = await agent_workflow()
    yield
    app.state.index.storage_context.vector_store.client.close()

    
    

app = FastAPI(title="J.A.R.V.I.S.",lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"ok": True}


app.include_router(chat_router)
app.include_router(system_router)
app.include_router(reminders_router)
app.include_router(roadmap_router)
app.include_router(router)
app.include_router(today_router)