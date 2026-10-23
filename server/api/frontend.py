"""Serve the built React pages (app/dist) next to the API."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DIST = Path(__file__).resolve().parents[2] / "app" / "dist"
PAGES = {
    "/": "index.html",
    "/benchmarks": "benchmarks/index.html",
    "/methodology": "methodology/index.html",
    "/dashboard": "dashboard/index.html",
    "/results": "results/index.html",
}


def mount_frontend(app: FastAPI, dist: Path = DIST) -> None:
    for folder in ("assets", "licenses"):
        app.mount(f"/{folder}", StaticFiles(directory=dist / folder), name=folder)
    for route, file in PAGES.items():
        app.add_api_route(route, _page(dist / file), include_in_schema=False)


def _page(path: Path):
    return lambda: FileResponse(path, headers={"Cache-Control": "no-cache"})
