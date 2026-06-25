"""ASGI app factory for the AirTouch runtime service."""

from __future__ import annotations

import asyncio
from typing import Any

from .commands import CommandRequestError, build_transaction
from .controller import RuntimeController
from .ui import INDEX_HTML


def create_app(controller: RuntimeController):
    try:
        from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse
    except ModuleNotFoundError as exc:  # pragma: no cover - import guard
        raise RuntimeError("FastAPI is required for the service API. Install dependencies from requirements.txt") from exc

    app = FastAPI(title="AirTouch 4 Touchpad Host", version="0.1.0")

    @app.on_event("startup")
    def _startup() -> None:
        controller.start()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        controller.stop()

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return controller.health()

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return controller.snapshot()

    @app.get("/api/events")
    def events() -> dict[str, Any]:
        return {"events": controller.recent_events()}

    @app.post("/api/adaptive")
    async def adaptive(body: dict[str, Any]) -> dict[str, Any]:
        try:
            config = controller.update_adaptive_config(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"adaptive": config}

    @app.post("/api/adaptive/model")
    async def adaptive_model(body: dict[str, Any]) -> dict[str, Any]:
        try:
            learning = controller.manage_adaptive_learning(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"learning": learning}

    @app.post("/api/command")
    async def command(body: dict[str, Any]) -> dict[str, Any]:
        action = str(body.get("action", ""))
        data = body.get("data", {})
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="data must be an object")
        try:
            runtime = controller.snapshot().get("runtime") or {}
            spec = build_transaction(action, data, state=runtime.get("state") or {})
        except CommandRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return controller.enqueue(spec)

    @app.websocket("/ws")
    async def websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        cursor = 0
        try:
            while True:
                recent = controller.recent_events()
                if cursor > len(recent):
                    cursor = 0
                for event in recent[cursor:]:
                    await websocket.send_json(event)
                cursor = len(recent)
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            return

    return app
