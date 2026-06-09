import asyncio
from ingest.server import create_app
from pipeline.worker import run_workers
import uvicorn

async def main():
    config = uvicorn.Config(create_app(), host="0.0.0.0", port=7777)
    server = uvicorn.Server(config)
    await asyncio.gather(
        server.serve(),
        run_workers(),
    )

if __name__ == "__main__":
    asyncio.run(main())
