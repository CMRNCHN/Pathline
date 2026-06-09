import asyncio
from pipeline.whisper.transcribe import transcribe
from pipeline.actions.extract import extract_actions
from pipeline.embeddings.embed import embed
from pipeline.storage.sqlite import save_transcript, save_actions
from ingest.server import get_queue

def process(chunk):
    text = transcribe(chunk)
    actions = extract_actions(text)
    vector = embed(text)
    save_transcript(text, vector)
    save_actions(actions)

async def run_workers():
    queue = get_queue()
    while True:
        chunk = await queue.get()
        process(chunk)
        queue.task_done()
