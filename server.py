import uvicorn
import asyncio
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal
import PyPDF2
import io
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from swarm import app as swarm_app
from socket_server import sio, socket_app, emit_to_session
from security import sign_session_id, verify_session_id, check_backend_token

import contextlib

active_runs = set()

def get_tracing_context(tracing: str, api_key: str, project: str, endpoint: str):
    """ponytail: Programmatic LangSmith tracing context wrapper."""
    if tracing == "true" and api_key:
        try:
            from langsmith import Client
            from langchain_core.tracers.context import tracing_v2_enabled
            client = Client(api_key=api_key, api_url=endpoint or "https://api.smith.langchain.com")
            return tracing_v2_enabled(project_name=project or "CriticAI", client=client)
        except Exception as e:
            print(f"[TRACING ERROR] Failed to initialize LangSmith tracing: {e}")
    
    @contextlib.contextmanager
    def no_op():
        yield
    return no_op()


async def extract_text(file: UploadFile) -> str:
    if not file:
        return ""
    if file.filename.endswith(".txt"):
        return (await file.read()).decode("utf-8")
    elif file.filename.endswith(".pdf"):
        pdf_bytes = io.BytesIO(await file.read())
        reader = PyPDF2.PdfReader(pdf_bytes)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    return ""

app = FastAPI(
    title="CriticAI Swarm API",
    description="""
    Premium Multi-Agent Orchestration Swarm API. 
    
    Provides endpoints for bootstrapping task plans, dispatching parallel AI workers, 
    injecting targeted or global human feedback loops, and persisting session progress.
    """,
    version="1.0.0",
    contact={
        "name": "CriticAI Engineering Team",
        "url": "https://github.com/raj/CriticAI",
    }
)

# Secure CORS: Allow local development origins only (no wildcards)
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartRequest(BaseModel):
    session_id: str
    task_prompt: str
    guidelines_path: Optional[str] = "brand_guidelines.txt"

class FeedbackRequest(BaseModel):
    session_id: str
    feedback: str
    type: str = "global"
    agent: Optional[str] = None

class StartResponse(BaseModel):
    status: Literal["completed", "pending_review"]
    deliverables: dict[str, str]
    execution_plan: list[dict]
    agent_statuses: dict[str, str]
    agent_durations: dict[str, float] = Field(default_factory=dict)

class FeedbackResponse(BaseModel):
    status: Literal["completed", "pending_review"]
    deliverables: dict[str, str]
    execution_plan: list[dict]
    agent_statuses: dict[str, str]
    agent_durations: dict[str, float] = Field(default_factory=dict)

class SessionResponse(BaseModel):
    status: Literal["completed", "pending_review", "processing"]
    deliverables: dict[str, str]
    execution_plan: list[dict]
    agent_statuses: dict[str, str]
    agent_durations: dict[str, float] = Field(default_factory=dict)

class VerifyKeyRequest(BaseModel):
    key: str

@app.post("/api/verify-key", tags=["General"], summary="Verify OpenRouter API Key")
async def verify_openrouter_key(req: VerifyKeyRequest):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bearer {req.key}"}
            res = await client.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
            if res.status_code == 200:
                data = res.json()
                key_data = data.get("data", {})
                if key_data.get("is_valid", True):
                    limit = key_data.get("limit") or "No limit"
                    usage = key_data.get("usage") or 0
                    return {"valid": True, "label": key_data.get("label", "Key"), "limit": limit, "usage": usage}
            return {"valid": False, "error": f"OpenRouter returned status {res.status_code}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}

@app.get("/", tags=["General"], summary="Root Health Check")
def read_root():
    return {"message": "CriticAI Swarm API is running! 🚀"}

@app.post("/api/start", tags=["Swarm Lifecycle"], summary="Initialize Swarm Campaign", response_model=StartResponse)
async def start_swarm(
    session_id: str = Form(...),
    task_prompt: str = Form(...),
    guidelines_path: Optional[str] = Form("brand_guidelines.txt"),
    file: UploadFile = File(None),
    x_llm_provider: Optional[str] = Header(None, alias="X-LLM-Provider"),
    x_groq_api_key: Optional[str] = Header(None, alias="X-Groq-API-Key"),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key"),
    x_openrouter_api_key: Optional[str] = Header(None, alias="X-OpenRouter-API-Key"),
    x_langsmith_tracing: Optional[str] = Header(None, alias="X-Langsmith-Tracing"),
    x_langsmith_api_key: Optional[str] = Header(None, alias="X-Langsmith-API-Key"),
    x_langsmith_project: Optional[str] = Header(None, alias="X-Langsmith-Project"),
    x_langsmith_endpoint: Optional[str] = Header(None, alias="X-Langsmith-Endpoint"),
    x_backend_token: Optional[str] = Header(None, alias="X-Backend-Token"),
):
    """Initializes the graph and runs until the first HITL interrupt."""
    check_backend_token(x_backend_token)
    verified_session_id = verify_session_id(session_id)
    if not verified_session_id:
        raise HTTPException(status_code=403, detail="Invalid session signature")
        
    config = {
        "configurable": {
            "thread_id": verified_session_id,
            "llm_provider": x_llm_provider,
            "groq_api_key": x_groq_api_key,
            "gemini_api_key": x_gemini_api_key,
            "openrouter_api_key": x_openrouter_api_key
        }
    }
    
    file_content = await extract_text(file) if file else ""
    final_prompt = f"User Request: {task_prompt}\n\nAttached Document Content:\n{file_content}" if file_content else task_prompt
    
    initial_state = {
        "task_prompt":      final_prompt,
        "user_brief":       task_prompt,
        "guidelines_path":  guidelines_path,
        "execution_plan":   [],
        "deliverables":     {},
        # Legacy creative-pipeline defaults (backward-compat with frontend)
        "slogan_draft":       "",
        "image_prompt_draft": "",
        "internal_feedback":  "",
        "revision_count":     0,
        "final_outputs":      [],
    }
    
    # Start the graph (it will pause since we compiled with interrupt_before=["hitl"])
    active_runs.add(verified_session_id)
    try:
        with get_tracing_context(x_langsmith_tracing, x_langsmith_api_key, x_langsmith_project, x_langsmith_endpoint):
            swarm_app.invoke(initial_state, config=config)
    finally:
        active_runs.discard(verified_session_id)
    
    # Get the current state snapshot after interrupt
    try:
        state_snapshot = swarm_app.get_state(config)
        is_completed = not state_snapshot.next
        return {
            "status": "completed" if is_completed else "pending_review",
            "deliverables": state_snapshot.values.get("deliverables", {}),
            "execution_plan": state_snapshot.values.get("execution_plan", []),
            "agent_statuses": state_snapshot.values.get("agent_statuses", {}),
            "agent_durations": state_snapshot.values.get("agent_durations", {}),
        }
    except Exception:
        return {
            "status": "completed",
            "deliverables": {},
            "execution_plan": [],
            "agent_statuses": {},
            "agent_durations": {},
        }

@app.post("/api/feedback", tags=["Swarm Lifecycle"], summary="Submit HITL Feedback", response_model=FeedbackResponse)
async def provide_feedback(
    session_id: str = Form(...),
    feedback: str = Form(...),
    type: str = Form(...),
    target_agent: Optional[str] = Form(None),
    file: UploadFile = File(None),
    x_llm_provider: Optional[str] = Header(None, alias="X-LLM-Provider"),
    x_groq_api_key: Optional[str] = Header(None, alias="X-Groq-API-Key"),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key"),
    x_openrouter_api_key: Optional[str] = Header(None, alias="X-OpenRouter-API-Key"),
    x_langsmith_tracing: Optional[str] = Header(None, alias="X-Langsmith-Tracing"),
    x_langsmith_api_key: Optional[str] = Header(None, alias="X-Langsmith-API-Key"),
    x_langsmith_project: Optional[str] = Header(None, alias="X-Langsmith-Project"),
    x_langsmith_endpoint: Optional[str] = Header(None, alias="X-Langsmith-Endpoint"),
    x_backend_token: Optional[str] = Header(None, alias="X-Backend-Token"),
):
    """Injects user feedback and resumes the graph."""
    check_backend_token(x_backend_token)
    verified_session_id = verify_session_id(session_id)
    if not verified_session_id:
        raise HTTPException(status_code=403, detail="Invalid session signature")
        
    config = {
        "configurable": {
            "thread_id": verified_session_id,
            "llm_provider": x_llm_provider,
            "groq_api_key": x_groq_api_key,
            "gemini_api_key": x_gemini_api_key,
            "openrouter_api_key": x_openrouter_api_key
        }
    }
    try:
        state_snapshot = swarm_app.get_state(config)
    except Exception:
        return {
            "status": "completed",
            "deliverables": {},
            "execution_plan": [],
            "agent_statuses": {},
            "agent_durations": {},
        }
    
    if not state_snapshot.next:
        return {
            "status": "completed",
            "deliverables": state_snapshot.values.get("deliverables", {}),
            "execution_plan": state_snapshot.values.get("execution_plan", []),
            "agent_statuses": state_snapshot.values.get("agent_statuses", {}),
            "agent_durations": state_snapshot.values.get("agent_durations", {}),
        }

    file_content = await extract_text(file) if file else ""
    user_feedback = f"User Feedback: {feedback}\n\nAttached Document Content:\n{file_content}" if file_content else feedback
    
    fb_type = type
    target = target_agent
    
    # Check if user approved the draft
    if user_feedback.strip().lower() in ["approve", "proceed", "yes", "y", "approved"]:
        # Inject approval into state
        swarm_app.update_state(config, {"feedback": "HITL_APPROVED", "feedback_type": "approved"})
    else:
        # Inject revision feedback into state
        new_revision_count = state_snapshot.values.get("revision_count", 0) + 1
        
        update_payload = {
            "feedback": user_feedback,
            "feedback_type": fb_type,
            "target_agent": target,
            "revision_count": new_revision_count,
            "messages": [HumanMessage(content=f"Feedback ({fb_type}):\n{user_feedback}")]
        }

        # For global feedback, we also update the task_prompt so the orchestrator
        # sees the new instructions in its 'Continuous Manager' loop.
        if fb_type == "global":
            update_payload["task_prompt"] = user_feedback
            update_payload["user_brief"] = feedback

        swarm_app.update_state(config, update_payload)
        
    # Resume the graph
    active_runs.add(verified_session_id)
    try:
        with get_tracing_context(x_langsmith_tracing, x_langsmith_api_key, x_langsmith_project, x_langsmith_endpoint):
            swarm_app.invoke(None, config=config)
    finally:
        active_runs.discard(verified_session_id)
    
    # Get the new state snapshot after it pauses again (or finishes)
    try:
        new_snapshot = swarm_app.get_state(config)
        is_completed = not new_snapshot.next
        return {
            "status": "completed" if is_completed else "pending_review",
            "deliverables": new_snapshot.values.get("deliverables", {}),
            "execution_plan": new_snapshot.values.get("execution_plan", []),
            "agent_statuses": new_snapshot.values.get("agent_statuses", {}),
            "agent_durations": new_snapshot.values.get("agent_durations", {}),
        }
    except Exception:
        return {
            "status": "completed",
            "deliverables": {},
            "execution_plan": [],
            "agent_statuses": {},
            "agent_durations": {},
        }

class SessionCreateResponse(BaseModel):
    session_id: str

@app.post("/api/sessions", tags=["Session History"], summary="Create Secure Signed Session", response_model=SessionCreateResponse)
def create_session(x_backend_token: Optional[str] = Header(None, alias="X-Backend-Token")):
    check_backend_token(x_backend_token)
    import uuid
    raw_id = str(uuid.uuid4())
    signed_id = sign_session_id(raw_id)
    return {"session_id": signed_id}

@app.get("/api/sessions/{session_id}", tags=["Session History"], summary="Retrieve Session State", response_model=SessionResponse)
async def get_session(session_id: str, x_backend_token: Optional[str] = Header(None, alias="X-Backend-Token")):
    check_backend_token(x_backend_token)
    verified_id = verify_session_id(session_id)
    if not verified_id:
        raise HTTPException(status_code=403, detail="Invalid session signature")
        
    config = {"configurable": {"thread_id": verified_id}}
    state_snapshot = swarm_app.get_state(config)
    
    if not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Session not found")
        
    is_completed = not state_snapshot.next
    if verified_id in active_runs:
        status = "processing"
    else:
        status = "completed" if is_completed else "pending_review"

    return {
        "status": status,
        "deliverables": state_snapshot.values.get("deliverables", {}),
        "execution_plan": state_snapshot.values.get("execution_plan", []),
        "agent_statuses": state_snapshot.values.get("agent_statuses", {}),
        "agent_durations": state_snapshot.values.get("agent_durations", {}),
    }

# ── Mount Socket.IO under /ws (existing /api routes are untouched) ────────────
app.mount("/ws/socket.io", socket_app)

@app.on_event("startup")
async def startup_event():
    from swarm import set_main_loop
    set_main_loop(asyncio.get_running_loop())


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET EVENT HANDLERS  (Socket.IO)
# ══════════════════════════════════════════════════════════════════════════════

@sio.event
async def start_campaign(sid, data: dict):
    """
    Socket event: client sends campaign details, server runs swarm and streams events.

    Expected data keys:
      session_id, task_prompt, guidelines_path (opt),
      file_content (opt, base64 str), file_name (opt),
      provider, groq_api_key, gemini_api_key, openrouter_api_key,
      langsmith_tracing, langsmith_api_key, langsmith_project, langsmith_endpoint,
      backend_token (opt)
    """
    # 🛡️ Verify backend access token
    try:
        check_backend_token(data.get("backend_token"))
    except Exception as e:
        await sio.emit("swarm_error", {"message": "Unauthorized backend access token"}, to=sid)
        return

    session_id = data.get("session_id", "")
    # 🛡️ Verify session signature
    verified_session_id = verify_session_id(session_id)
    if not verified_session_id:
        await sio.emit("swarm_error", {"message": "Invalid session signature"}, to=sid)
        return

    task_prompt       = data.get("task_prompt", "")
    guidelines_path   = data.get("guidelines_path", "brand_guidelines.txt")
    provider          = data.get("provider", "")
    groq_key          = data.get("groq_api_key", "")
    gemini_key        = data.get("gemini_api_key", "")
    openrouter_key    = data.get("openrouter_api_key", "")
    langsmith_tracing = data.get("langsmith_tracing", "false")
    langsmith_api_key = data.get("langsmith_api_key", "")
    langsmith_project = data.get("langsmith_project", "CriticAI")
    langsmith_endpoint = data.get("langsmith_endpoint", "https://api.smith.langchain.com")

    # Decode base64 file if present
    file_content_text = ""
    file_name = data.get("file_name", "")
    file_b64  = data.get("file_content", "")
    if file_b64 and file_name:
        import base64
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
            "thread_id":         verified_session_id,
            "llm_provider":      provider,
            "groq_api_key":      groq_key,
            "gemini_api_key":    gemini_key,
            "openrouter_api_key": openrouter_key,
            "ws_session_id":     verified_session_id,
        }
    }

    initial_state = {
        "task_prompt":     final_prompt,
        "user_brief":      task_prompt,
        "guidelines_path": guidelines_path,
        "execution_plan":  [],
        "deliverables":    {},
        "revision_count":  0,
        "final_outputs":   [],
    }

    await emit_to_session(verified_session_id, "swarm_status", {"status": "starting"})

    def run_swarm():
        active_runs.add(verified_session_id)
        try:
            with get_tracing_context(langsmith_tracing, langsmith_api_key, langsmith_project, langsmith_endpoint):
                return swarm_app.invoke(initial_state, config=config)
        finally:
            active_runs.discard(verified_session_id)

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, run_swarm)
        state_snapshot = swarm_app.get_state(config)
        is_completed   = not state_snapshot.next
        agent_durations = state_snapshot.values.get("agent_durations", {})
        await emit_to_session(verified_session_id, "swarm_complete", {
            "status":          "completed" if is_completed else "pending_review",
            "deliverables":    state_snapshot.values.get("deliverables", {}),
            "execution_plan":  state_snapshot.values.get("execution_plan", []),
            "agent_statuses":  state_snapshot.values.get("agent_statuses", {}),
            "agent_durations": agent_durations,
        })
    except Exception as e:
        await emit_to_session(verified_session_id, "swarm_error", {"message": str(e)})


@sio.event
async def send_feedback(sid, data: dict):
    """
    Socket event: client sends HITL feedback to resume the graph.

    Expected data keys:
      session_id, feedback, type (global|targeted), target_agent (opt),
      file_content (opt, base64), file_name (opt),
      provider, groq_api_key, gemini_api_key, openrouter_api_key,
      backend_token (opt)
    """
    # 🛡️ Verify backend access token
    try:
        check_backend_token(data.get("backend_token"))
    except Exception as e:
        await sio.emit("swarm_error", {"message": "Unauthorized backend access token"}, to=sid)
        return

    session_id = data.get("session_id", "")
    # 🛡️ Verify session signature
    verified_session_id = verify_session_id(session_id)
    if not verified_session_id:
        await sio.emit("swarm_error", {"message": "Invalid session signature"}, to=sid)
        return

    feedback_text  = data.get("feedback", "")
    fb_type        = data.get("type", "global")
    target_agent   = data.get("target_agent")
    provider       = data.get("provider", "")
    groq_key       = data.get("groq_api_key", "")
    gemini_key     = data.get("gemini_api_key", "")
    openrouter_key = data.get("openrouter_api_key", "")
    langsmith_tracing  = data.get("langsmith_tracing", "false")
    langsmith_api_key  = data.get("langsmith_api_key", "")
    langsmith_project  = data.get("langsmith_project", "CriticAI")
    langsmith_endpoint = data.get("langsmith_endpoint", "https://api.smith.langchain.com")

    # Decode file if present
    file_content_text = ""
    file_name = data.get("file_name", "")
    file_b64  = data.get("file_content", "")
    if file_b64 and file_name:
        import base64
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
            "thread_id":          verified_session_id,
            "llm_provider":       provider,
            "groq_api_key":       groq_key,
            "gemini_api_key":     gemini_key,
            "openrouter_api_key": openrouter_key,
            "ws_session_id":      verified_session_id,
        }
    }

    try:
        state_snapshot = swarm_app.get_state(config)
    except Exception:
        await emit_to_session(verified_session_id, "swarm_complete", {
            "status": "completed", "deliverables": {}, "execution_plan": [],
            "agent_statuses": {}, "agent_durations": {},
        })
        return

    is_completed = not state_snapshot.next
    intent = "REVISION"
    
    if is_completed:
        intent = "CONVERSATIONAL"
    elif fb_type == "global":
        intent_system = """You are an intent classifier for a multi-agent workspace.
Analyze the user's message.
Classify the user's intent into one of the following:
1. "CONVERSATIONAL": The user is asking a question about the outputs, requesting an explanation, asking for advice, saying thank you, or having a general chat.
2. "REVISION": The user wants to modify, rewrite, change, expand, or revise the campaign deliverables, or change the execution plan/hire new agents.

Respond with exactly one word: CONVERSATIONAL or REVISION.
Do not explain your reasoning."""
        try:
            classifier_client = get_llm_client(config, is_orchestrator=True)
            messages = [
                SystemMessage(content=intent_system),
                HumanMessage(content=f"User Message: {feedback_text}\n\nDeliverables generated: {list(state_snapshot.values.get('deliverables', {}).keys())}")
            ]
            intent_res = invoke_llm_with_timeout(classifier_client, messages, timeout_seconds=15.0)
            intent = intent_res.content.strip().upper()
        except Exception:
            intent = "REVISION"

    if intent == "CONVERSATIONAL":
        reply_system = """You are the Lead Critic & Orchestrator of CriticAI.
The user is asking a follow-up question or chatting about the campaign deliverables.
Answer their question directly and professionally based on the project brief, the plan, and the deliverables.
Be helpful, engaging, and clear. Format your response in clean Markdown.

Project Brief:
{user_brief}

Execution Plan:
{execution_plan}

Agent Deliverables:
{deliverables}
"""
        try:
            client = get_llm_client(config, is_orchestrator=False)
            history = state_snapshot.values.get("messages", [])
            system_content = reply_system.format(
                user_brief=state_snapshot.values.get("user_brief", ""),
                execution_plan=state_snapshot.values.get("execution_plan", []),
                deliverables=state_snapshot.values.get("deliverables", {})
            )
            reply_messages = [SystemMessage(content=system_content)] + list(history) + [HumanMessage(content=feedback_text)]
            
            reply_res = invoke_llm_with_timeout(client, reply_messages, timeout_seconds=45.0)
            reply_content = reply_res.content.strip()
            
            # ponytail: save both the user message and the conversational answer in SQLite checkpointer state
            swarm_app.update_state(config, {
                "messages": [
                    HumanMessage(content=feedback_text),
                    AIMessage(content=reply_content)
                ]
            })
            
            await emit_to_session(verified_session_id, "swarm_complete", {
                "status": "completed" if is_completed else "pending_review",
                "deliverables": state_snapshot.values.get("deliverables", {}),
                "execution_plan": state_snapshot.values.get("execution_plan", []),
                "agent_statuses": state_snapshot.values.get("agent_statuses", {}),
                "agent_durations": state_snapshot.values.get("agent_durations", {}),
                "conversational_reply": reply_content
            })
            return
        except Exception as e:
            await emit_to_session(verified_session_id, "swarm_error", {"message": f"Conversational reply failed: {str(e)}"})
            return

    if user_feedback.strip().lower() in ["approve", "proceed", "yes", "y", "approved"]:
        swarm_app.update_state(config, {"feedback": "HITL_APPROVED", "feedback_type": "approved"})
    else:
        new_revision_count = state_snapshot.values.get("revision_count", 0) + 1
        update_payload = {
            "feedback":       user_feedback,
            "feedback_type":  fb_type,
            "target_agent":   target_agent,
            "revision_count": new_revision_count,
            "messages":       [HumanMessage(content=f"Feedback ({fb_type}):\n{user_feedback}")],
        }
        if fb_type == "global":
            update_payload["task_prompt"] = user_feedback
            update_payload["user_brief"]  = feedback_text
        swarm_app.update_state(config, update_payload)

    await emit_to_session(verified_session_id, "swarm_status", {"status": "resuming"})

    def resume_swarm():
        active_runs.add(verified_session_id)
        try:
            with get_tracing_context(langsmith_tracing, langsmith_api_key, langsmith_project, langsmith_endpoint):
                return swarm_app.invoke(None, config=config)
        finally:
            active_runs.discard(verified_session_id)

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, resume_swarm)
        new_snapshot = swarm_app.get_state(config)
        is_completed  = not new_snapshot.next
        await emit_to_session(verified_session_id, "swarm_complete", {
            "status":          "completed" if is_completed else "pending_review",
            "deliverables":    new_snapshot.values.get("deliverables", {}),
            "execution_plan":  new_snapshot.values.get("execution_plan", []),
            "agent_statuses":  new_snapshot.values.get("agent_statuses", {}),
            "agent_durations": new_snapshot.values.get("agent_durations", {}),
        })
    except Exception as e:
        await emit_to_session(verified_session_id, "swarm_error", {"message": str(e)})


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
