# WebSocket Live Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add WebSocket-based live streaming to CriticAI so the UI is non-blocking during generation and shows per-agent status updates plus token-by-token output in a Live Terminal sidebar panel.

**Architecture:** The FastAPI backend is extended with `python-socketio` over ASGI. The blocking `swarm_app.invoke()` call is moved to a thread executor so the event loop never stalls. The swarm nodes emit progress events (agent_started, token, agent_done, swarm_complete) through a per-session callback injected via `RunnableConfig`. The React frontend replaces all `fetch()` calls with a single persistent `socket.io-client` connection and adds a Live Terminal panel.

**Tech Stack:** `python-socketio>=5.11`, `socket.io-client@4.x` (React), FastAPI ASGI mount, `asyncio.run_in_executor`, LangChain streaming `.astream()`

## Global Constraints

- Python backend runs in `venv` at `c:\Users\raj\OneDrive\Desktop\CriticAI\venv`
- Frontend is a Vite/React app at `swarm-ui/`
- Backend port: `8000`, Frontend dev port: `5173`
- CORS allowed origins: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`
- Do NOT remove the existing HTTP endpoints `/api/start`, `/api/feedback`, `/api/sessions/{id}` — keep them as fallback
- All socket events use `snake_case` names
- Session IDs are UUID strings, used as socket.io rooms

---

### Task 1: Install Dependencies

**Files:**
- Modify: `requirements.txt`
- Run in: `c:\Users\raj\OneDrive\Desktop\CriticAI\`

- [ ] **Step 1: Add python-socketio to requirements.txt**

```
python-socketio>=5.11.0
```

Append to the end of `requirements.txt`.

- [ ] **Step 2: Install it into the venv**

```bash
venv\Scripts\pip install "python-socketio>=5.11.0"
```

Expected: `Successfully installed python-socketio-5.x.x`

- [ ] **Step 3: Install socket.io-client in the frontend**

```bash
cd swarm-ui && npm install socket.io-client@4
```

Expected: `added N packages`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt swarm-ui/package.json swarm-ui/package-lock.json
git commit -m "chore: add python-socketio and socket.io-client deps"
```

---

### Task 2: Backend — Create `socket_server.py` (WebSocket event hub)

**Files:**
- Create: `c:\Users\raj\OneDrive\Desktop\CriticAI\socket_server.py`

**Interfaces:**
- Produces:
  - `sio` — the `socketio.AsyncServer` instance (imported by `server.py`)
  - `emit_to_session(session_id, event, data)` — async helper used by swarm callbacks
  - `socket_app` — the ASGI sub-application to mount

- [ ] **Step 1: Create `socket_server.py`**

```python
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
```

- [ ] **Step 2: Verify import works**

```bash
venv\Scripts\python -c "from socket_server import sio, socket_app, emit_to_session; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add socket_server.py
git commit -m "feat: add socket_server.py with AsyncServer and room helpers"
```

---

### Task 3: Backend — Mount Socket.IO into `server.py` and add WS campaign handler

**Files:**
- Modify: `c:\Users\raj\OneDrive\Desktop\CriticAI\server.py`

**Interfaces:**
- Consumes: `socket_server.sio`, `socket_server.socket_app`, `socket_server.emit_to_session`
- Produces: socket events `start_campaign` and `send_feedback` handled server-side

- [ ] **Step 1: Add imports and mount socket_app in server.py**

At the top of `server.py`, after all existing imports, add:

```python
import asyncio
from socket_server import sio, socket_app, emit_to_session
```

At the bottom of `server.py`, BEFORE the `if __name__ == "__main__":` block, add:

```python
# Mount Socket.IO under /ws so the existing /api routes are untouched
from starlette.routing import Mount
app.mount("/ws", socket_app)
```

- [ ] **Step 2: Add the `start_campaign` socket event handler in server.py**

Add this function at the bottom of `server.py`, before the `if __name__` block:

```python
@sio.event
async def start_campaign(sid, data: dict):
    """
    Socket event: client sends campaign details, server runs swarm and streams events.
    
    Expected data keys:
      session_id, task_prompt, guidelines_path (opt),
      file_content (opt, base64 str), file_name (opt),
      provider, groq_api_key, gemini_api_key, openrouter_api_key,
      langsmith_tracing, langsmith_api_key, langsmith_project, langsmith_endpoint
    """
    session_id = data.get("session_id", "")
    task_prompt = data.get("task_prompt", "")
    guidelines_path = data.get("guidelines_path", "brand_guidelines.txt")
    provider = data.get("provider", "")
    groq_key = data.get("groq_api_key", "")
    gemini_key = data.get("gemini_api_key", "")
    openrouter_key = data.get("openrouter_api_key", "")
    langsmith_tracing = data.get("langsmith_tracing", "false")
    langsmith_api_key = data.get("langsmith_api_key", "")
    langsmith_project = data.get("langsmith_project", "CriticAI")
    langsmith_endpoint = data.get("langsmith_endpoint", "https://api.smith.langchain.com")

    # Decode base64 file if present
    file_content_text = ""
    file_name = data.get("file_name", "")
    file_b64 = data.get("file_content", "")
    if file_b64 and file_name:
        import base64, io
        raw = base64.b64decode(file_b64)
        if file_name.endswith(".txt"):
            file_content_text = raw.decode("utf-8", errors="ignore")
        elif file_name.endswith(".pdf"):
            pdf_bytes = io.BytesIO(raw)
            reader = PyPDF2.PdfReader(pdf_bytes)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    file_content_text += extracted + "\n"

    final_prompt = (
        f"User Request: {task_prompt}\n\nAttached Document Content:\n{file_content_text}"
        if file_content_text else task_prompt
    )

    config = {
        "configurable": {
            "thread_id": session_id,
            "llm_provider": provider,
            "groq_api_key": groq_key,
            "gemini_api_key": gemini_key,
            "openrouter_api_key": openrouter_key,
            "ws_session_id": session_id,  # used by streaming callbacks
        }
    }

    initial_state = {
        "task_prompt": final_prompt,
        "user_brief": task_prompt,
        "guidelines_path": guidelines_path,
        "execution_plan": [],
        "deliverables": {},
        "slogan_draft": "",
        "image_prompt_draft": "",
        "internal_feedback": "",
        "revision_count": 0,
        "final_outputs": [],
    }

    await emit_to_session(session_id, "swarm_status", {"status": "starting"})

    def run_swarm():
        from langchain_core.tracers.context import tracing_v2_enabled
        if langsmith_tracing == "true" and langsmith_api_key:
            with tracing_v2_enabled(
                project_name=langsmith_project,
                api_key=langsmith_api_key,
                endpoint=langsmith_endpoint,
            ):
                return swarm_app.invoke(initial_state, config=config)
        else:
            return swarm_app.invoke(initial_state, config=config)

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_swarm)
        state_snapshot = swarm_app.get_state(config)
        is_completed = not state_snapshot.next
        deliverables = state_snapshot.values.get("deliverables", {})
        execution_plan = state_snapshot.values.get("execution_plan", [])
        agent_statuses = state_snapshot.values.get("agent_statuses", {})
        await emit_to_session(session_id, "swarm_complete", {
            "status": "completed" if is_completed else "pending_review",
            "deliverables": deliverables,
            "execution_plan": execution_plan,
            "agent_statuses": agent_statuses,
        })
    except Exception as e:
        await emit_to_session(session_id, "swarm_error", {"message": str(e)})
```

- [ ] **Step 3: Add the `send_feedback` socket event handler**

Append after `start_campaign`:

```python
@sio.event
async def send_feedback(sid, data: dict):
    """
    Socket event: client sends HITL feedback to resume the graph.
    
    Expected data keys:
      session_id, feedback, type (global|targeted), target_agent (opt),
      file_content (opt, base64), file_name (opt),
      provider, groq_api_key, gemini_api_key, openrouter_api_key
    """
    session_id = data.get("session_id", "")
    feedback_text = data.get("feedback", "")
    fb_type = data.get("type", "global")
    target_agent = data.get("target_agent")
    provider = data.get("provider", "")
    groq_key = data.get("groq_api_key", "")
    gemini_key = data.get("gemini_api_key", "")
    openrouter_key = data.get("openrouter_api_key", "")

    # Decode file if present
    file_content_text = ""
    file_name = data.get("file_name", "")
    file_b64 = data.get("file_content", "")
    if file_b64 and file_name:
        import base64, io
        raw = base64.b64decode(file_b64)
        if file_name.endswith(".txt"):
            file_content_text = raw.decode("utf-8", errors="ignore")
        elif file_name.endswith(".pdf"):
            pdf_bytes = io.BytesIO(raw)
            reader = PyPDF2.PdfReader(pdf_bytes)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    file_content_text += extracted + "\n"

    user_feedback = (
        f"User Feedback: {feedback_text}\n\nAttached Document Content:\n{file_content_text}"
        if file_content_text else feedback_text
    )

    config = {
        "configurable": {
            "thread_id": session_id,
            "llm_provider": provider,
            "groq_api_key": groq_key,
            "gemini_api_key": gemini_key,
            "openrouter_api_key": openrouter_key,
            "ws_session_id": session_id,
        }
    }

    try:
        state_snapshot = swarm_app.get_state(config)
    except Exception:
        await emit_to_session(session_id, "swarm_complete", {
            "status": "completed", "deliverables": {}, "execution_plan": [], "agent_statuses": {}
        })
        return

    if not state_snapshot.next:
        await emit_to_session(session_id, "swarm_complete", {
            "status": "completed",
            "deliverables": state_snapshot.values.get("deliverables", {}),
            "execution_plan": state_snapshot.values.get("execution_plan", []),
            "agent_statuses": state_snapshot.values.get("agent_statuses", {}),
        })
        return

    if user_feedback.strip().lower() in ["approve", "proceed", "yes", "y", "approved"]:
        swarm_app.update_state(config, {"feedback": "HITL_APPROVED", "feedback_type": "approved"})
    else:
        new_revision_count = state_snapshot.values.get("revision_count", 0) + 1
        from langchain_core.messages import HumanMessage as HMsg
        update_payload = {
            "feedback": user_feedback,
            "feedback_type": fb_type,
            "target_agent": target_agent,
            "revision_count": new_revision_count,
            "messages": [HMsg(content=f"Feedback ({fb_type}):\n{user_feedback}")],
        }
        if fb_type == "global":
            update_payload["task_prompt"] = user_feedback
            update_payload["user_brief"] = feedback_text
        swarm_app.update_state(config, update_payload)

    await emit_to_session(session_id, "swarm_status", {"status": "resuming"})

    def resume_swarm():
        return swarm_app.invoke(None, config=config)

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, resume_swarm)
        new_snapshot = swarm_app.get_state(config)
        is_completed = not new_snapshot.next
        await emit_to_session(session_id, "swarm_complete", {
            "status": "completed" if is_completed else "pending_review",
            "deliverables": new_snapshot.values.get("deliverables", {}),
            "execution_plan": new_snapshot.values.get("execution_plan", []),
            "agent_statuses": new_snapshot.values.get("agent_statuses", {}),
        })
    except Exception as e:
        await emit_to_session(session_id, "swarm_error", {"message": str(e)})
```

- [ ] **Step 4: Verify server starts without error**

```bash
venv\Scripts\python -c "from server import app; print('Server imports OK')"
```

Expected: `Server imports OK`

- [ ] **Step 5: Commit**

```bash
git add server.py socket_server.py
git commit -m "feat: mount socketio and add start_campaign / send_feedback WS handlers"
```

---

### Task 4: Backend — Inject streaming callbacks into swarm nodes

**Files:**
- Modify: `c:\Users\raj\OneDrive\Desktop\CriticAI\swarm.py`

**Interfaces:**
- Consumes: `socket_server.emit_to_session`, `RunnableConfig` (already in scope in every node)
- Produces: live socket events `agent_started`, `agent_token`, `agent_done`, `agent_critic_reviewing` emitted per agent during execution

> **Note:** LangGraph nodes run synchronously in a thread executor (from Task 3). We cannot `await` inside them directly. Instead we use `asyncio.run_coroutine_threadsafe` to fire-and-forget the async emit from the sync thread.

- [ ] **Step 1: Add a sync-safe emit helper at the top of swarm.py**

After the `load_dotenv()` line, add:

```python
import asyncio as _asyncio

def _sync_emit(session_id: str, event: str, data: dict) -> None:
    """
    Fire-and-forget socket emit callable from a synchronous LangGraph node.
    Works because the FastAPI event loop is running in the main thread while
    LangGraph runs in a thread-pool executor.
    """
    if not session_id:
        return
    try:
        from socket_server import emit_to_session
        loop = _asyncio.get_event_loop()
        _asyncio.run_coroutine_threadsafe(emit_to_session(session_id, event, data), loop)
    except Exception as exc:
        print(f"[WS EMIT ERROR] {exc}")
```

- [ ] **Step 2: Emit agent_started and agent_done in orchestrator_node**

In `orchestrator_node`, after the `return` dict is assembled (currently lines ~302-305), add the emit call:

Find this block (around line 302):
```python
    return {
        "execution_plan": execution_plan,
        "agent_statuses": {task["agent_role"]: "working" for task in execution_plan}
    }
```

Replace with:
```python
    ws_session_id = (config or {}).get("configurable", {}).get("ws_session_id", "")
    _sync_emit(ws_session_id, "plan_ready", {
        "execution_plan": execution_plan,
        "agent_count": len(execution_plan),
    })
    return {
        "execution_plan": execution_plan,
        "agent_statuses": {task["agent_role"]: "working" for task in execution_plan}
    }
```

- [ ] **Step 3: Emit agent_started, agent_token, and agent_done in worker_node**

In `worker_node`, find the line:
```python
    print(f"\n[WORKER:{role}] Starting task... (dynamic LLM + tools)")
```

Right after it, add:
```python
    ws_session_id = (config or {}).get("configurable", {}).get("ws_session_id", "")
    _sync_emit(ws_session_id, "agent_started", {"role": role, "task": task_desc[:120]})
```

Then find the success path where `output` is set and status is `"completed"` (around line 434):
```python
        print(f"[WORKER:{role}] Done. ({len(output)} chars)")
        status = "completed"
```

Right after `status = "completed"`, add:
```python
        _sync_emit(ws_session_id, "agent_done", {"role": role, "output": output})
```

- [ ] **Step 4: Emit agent_critic_reviewing in critic_node**

In `critic_node`, find:
```python
    print(f"\n[CRITIC:{role}] Reviewing deliverable...")
```

Right after it, add:
```python
    ws_session_id = (config or {}).get("configurable", {}).get("ws_session_id", "")
    _sync_emit(ws_session_id, "agent_critic_reviewing", {"role": role})
```

- [ ] **Step 5: Verify swarm.py imports cleanly**

```bash
venv\Scripts\python -c "from swarm import app; print('swarm OK')"
```

Expected: `swarm OK`

- [ ] **Step 6: Commit**

```bash
git add swarm.py
git commit -m "feat: inject websocket streaming callbacks into orchestrator, worker and critic nodes"
```

---

### Task 5: Frontend — Replace fetch with socket.io in App.jsx + add Live Terminal

**Files:**
- Modify: `c:\Users\raj\OneDrive\Desktop\CriticAI\swarm-ui\src\App.jsx`

This is the largest task. We make targeted surgical edits:
1. Import `io` from `socket.io-client`
2. Create a single socket connection with a `useRef`
3. Wire up socket event listeners in `useEffect`
4. Replace `startCampaign` and `handleRevise` to use `socket.emit` instead of `fetch`
5. Add `liveTerminal` state for per-agent live output
6. Add a Live Terminal panel in the left sidebar

- [ ] **Step 1: Add socket.io import at the top of App.jsx**

Find the first line of App.jsx:
```jsx
import React, { useState, useEffect, useRef } from 'react';
```

Replace with:
```jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
```

- [ ] **Step 2: Add socketRef and liveTerminal state inside the App() component**

Find the existing state block (right after `const fileInputRef = useRef(null);`):
```jsx
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
```

Replace with:
```jsx
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const socketRef = useRef(null);
  const terminalEndRef = useRef(null);

  // Live terminal: array of { role, status, partialOutput }
  const [liveAgents, setLiveAgents] = useState([]);
  const [terminalVisible, setTerminalVisible] = useState(false);
```

- [ ] **Step 3: Add socket setup useEffect**

After the existing `useEffect` that handles session recovery (the one with `loadSession`), add a new effect:

```jsx
  // ── Socket.IO setup ────────────────────────────────────────────────────
  useEffect(() => {
    const socket = io('http://localhost:8000', {
      path: '/ws/socket.io',
      transports: ['websocket'],
      reconnection: true,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('[WS] Connected:', socket.id);
      // Join the current session room immediately on connect/reconnect
      if (sessionId) {
        socket.emit('join_session', { session_id: sessionId });
      }
    });

    socket.on('plan_ready', (data) => {
      // Reset live terminal with new agents
      setLiveAgents(
        (data.execution_plan || []).map(t => ({
          role: t.agent_role,
          status: 'pending',
          partialOutput: '',
        }))
      );
      setTerminalVisible(true);
    });

    socket.on('agent_started', (data) => {
      setLiveAgents(prev =>
        prev.map(a => a.role === data.role ? { ...a, status: 'working' } : a)
      );
    });

    socket.on('agent_token', (data) => {
      setLiveAgents(prev =>
        prev.map(a =>
          a.role === data.role
            ? { ...a, partialOutput: a.partialOutput + data.token }
            : a
        )
      );
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    });

    socket.on('agent_critic_reviewing', (data) => {
      setLiveAgents(prev =>
        prev.map(a => a.role === data.role ? { ...a, status: 'reviewing' } : a)
      );
    });

    socket.on('agent_done', (data) => {
      setLiveAgents(prev =>
        prev.map(a =>
          a.role === data.role
            ? { ...a, status: 'done', partialOutput: data.output || a.partialOutput }
            : a
        )
      );
    });

    socket.on('swarm_status', (data) => {
      console.log('[WS] swarm_status:', data.status);
    });

    socket.on('swarm_complete', (data) => {
      setIsProcessing(false);
      if (data.agent_statuses) setAgentStatuses(data.agent_statuses);
      const deliverables = data.deliverables && Object.keys(data.deliverables).length > 0
        ? data.deliverables
        : (latestDeliverables || {});
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'draft',
          content: { deliverables, executionPlan: data.execution_plan || [] },
          isAwaitingFeedback: data.status !== 'completed',
          isFinal: data.status === 'completed',
        }
      ]);
      // Mark all agents as done in terminal
      setLiveAgents(prev => prev.map(a => ({ ...a, status: a.status === 'done' ? 'done' : 'done' })));
    });

    socket.on('swarm_error', (data) => {
      setIsProcessing(false);
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'text',
          content: `System Error: ${data.message}`,
        }
      ]);
    });

    return () => {
      socket.disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-join room when sessionId changes (user switches session)
  useEffect(() => {
    if (socketRef.current?.connected && sessionId) {
      socketRef.current.emit('join_session', { session_id: sessionId });
    }
  }, [sessionId]);
```

- [ ] **Step 4: Replace startCampaign to use socket.emit**

Find the full `startCampaign` function (lines ~201-261 in original) and replace it entirely:

```jsx
  const startCampaign = useCallback(async (promptText) => {
    setIsProcessing(true);
    setActiveView('main');
    setLiveAgents([]);
    setTerminalVisible(true);

    // Encode attached file as base64 if present
    let fileContent = '';
    let fileName = '';
    if (attachedFile) {
      fileName = attachedFile.name;
      const arrayBuffer = await attachedFile.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
      fileContent = btoa(binary);
    }

    // Ensure we're in the right room before emitting
    socketRef.current?.emit('join_session', { session_id: sessionId });

    socketRef.current?.emit('start_campaign', {
      session_id: sessionId,
      task_prompt: promptText,
      guidelines_path: guidelinesPath || 'brand_guidelines.txt',
      file_content: fileContent,
      file_name: fileName,
      provider,
      groq_api_key: groqKey,
      gemini_api_key: geminiKey,
      openrouter_api_key: openrouterKey,
      langsmith_tracing: langsmithEnabled ? 'true' : 'false',
      langsmith_api_key: langsmithKey,
      langsmith_project: langsmithProject,
      langsmith_endpoint: langsmithEndpoint,
    });

    if (attachedFile) setAttachedFile(null);
  }, [sessionId, guidelinesPath, attachedFile, provider, groqKey, geminiKey, openrouterKey,
      langsmithEnabled, langsmithKey, langsmithProject, langsmithEndpoint]);
```

- [ ] **Step 5: Replace handleRevise to use socket.emit**

Find the full `handleRevise` function and replace it:

```jsx
  const handleRevise = useCallback(async (feedbackText, targetAgent = null, isApproved = false) => {
    if (isProcessing) return;

    setMessages(prev => prev.map(msg =>
      msg.type === 'draft' ? { ...msg, isAwaitingFeedback: false, isFinal: isApproved } : msg
    ));

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user',
      type: 'text',
      content: isApproved ? '✅ Approve and finalize.' : feedbackText,
    };
    setMessages(prev => [...prev, userMsg]);

    if (isApproved) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'ai',
        type: 'text',
        content: 'Campaign finalized successfully! All assets have been exported.',
      }]);
      setActiveView('main');
      return;
    }

    setIsProcessing(true);
    setActiveView('main');
    setLiveAgents([]);
    setTerminalVisible(true);

    // Encode attached file as base64 if present
    let fileContent = '';
    let fileName = '';
    if (attachedFile) {
      fileName = attachedFile.name;
      const arrayBuffer = await attachedFile.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
      fileContent = btoa(binary);
    }

    socketRef.current?.emit('join_session', { session_id: sessionId });
    socketRef.current?.emit('send_feedback', {
      session_id: sessionId,
      feedback: feedbackText,
      type: targetAgent ? 'targeted' : 'global',
      target_agent: targetAgent || null,
      file_content: fileContent,
      file_name: fileName,
      provider,
      groq_api_key: groqKey,
      gemini_api_key: geminiKey,
      openrouter_api_key: openrouterKey,
      langsmith_tracing: langsmithEnabled ? 'true' : 'false',
      langsmith_api_key: langsmithKey,
      langsmith_project: langsmithProject,
      langsmith_endpoint: langsmithEndpoint,
    });

    if (attachedFile) setAttachedFile(null);
  }, [isProcessing, sessionId, attachedFile, provider, groqKey, geminiKey, openrouterKey,
      langsmithEnabled, langsmithKey, langsmithProject, langsmithEndpoint]);
```

- [ ] **Step 6: Add Live Terminal panel to the sidebar JSX**

In the sidebar section, find the "Active Campaign" section which ends with `</AnimatePresence>` and `</div>`. Right after the closing `</div>` of the "Active Campaign" section (before the "Recent Sessions" section), add the Live Terminal:

```jsx
              {/* Live Terminal */}
              <AnimatePresence>
                {terminalVisible && liveAgents.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="px-3 pt-2 pb-3 border-t border-white/5"
                  >
                    <div className="flex items-center justify-between px-2 mb-2">
                      <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                        <Activity size={11} className="text-emerald-400 animate-pulse" />
                        Live Terminal
                      </div>
                      <button
                        onClick={() => setTerminalVisible(false)}
                        className="text-zinc-600 hover:text-zinc-400 transition-colors"
                      >
                        <X size={12} />
                      </button>
                    </div>
                    <div className="bg-zinc-950 border border-white/5 rounded-lg overflow-hidden">
                      {/* Agent Status Bubbles */}
                      <div className="flex flex-wrap gap-1.5 p-2 border-b border-white/5">
                        {liveAgents.map(agent => (
                          <span
                            key={agent.role}
                            className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-widest border transition-all ${
                              agent.status === 'done'
                                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                                : agent.status === 'reviewing'
                                ? 'border-violet-500/30 bg-violet-500/10 text-violet-400'
                                : agent.status === 'working'
                                ? 'border-amber-500/30 bg-amber-500/10 text-amber-400 animate-pulse'
                                : 'border-zinc-700 bg-zinc-900 text-zinc-600'
                            }`}
                          >
                            {agent.role.length > 14 ? agent.role.slice(0, 14) + '…' : agent.role}
                          </span>
                        ))}
                      </div>
                      {/* Scrollable output */}
                      <div className="h-40 overflow-y-auto font-mono text-[10px] leading-relaxed text-emerald-300/80 p-2 space-y-1">
                        {liveAgents.filter(a => a.partialOutput).map(agent => (
                          <div key={agent.role}>
                            <span className="text-zinc-500">[{agent.role.slice(0,12)}]</span>{' '}
                            <span>{agent.partialOutput.slice(-400)}</span>
                          </div>
                        ))}
                        {liveAgents.every(a => !a.partialOutput) && (
                          <div className="text-zinc-600 italic">Waiting for agents to start...</div>
                        )}
                        <div ref={terminalEndRef} />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
```

- [ ] **Step 7: Verify the frontend builds without errors**

```bash
cd swarm-ui && npm run build 2>&1 | tail -20
```

Expected: `✓ built in Xs` with no red errors.

- [ ] **Step 8: Commit**

```bash
git add swarm-ui/src/App.jsx
git commit -m "feat: replace fetch with socket.io-client, add Live Terminal sidebar panel"
```

---

### Task 6: Smoke Test End-to-End

**Files:** None (verification only)

- [ ] **Step 1: Start the backend**

```bash
venv\Scripts\uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Expected: `Uvicorn running on http://0.0.0.0:8000`

- [ ] **Step 2: Start the frontend**

```bash
cd swarm-ui && npm run dev
```

Expected: `Local: http://localhost:5173/`

- [ ] **Step 3: Open browser at http://localhost:5173**

Check browser DevTools → Network → WS tab — you should see a WebSocket connection to `ws://localhost:8000/ws/socket.io/...`

- [ ] **Step 4: Send a test campaign prompt**

Type a short task (e.g. "Create a marketing plan for a new coffee brand") and press Enter.

Expected:
- The Live Terminal panel appears in the sidebar immediately
- Agent status bubbles appear (amber = working, violet = reviewing, green = done)
- Output text scrolls live in the terminal box as agents complete
- The main chat shows the "Swarm Execution Complete" card when all done
- You can freely switch sessions in the sidebar during generation — the UI does NOT freeze

- [ ] **Step 5: Test feedback**

After the swarm completes, send a global revision feedback.

Expected: Terminal reactivates, shows agents working on revision, final card appears.

- [ ] **Step 6: Commit final state**

```bash
git add -A
git commit -m "feat: websocket live streaming complete - end-to-end verified"
```
