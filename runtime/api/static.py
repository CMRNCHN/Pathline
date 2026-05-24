from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_static(app: FastAPI) -> None:
    static_dir = Path(__file__).parent.parent.parent / "frontend"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
