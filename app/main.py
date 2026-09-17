from fastapi import FastAPI
from app.config import settings

app = FastAPI(title=settings.app_name)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "debug": settings.debug,
        "model": settings.oneapi_chat_model,
    }