# Optimization & Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a CI/CD test pipeline, dynamic LangSmith telemetry, automated FastAPI Swagger enhancements, and token optimizations to reduce redundant LLM context usage.

**Architecture:** 
1. Use GitHub Actions for CI/CD.
2. Intercept custom telemetry HTTP headers on the FastAPI server and wrap swarm graph runs dynamically with LangChain's `tracing_v2_enabled` context manager.
3. Define explicit Pydantic response models, tags, and custom metadata for OpenAPI.
4. Clean worker revision loops and attached document propagation by separating `user_brief` and stripping reviewer feedback markdown.

**Tech Stack:** Python 3.10+, FastAPI, LangGraph, LangChain Core, PyTest, GitHub Actions, React (Vite).

## Global Constraints
- Target Python 3.10+ compatibility.
- Ensure all tests pass via pytest without requiring active LLM API keys.
- Store telemetry keys in browser localStorage and send via headers. Do not store credentials on the server.

---

### Task 1: GitHub Actions CI/CD Pipeline

**Files:**
- Create: `.github/workflows/test.yml`

**Interfaces:**
- Consumes: Existing pytest test suite in `tests/`
- Produces: GitHub Action run status

- [ ] **Step 1: Create the workflow file**

Write the following content to `.github/workflows/test.yml`:
```yaml
name: Python Testing CI

on:
  push:
    branches: [ master, main ]
  pull_request:
    branches: [ master, main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - name: Check out repository
      uses: actions/checkout@v4

    - name: Set up Python 3.10
      uses: actions/setup-python@v5
      with:
        python-version: "3.10"
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest

    - name: Run test suite
      run: |
        pytest
```

- [ ] **Step 2: Verify locally using a git add commit**

Run: `git add .github/workflows/test.yml`
Expected: File staged for commit.

- [ ] **Step 3: Commit**

Run: `git commit -m "ci: add GitHub Actions workflow for pytest execution"`
Expected: Commit successful.

---

### Task 2: Token Optimization - Feedback Cleaning Utility

**Files:**
- Modify: `swarm.py`
- Test: `tests/test_swarm.py`

**Interfaces:**
- Consumes: `SwarmState` deliverables
- Produces: `clean_previous_output(output: str) -> str`

- [ ] **Step 1: Write the failing test in `tests/test_swarm.py`**

Open `tests/test_swarm.py` and append the following unit test:
```python
def test_clean_previous_output():
    from swarm import clean_previous_output
    text_with_fb = "Slogan: Brew the future!\n\n*Reviewer Feedback (Internal Revision 1):\nSlogan must be shorter."
    assert clean_previous_output(text_with_fb) == "Slogan: Brew the future!"
    assert clean_previous_output("Slogan: Brew the future!") == "Slogan: Brew the future!"
    assert clean_previous_output("") == ""
```

- [ ] **Step 2: Run pytest to verify test failure**

Run: `venv\Scripts\pytest tests/test_swarm.py::test_clean_previous_output`
Expected: Fails with `ImportError: cannot import name 'clean_previous_output'`.

- [ ] **Step 3: Implement `clean_previous_output` in `swarm.py`**

Open `swarm.py` and insert the utility function around line 43 (after `_merge_dicts`):
```python
def clean_previous_output(output: str) -> str:
    """Strips reviewer feedback appended to deliverables from previous turns."""
    if not output:
        return ""
    # Split by the reviewer feedback markdown indicator and keep the prefix
    parts = re.split(r"\n\n\*Reviewer Feedback \(Internal Revision \d+\):\*", output)
    return parts[0].strip()
```

- [ ] **Step 4: Update `assign_workers` and `route_feedback` in `swarm.py`**

Update `previous_output` mapping in both functions in `swarm.py` to use `clean_previous_output`.

In `assign_workers` (around line 544):
```python
"previous_output":  clean_previous_output(state.get("deliverables", {}).get(task["agent_role"], "")),
```

In `route_feedback` (around line 578):
```python
"previous_output": clean_previous_output(state.get("deliverables", {}).get(target, "")),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\pytest tests/test_swarm.py::test_clean_previous_output`
Expected: PASS.
Run: `venv\Scripts\pytest`
Expected: All 9 tests PASS.

- [ ] **Step 6: Commit changes**

Run: `git commit -am "feat: implement clean_previous_output utility to optimize feedback tokens"`
Expected: Commit successful.

---

### Task 3: Token Optimization - Attached Document Isolation

**Files:**
- Modify: `swarm.py`, `server.py`
- Test: `tests/test_swarm.py`

**Interfaces:**
- Consumes: `SwarmState` (specifically `user_brief`)
- Produces: Isolated `user_brief` string passed to workers instead of `task_prompt`

- [ ] **Step 1: Write the test in `tests/test_swarm.py`**

Add the test for `user_brief` assignment:
```python
def test_user_brief_in_worker_state(mock_get_llm_client):
    from swarm import assign_workers
    state = {
        "task_prompt": "Task brief\n\nAttached Document Content:\nPDF TEXT",
        "user_brief": "Task brief",
        "guidelines_path": "brand_guidelines.txt",
        "execution_plan": [{"agent_role": "Copywriter", "task_description": "Write slogan", "action_type": "NEW_HIRE"}],
        "deliverables": {}
    }
    sends = assign_workers(state)
    assert len(sends) == 1
    assert sends[0].state["task_prompt"] == "Task brief"
```

- [ ] **Step 2: Run pytest to verify test failure**

Run: `venv\Scripts\pytest tests/test_swarm.py::test_user_brief_in_worker_state`
Expected: FAIL because `user_brief` is not yet populated or passed, and `sends[0].state["task_prompt"]` equals the full state `task_prompt`.

- [ ] **Step 3: Update `SwarmState` in `swarm.py`**

Add `user_brief: str` to `SwarmState` TypedDict around line 47:
```python
class SwarmState(TypedDict):
    # ── Core inputs ──────────────────────────────────────────────
    task_prompt: str          # The raw user request sent from the frontend
    user_brief: str           # The user request without attached file content
    guidelines_path: str      # Path to the brand-guidelines file
```

- [ ] **Step 4: Update `assign_workers` and `route_feedback` in `swarm.py`**

Update `task_prompt` inside worker state creation to prioritize `user_brief`.

In `assign_workers`:
```python
                "task_prompt":      state.get("user_brief", state["task_prompt"]),
```

In `route_feedback`:
```python
                    "task_prompt": state.get("user_brief", state["task_prompt"]),
```

- [ ] **Step 5: Update `server.py` to populate `user_brief`**

Open `server.py`. In `start_swarm` (around line 90) and `provide_feedback` (around line 157), update `initial_state` and feedback updates to set `user_brief`.

In `start_swarm`:
```python
    initial_state = {
        "task_prompt":      final_prompt,
        "user_brief":       task_prompt, # Core prompt without attachment
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
```

In `provide_feedback`:
```python
        update_payload = {
            "feedback": user_feedback,
            "feedback_type": fb_type,
            "target_agent": target,
            "revision_count": new_revision_count,
            "messages": [HumanMessage(content=f"Feedback ({fb_type}):\n{user_feedback}")]
        }

        # For global feedback, we also update the task_prompt and user_brief
        if fb_type == "global":
            update_payload["task_prompt"] = user_feedback
            update_payload["user_brief"] = feedback  # Clean feedback string
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `venv\Scripts\pytest tests/test_swarm.py::test_user_brief_in_worker_state`
Expected: PASS.
Run: `venv\Scripts\pytest`
Expected: All 10 tests PASS.

- [ ] **Step 7: Commit changes**

Run: `git commit -am "feat: implement user_brief state field to isolate large documents from workers"`
Expected: Commit successful.

---

### Task 4: Dynamic Observability (LangSmith)

**Files:**
- Modify: `server.py`, `swarm-ui/src/App.jsx`

**Interfaces:**
- Consumes: Custom HTTP Headers (`X-Langsmith-Tracing`, `X-Langsmith-API-Key`, etc.)
- Produces: Dynamic tracing integration in FastAPI server endpoint using `tracing_v2_enabled`

- [ ] **Step 1: Implement LangSmith header extraction in `server.py`**

In `server.py`, modify `/api/start` and `/api/feedback` to extract telemetry headers:
```python
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
    x_langsmith_tracing: Optional[str] = Header(None, alias="X-Langsmith-Tracing"),
    x_langsmith_api_key: Optional[str] = Header(None, alias="X-Langsmith-API-Key"),
    x_langsmith_project: Optional[str] = Header(None, alias="X-Langsmith-Project"),
    x_langsmith_endpoint: Optional[str] = Header(None, alias="X-Langsmith-Endpoint"),
):
```

Do the same for `provide_feedback`:
```python
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
    x_langsmith_tracing: Optional[str] = Header(None, alias="X-Langsmith-Tracing"),
    x_langsmith_api_key: Optional[str] = Header(None, alias="X-Langsmith-API-Key"),
    x_langsmith_project: Optional[str] = Header(None, alias="X-Langsmith-Project"),
    x_langsmith_endpoint: Optional[str] = Header(None, alias="X-Langsmith-Endpoint"),
):
```

- [ ] **Step 2: Apply `tracing_v2_enabled` in `server.py` endpoints**

Import `tracing_v2_enabled`:
```python
from langchain_core.tracers.context import tracing_v2_enabled
```

Wrap `swarm_app.invoke` in `start_swarm`:
```python
    # Start the graph dynamically tracing with LangSmith if enabled
    if x_langsmith_tracing == "true" and x_langsmith_api_key:
        with tracing_v2_enabled(
            project_name=x_langsmith_project or "CriticAI",
            api_key=x_langsmith_api_key,
            endpoint=x_langsmith_endpoint or "https://api.smith.langchain.com"
        ):
            swarm_app.invoke(initial_state, config=config)
    else:
        swarm_app.invoke(initial_state, config=config)
```

Wrap `swarm_app.invoke` in `provide_feedback`:
```python
    # Resume the graph dynamically tracing with LangSmith if enabled
    if x_langsmith_tracing == "true" and x_langsmith_api_key:
        with tracing_v2_enabled(
            project_name=x_langsmith_project or "CriticAI",
            api_key=x_langsmith_api_key,
            endpoint=x_langsmith_endpoint or "https://api.smith.langchain.com"
        ):
            swarm_app.invoke(None, config=config)
    else:
        swarm_app.invoke(None, config=config)
```

- [ ] **Step 3: Update Settings Modal and Fetch Headers in `swarm-ui/src/App.jsx`**

Open `App.jsx`.
Add LangSmith key state declarations:
```javascript
  const [langsmithEnabled, setLangsmithEnabled] = useState(() => localStorage.getItem('swarm_langsmith_enabled') === 'true');
  const [langsmithKey, setLangsmithKey] = useState(() => localStorage.getItem('swarm_langsmith_api_key') || '');
  const [langsmithProject, setLangsmithProject] = useState(() => localStorage.getItem('swarm_langsmith_project') || 'CriticAI');
  const [langsmithEndpoint, setLangsmithEndpoint] = useState(() => localStorage.getItem('swarm_langsmith_endpoint') || 'https://api.smith.langchain.com');
  const [showLangsmithKey, setShowLangsmithKey] = useState(false);
```

Update headers sent by `startCampaign` and `handleRevise`:
```javascript
        headers: {
          'X-LLM-Provider': provider,
          'X-Groq-API-Key': groqKey,
          'X-Gemini-API-Key': geminiKey,
          'X-OpenRouter-API-Key': openrouterKey,
          'X-Langsmith-Tracing': langsmithEnabled ? 'true' : 'false',
          'X-Langsmith-API-Key': langsmithKey,
          'X-Langsmith-Project': langsmithProject,
          'X-Langsmith-Endpoint': langsmithEndpoint,
        }
```

Add input controls in the Settings Modal in `App.jsx` (before the "Save Settings" button / around line 904):
```jsx
                <hr className="border-white/5" />

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">LangSmith Tracing</label>
                    <input 
                      type="checkbox" 
                      checked={langsmithEnabled} 
                      onChange={(e) => {
                        setLangsmithEnabled(e.target.checked);
                        localStorage.setItem('swarm_langsmith_enabled', e.target.checked);
                      }}
                      className="accent-white h-4 w-4 rounded border-zinc-700 bg-zinc-900"
                    />
                  </div>

                  {langsmithEnabled && (
                    <>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-zinc-300">LangSmith API Key</label>
                        <div className="relative flex items-center">
                          <input 
                            type={showLangsmithKey ? 'text' : 'password'}
                            value={langsmithKey}
                            onChange={(e) => {
                              setLangsmithKey(e.target.value);
                              localStorage.setItem('swarm_langsmith_api_key', e.target.value);
                            }}
                            placeholder="lsv2_pt_..."
                            className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-700 text-zinc-200 pr-10"
                          />
                          <button 
                            type="button" 
                            onClick={() => setShowLangsmithKey(!showLangsmithKey)}
                            className="absolute right-3 text-zinc-500 hover:text-zinc-300 transition-colors"
                          >
                            {showLangsmithKey ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-zinc-300">LangSmith Project</label>
                        <input 
                          type="text"
                          value={langsmithProject}
                          onChange={(e) => {
                            setLangsmithProject(e.target.value);
                            localStorage.setItem('swarm_langsmith_project', e.target.value);
                          }}
                          placeholder="CriticAI"
                          className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-700 text-zinc-200"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-zinc-300">LangSmith Endpoint</label>
                        <input 
                          type="text"
                          value={langsmithEndpoint}
                          onChange={(e) => {
                            setLangsmithEndpoint(e.target.value);
                            localStorage.setItem('swarm_langsmith_endpoint', e.target.value);
                          }}
                          placeholder="https://api.smith.langchain.com"
                          className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-700 text-zinc-200"
                        />
                      </div>
                    </>
                  )}
                </div>
```

- [ ] **Step 4: Run unit tests to ensure no regressions**

Run: `venv\Scripts\pytest`
Expected: All tests pass.

- [ ] **Step 5: Commit changes**

Run: `git commit -am "feat: add dynamic LangSmith tracing integration to server and settings UI"`
Expected: Commit successful.

---

### Task 5: API Documentation (Swagger/OpenAPI) Improvements

**Files:**
- Modify: `server.py`

**Interfaces:**
- Consumes: FastAPI App Configuration
- Produces: Rich custom OpenAPI Documentation schema and structured response types

- [ ] **Step 1: Define explicit Pydantic response models**

In `server.py`, define structural schemas for the endpoints:
```python
class AgentStatus(BaseModel):
    status: str
    role: str

class StartResponse(BaseModel):
    status: Literal["completed", "pending_review"]
    deliverables: dict[str, str] = Field(description="Dictionary mapping agent roles to their generated deliverables.")
    execution_plan: list[dict] = Field(description="The compiled project steps/assignments generated by the orchestrator.")
    agent_statuses: dict[str, str] = Field(description="Dictionary mapping active agent roles to their current working state.")

class FeedbackResponse(BaseModel):
    status: Literal["completed", "pending_review"]
    deliverables: dict[str, str]
    execution_plan: list[dict]
    agent_statuses: dict[str, str]

class SessionResponse(BaseModel):
    deliverables: dict[str, str]
    execution_plan: list[dict]
    agent_statuses: dict[str, str]
```

- [ ] **Step 2: Update FastAPI configuration and metadata**

Open `server.py` and enrich the `FastAPI` instance:
```python
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
```

- [ ] **Step 3: Enrich FastAPI Endpoint route parameters, tags, and response models**

Annotate route decorators:

```python
@app.get("/", tags=["General"], summary="Root Health Check")
def read_root():
    return {"message": "CriticAI Swarm API is running! 🚀"}

@app.post("/api/start", tags=["Swarm Lifecycle"], summary="Initialize Swarm Campaign", response_model=StartResponse)
async def start_swarm(...):
    # (impl unchanged, just add response_model, tags, summary)

@app.post("/api/feedback", tags=["Swarm Lifecycle"], summary="Submit HITL Feedback", response_model=FeedbackResponse)
async def provide_feedback(...):
    # (impl unchanged, just add response_model, tags, summary)

@app.get("/api/sessions/{session_id}", tags=["Session History"], summary="Retrieve Session State", response_model=SessionResponse)
async def get_session(session_id: str):
    # (impl unchanged, just add response_model, tags, summary)
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `venv\Scripts\pytest`
Expected: PASS

- [ ] **Step 5: Commit changes**

Run: `git commit -am "feat: improve FastAPI OpenAPI documentation with custom models and tags"`
Expected: Commit successful.
