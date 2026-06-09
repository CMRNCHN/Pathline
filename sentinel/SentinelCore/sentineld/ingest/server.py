import asyncio
from fastapi import FastAPI, UploadFile

_queue: asyncio.Queue = None

def get_queue() -> asyncio.Queue:
    return _queue

def create_app() -> FastAPI:
    global _queue
    _queue = asyncio.Queue()
    app = FastAPI()

    @app.post("/ingest")
    async def ingest(file: UploadFile):
        data = await file.read()
        await _queue.put(data)
        return {"status": "ok"}

    return app
