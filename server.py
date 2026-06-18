import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import PyPDF2
import io

from langchain_core.messages import HumanMessage
from swarm import app as swarm_app

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

app = FastAPI(title="CriticAI Swarm API")

# Configure CORS to allow requests from the React frontend (Vite defaults to 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
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

@app.get("/")
def read_root():
    return {"message": "CriticAI Swarm API is running! 🚀"}

@app.post("/api/start")
async def start_swarm(
    session_id: str = Form(...),
    task_prompt: str = Form(...),
    guidelines_path: Optional[str] = Form("brand_guidelines.txt"),
    file: UploadFile = File(None),
    x_llm_provider: Optional[str] = Header(None, alias="X-LLM-Provider"),
    x_groq_api_key: Optional[str] = Header(None, alias="X-Groq-API-Key"),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key"),
    x_openrouter_api_key: Optional[str] = Header(None, alias="X-OpenRouter-API-Key"),
):
    """Initializes the graph and runs until the first HITL interrupt."""
    config = {
        "configurable": {
            "thread_id": session_id,
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
    swarm_app.invoke(initial_state, config=config)
    
    # Get the current state snapshot after interrupt
    state_snapshot = swarm_app.get_state(config)
    is_completed = not state_snapshot.next
    
    return {
        "status": "completed" if is_completed else "pending_review",
        "deliverables": state_snapshot.values.get("deliverables", {}),
        "execution_plan": state_snapshot.values.get("execution_plan", []),
        "agent_statuses": state_snapshot.values.get("agent_statuses", {})
    }

@app.post("/api/feedback")
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
):
    """Injects user feedback and resumes the graph."""
    config = {
        "configurable": {
            "thread_id": session_id,
            "llm_provider": x_llm_provider,
            "groq_api_key": x_groq_api_key,
            "gemini_api_key": x_gemini_api_key,
            "openrouter_api_key": x_openrouter_api_key
        }
    }
    state_snapshot = swarm_app.get_state(config)
    
    if not state_snapshot.next:
         return {"status": "completed", "message": "Graph already completed"}

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

        swarm_app.update_state(config, update_payload)
        
    # Resume the graph
    swarm_app.invoke(None, config=config)
    
    # Get the new state snapshot after it pauses again (or finishes)
    new_snapshot = swarm_app.get_state(config)
    is_completed = not new_snapshot.next
    
    return {
        "status": "completed" if is_completed else "pending_review",
        "deliverables": new_snapshot.values.get("deliverables", {}),
        "execution_plan": new_snapshot.values.get("execution_plan", []),
        "agent_statuses": new_snapshot.values.get("agent_statuses", {})
    }

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    config = {"configurable": {"thread_id": session_id}}
    state_snapshot = swarm_app.get_state(config)
    
    if not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "deliverables": state_snapshot.values.get("deliverables", {}),
        "execution_plan": state_snapshot.values.get("execution_plan", []),
        "agent_statuses": state_snapshot.values.get("agent_statuses", {})
    }

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
