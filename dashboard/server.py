"""FastAPI dashboard server.

Serves the HTML dashboard and provides:
- GET  /api/state        — current snapshot (for reconnecting clients)
- POST /api/run          — start a new pipeline
- POST /api/hitm/resolve — resolve a HITM checkpoint
- WS   /ws               — real-time state stream
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings
from core.state_manager import state
from orchestrator import Coordinator

STATIC_DIR = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    title: str
    description: str
    hitm: bool | None = None


class HITMResolution(BaseModel):
    checkpoint_id: str
    approved: bool
    notes: str = ""


def create_app() -> FastAPI:
    app = FastAPI(title="SpecAgent Dashboard", version="0.1.0")

    # Serve static files
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # ------------------------------------------------------------------ HTML
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # ------------------------------------------------------------ REST API
    @app.get("/api/state")
    async def get_state():
        return state.snapshot()

    @app.post("/api/run")
    async def run_pipeline(req: RunRequest):
        print("### we are running...")
        if state.task and state.task.overall_status.value in ("pending", "in_progress"):
            raise HTTPException(status_code=409, detail="A pipeline is already running")
        coordinator = Coordinator()
        asyncio.create_task(coordinator.run(req.title, req.description, req.hitm))
        return {"status": "started", "task_id": state.task.id if state.task else None}

    @app.post("/api/hitm/resolve")
    async def resolve_hitm(resolution: HITMResolution):
        state.resolve_hitm(resolution.checkpoint_id, {
            "approved": resolution.approved,
            "notes": resolution.notes,
        })
        return {"status": "resolved"}

    @app.get("/api/output/{task_id}")
    async def list_output(task_id: str):
        out_dir = settings.output_dir / task_id
        if not out_dir.exists():
            raise HTTPException(status_code=404, detail="No output found for this task")
        files = [str(f.relative_to(out_dir)) for f in out_dir.rglob("*") if f.is_file()]
        return {"task_id": task_id, "files": files}

    # ------------------------------------------------------------------- WS
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        state.register_ws(ws)
        try:
            # Send current state immediately on connect
            await ws.send_text(json.dumps(state.snapshot(), default=str))
            # Keep alive — read loop (client can send HITM resolutions here too)
            while True:
                try:
                    data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                    msg = json.loads(data)
                    if msg.get("type") == "hitm.resolve":
                        state.resolve_hitm(msg["checkpoint_id"], {
                            "approved": msg.get("approved", False),
                            "notes": msg.get("notes", ""),
                        })
                except asyncio.TimeoutError:
                    await ws.send_text('{"type":"ping"}')
        except WebSocketDisconnect:
            pass
        finally:
            state.unregister_ws(ws)

    return app
