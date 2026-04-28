from fastapi import FastAPI
from routes.chat import router
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title='jarvis application')

@app.get("/")
@app.get("/home")
def health():
    return {"ok":True}

app.include_router(router)