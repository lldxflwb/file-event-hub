"""FastAPI application for the file-event-hub server."""

import json
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import EventCreate, EventListResponse, FileResponse
from .store import event_store

app = FastAPI(title="file-event-hub", version="0.1.0")

# CORS middleware - allow all origins for local/LAN use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
_ws_clients: set[WebSocket] = set()


@app.post("/api/events", status_code=201)
async def create_event(event_create: EventCreate):
    """Receive a file change event from a hook publisher."""
    event = event_store.add(event_create)

    # Broadcast to all connected WebSocket clients
    message = json.dumps({"type": "new_event", "event": event.model_dump()})
    disconnected: list[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _ws_clients.discard(ws)

    return event.model_dump()


@app.get("/api/events")
async def list_events(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    """Query stored events in reverse chronological order."""
    events, total = event_store.list(limit=limit, offset=offset)
    return EventListResponse(events=events, total=total)


@app.get("/api/files/{file_path:path}")
async def read_file(file_path: str) -> FileResponse:
    """Read a file's content from the filesystem."""
    # Security: reject path traversal
    if ".." in file_path:
        return FileResponse(path=file_path, content=None, exists=False)

    # Ensure absolute path
    if not file_path.startswith("/"):
        file_path = "/" + file_path

    try:
        content = Path(file_path).read_text(encoding="utf-8")
        return FileResponse(path=file_path, content=content, exists=True)
    except (OSError, UnicodeDecodeError):
        return FileResponse(path=file_path, content=None, exists=False)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await ws.accept()
    _ws_clients.add(ws)
    try:
        await ws.send_text(
            json.dumps(
                {"type": "connected", "message": "Connected to file-event-hub"}
            )
        )
        # Keep connection alive, waiting for client messages or disconnect
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)


# Mount static files LAST so API routes take priority
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
