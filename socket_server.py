"""
socket_server.py — Socket.IO async server for CriticAI live streaming.

Exposes:
  sio          – AsyncServer instance
  socket_app   – ASGI app to mount at /ws
  emit_to_session(session_id, event, data) – helper for swarm callbacks
"""
import socketio

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    logger=False,
    engineio_logger=False,
)

socket_app = socketio.ASGIApp(sio, socketio_path="")


async def emit_to_session(session_id: str, event: str, data: dict) -> None:
    """Emit a named event to all sockets that have joined the session room."""
    # ponytail: room is always raw UUID — strip HMAC suffix if present
    room = session_id.rsplit(".", 1)[0] if "." in session_id else session_id
    await sio.emit(event, data, room=room)


@sio.event
async def connect(sid, environ, auth):
    print(f"[WS] Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"[WS] Client disconnected: {sid}")


@sio.event
async def join_session(sid, data):
    """Client sends {session_id} to subscribe to that session's events."""
    session_id = data.get("session_id", "").strip()
    if not session_id:
        return
    # ponytail: strip HMAC suffix if present so room name is always the raw UUID
    raw_id = session_id.rsplit(".", 1)[0] if "." in session_id else session_id
    await sio.enter_room(sid, raw_id)
    print(f"[WS] {sid} joined room: {raw_id}")
    await sio.emit("joined", {"session_id": session_id}, to=sid)
