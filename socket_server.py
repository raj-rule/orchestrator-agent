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

socket_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")


async def emit_to_session(session_id: str, event: str, data: dict) -> None:
    """Emit a named event to all sockets that have joined the session room."""
    await sio.emit(event, data, room=session_id)


@sio.event
async def connect(sid, environ, auth):
    print(f"[WS] Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"[WS] Client disconnected: {sid}")


@sio.event
async def join_session(sid, data):
    """Client sends {session_id} to subscribe to that session's events."""
    session_id = data.get("session_id", "")
    if session_id:
        await sio.enter_room(sid, session_id)
        print(f"[WS] {sid} joined room: {session_id}")
        await sio.emit("joined", {"session_id": session_id}, to=sid)
