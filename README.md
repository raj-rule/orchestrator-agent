# 🤖 CriticAI: Secure Multi-Agent Orchestration Swarm

**CriticAI** is a premium, secure multi-agent workflow orchestration system designed to automate complex, multi-stage campaigns, technical plans, and content generation. Built using **FastAPI**, **LangGraph**, and **React (Vite)**, it deploys an elite swarm of autonomous AI agents that collaborate, execute tasks in parallel, review each other's deliverables, and incorporate Human-in-the-Loop (HITL) feedback.

---

## 🎨 Architecture & Workflow

```
[ User Prompt / Attached Files ]
               │
               ▼
   [ 🛡️ Security Guardrails ] ─────────► (Blocks Prompt Injections & Harmful Inputs)
               │ (Passed)
               ▼
   [ 🧠 Orchestrator Agent ] ─────────► (Decomposes task into a structured project plan)
               │
      ┌────────┼────────┐
      ▼        ▼        ▼  (Parallel Send API Worker Dispatch)
   [Worker] [Worker] [Worker] ────────► (Copywriter, GTM Strategist, AI Architect, etc.)
      │        │        │
      └────────┼────────┘
               ▼
   [ 🔬 Critic / Review Loop ] ───────► (Validates deliverables; triggers up to 2 revisions)
               │ (Halts)
               ▼
   [ 💬 HITL Collaboration ] ────────► (Awaits user approval, targeted or global revisions)
               │ (Approved)
               ▼
   [ 📁 Final Deliverables ] ────────► (Consolidated Markdown report compiled locally)
```

---

## 🛡️ Security & Privacy Hardening

CriticAI is designed with recruiter-facing and enterprise privacy standards:
1. **Cryptographic Session Signing**: All chat session IDs are signed server-side using **HMAC-SHA256** with a secret key (`CRITICAI_SESSION_SECRET`). This prevents session guessing, tampering, or state hijacking by external parties.
2. **Backend Authentication Token**: An optional backend protection token (`CRITICAI_BACKEND_TOKEN`) can be set. When enabled, the backend validates an `X-Backend-Token` header for all REST endpoints and Socket.IO events, blocking unauthorized access.
3. **Secure Local Credentials**: LLM API keys are stored solely in the user's browser `localStorage`. They are transmitted directly to the local FastAPI server via custom headers and are never written to disk or sent to a remote database.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+** (Python 3.11 recommended)
- **Node.js 18+** & **NPM**
- **Docker & Docker Compose** (Optional, for containerized run)

### 1. Environment Configuration
Create a `.env` file in the project root by copying the template:
```bash
cp .env.example .env
```
Open `.env` and fill in your keys:
```env
# Get your API key from https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Add Tavily API Key for web search capabilities
TAVILY_API_KEY=your_tavily_api_key_here
```

### 2. Fast Bootstrapping (Windows)
Double-click the **`start.bat`** script in the root directory. The script automatically:
1. Recreates/repairs the Python virtual environment (`venv`) if missing.
2. Installs backend dependencies.
3. Installs frontend packages (`npm install` inside `swarm-ui/`).
4. Starts both the FastAPI server (`http://localhost:8000`) and the Vite frontend (`http://localhost:5173`) concurrently.

---

## 🧪 Testing and Verification

CriticAI features a unit test suite that runs in a fully self-contained environment (all LLMs are mocked out-of-the-box):

### Run Backend Test Suite
Ensure the virtual environment is active, then run:
```bash
pytest
```
*Note: All tests pass without requiring active LLM API keys.*

---

## 🐳 Docker Deployment

To launch the full backend (FastAPI + WebSocket server) and frontend (Nginx hosting React bundle) using Docker Compose:

```bash
# Build and run containers
docker-compose up --build
```
Once booted:
- Access the frontend dashboard at: **`http://localhost:5173`**
- Access the FastAPI Swagger documentation at: **`http://localhost:8000/docs`**

---

## 🛠️ Technology Stack
- **Backend**: FastAPI, Uvicorn, LangGraph (StateGraph checkpointer), LangChain (OpenAI/OpenRouter bindings), SQLite (persistent states), Python-SocketIO.
- **Frontend**: React 18, Vite, TailwindCSS, Framer Motion (animations), Lucide React (icons), Socket.io Client.
