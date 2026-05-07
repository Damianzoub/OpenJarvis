from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.system import system_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="J.A.R.V.I.S.")

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