"""ASGI app factory for the AirTouch runtime service."""

from __future__ import annotations

import asyncio
from typing import Any

from .commands import CommandRequestError, build_transaction
from .controller import RuntimeController
from .ui import INDEX_HTML

WEBSOCKET_PING_INTERVAL = 15.0
WEBSOCKET_COALESCE_DELAY = 0.1

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
except ModuleNotFoundError:  # pragma: no cover - import guard
    FastAPI = HTTPException = WebSocket = WebSocketDisconnect = HTMLResponse = None  # type: ignore[assignment]


def create_app(controller: RuntimeController):
    if FastAPI is None:  # pragma: no cover - import guard
        raise RuntimeError("FastAPI is required for the service API. Install dependencies from requirements.txt")

    app = FastAPI(title="OpenAirTouch", version="0.4.0")

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
        recent = controller.recent_events()
        cursor = len(recent)
        version = controller.change_version()
        await websocket.send_json({
            "type": "hello",
            "version": version,
            "health": controller.health(),
            "state": controller.snapshot(),
            "events": recent,
        })
        try:
            while True:
                next_version = await asyncio.to_thread(controller.wait_for_change, version, WEBSOCKET_PING_INTERVAL)
                if next_version == version:
                    await websocket.send_json({"type": "ping", "version": version})
                    continue

                await asyncio.sleep(WEBSOCKET_COALESCE_DELAY)
                version = max(next_version, controller.change_version())
                recent = controller.recent_events()
                if cursor > len(recent):
                    cursor = 0
                new_events = recent[cursor:]
                cursor = len(recent)
                if new_events:
                    await websocket.send_json({"type": "events", "version": version, "events": new_events})
                await websocket.send_json({
                    "type": "state",
                    "version": version,
                    "health": controller.health(),
                    "state": controller.snapshot(),
                    "events": recent,
                })
        except WebSocketDisconnect:
            return

    return app
