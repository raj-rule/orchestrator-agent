import json
import operator
import os
import re
import sqlite3
import sys
import time
from typing import Annotated, Any, List, TypedDict, Literal
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_tavily import TavilySearch

load_dotenv()

# ==========================================
# 1. THE STATE (Dynamic Memory) & SCHEMAS
# ==========================================
class Assignment(BaseModel):
    reasoning: str = Field(description="Step-by-step chain of thought explaining why this specific agent role is required, and whether a new technical skill is needed.")
    action_type: Literal["NEW_HIRE", "EXISTING_ASSIGNMENT"] = Field(description="Must be NEW_HIRE if the exact technical skill is missing from the active agents.")
    agent_role: str = Field(description="The specific role of the agent.")
    task_description: str = Field(description="Detailed instructions for this agent.")

class OrchestratorPlan(BaseModel):
    assignments: List[Assignment]

# Custom reducer: merges two dicts instead of overwriting.
# Critical for parallel workers writing to `deliverables` simultaneously.
def _merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class SwarmState(TypedDict):
    # ── Core inputs ──────────────────────────────────────────────
    task_prompt: str          # The raw user request sent from the frontend
    guidelines_path: str      # Path to the brand-guidelines file

    # ── Orchestrator outputs ─────────────────────────────────────
    execution_plan: list[dict]
    # Each dict: { agent_role: str, task_description: str, status: str }

    # Annotated with operator.ior so parallel workers safely merge results
    # instead of the last writer silently overwriting the others.
    deliverables: Annotated[dict, operator.ior]
    agent_statuses: Annotated[dict, _merge_dicts]
    feedback_type: str
    target_agent: str

    # ── Legacy creative-pipeline fields (Phase 1 backward-compat) ─
    # Kept so server.py can still read slogan_draft / image_prompt_draft
    # without modification.  Will be retired in a later phase.
    slogan_draft: str
    image_prompt_draft: str
    internal_feedback: str
    current_draft: dict
    feedback: str
    revision_count: int
    messages: Annotated[list[AnyMessage], add_messages]
    final_outputs: Annotated[List[str], operator.add]


class WorkerState(TypedDict):
    """Scoped state passed to each dynamically-spawned worker via Send."""
    agent_role: str        # e.g. 'Market Strategist', 'CTO'
    task_description: str  # The specific deliverable this worker must produce
    task_prompt: str       # Overarching startup request (context)
    guidelines_path: str   # Path to brand-guidelines file
    feedback: str
    feedback_type: str
    previous_output: str


# ==========================================
# 2. THE LOCAL LLM & TOOLS  (legacy worker pipeline)
# ==========================================
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
    temperature=0.7,
)

tavily_tool = TavilySearch(max_results=3)

@tool
def read_brand_guidelines(file_path: str) -> str:
    """Reads the contents of the brand guidelines text file.
    Use this tool to ingest client constraints before generating the draft.
    INPUT: The path to the file, e.g., 'brand_guidelines.txt'."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found."
    except Exception as e:
        return f"Error reading file: {str(e)}"

tools_list = [tavily_tool, read_brand_guidelines]
llm_with_tools = llm.bind_tools(tools_list)


# ==========================================
# 3. GROQ ORCHESTRATOR LLM (Legacy globals)
# ==========================================
orchestrator_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    max_retries=3
)

local_llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
    temperature=0.7,
)

# ── Dynamic Model Client Factory ──────────────────────────────────
def get_llm_client(config: RunnableConfig = None, is_orchestrator: bool = False) -> Any:
    """
    Dynamically instantiates the LLM client based on the provided configuration.
    If provider and keys are missing from config, it falls back to environment variables.
    """
    configurable = config.get("configurable", {}) if config else {}
    provider = configurable.get("llm_provider", "").lower()
    
    # Retrieve keys from config
    groq_key = configurable.get("groq_api_key") or os.getenv("GROQ_API_KEY")
    gemini_key = configurable.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    openrouter_key = configurable.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")

    if provider == "groq" and groq_key:
        model = "llama-3.3-70b-versatile" if is_orchestrator else "llama-3.1-8b-instant"
        return ChatGroq(model=model, api_key=groq_key, temperature=0.2 if is_orchestrator else 0.7)
        
    elif provider == "gemini" and gemini_key:
        model = "gemini-1.5-flash"
        return ChatGoogleGenerativeAI(model=model, google_api_key=gemini_key, temperature=0.2 if is_orchestrator else 0.7)
        
    elif provider == "openrouter" and openrouter_key:
        # OpenRouter free tier or standard models
        model = "google/gemini-2.0-flash-exp:free" if is_orchestrator else "meta-llama/llama-3-8b-instruct:free"
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            model=model,
            temperature=0.2 if is_orchestrator else 0.7
        )
    
    # Fallbacks to env variables directly
    if os.getenv("GROQ_API_KEY"):
        model = "llama-3.3-70b-versatile" if is_orchestrator else "llama-3.1-8b-instant"
        return ChatGroq(model=model, api_key=os.getenv("GROQ_API_KEY"), temperature=0.2 if is_orchestrator else 0.7)
    elif os.getenv("GEMINI_API_KEY"):
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"), temperature=0.2 if is_orchestrator else 0.7)
    
    # Default backups
    if is_orchestrator:
        return orchestrator_llm
    else:
        return local_llm


# ==========================================
# 4. ORCHESTRATOR NODE  (Gemini-powered)
# ==========================================
def orchestrator_node(state: SwarmState, config: RunnableConfig = None) -> dict[str, Any]:
    """
    Phase 1 – Groq Orchestrator (Continuous Manager).
    """
    task_prompt = state.get("task_prompt", "")
    guidelines_path = state.get("guidelines_path", "brand_guidelines.txt")
    
    existing_agents = list(state.get("deliverables", {}).keys()) if state.get("deliverables") else []
    
    system_prompt = f"""You are the elite Technical Project Manager of an AI Swarm.
Current Active Agents in Workspace: {existing_agents}
User Request/Feedback: {task_prompt}

CRITICAL RULES FOR ASSIGNMENT:
1. STRICT SKILL MATCHING: Evaluate the technical requirements of the user request. A Content Writer CANNOT write code. A Marketer CANNOT design databases. 
2. SPAWNING NEW HIRES: If the required skill does not perfectly match an agent in {existing_agents}, you MUST use "NEW_HIRE" and invent a new highly technical role (e.g., 'Backend Python Engineer', 'React Native Dev').
3. TARGETED REVISIONS: ONLY route tasks to an existing agent (action_type: "EXISTING_ASSIGNMENT") if the user is explicitly asking to modify or expand upon that specific agent's previous deliverable.
4. TEAM WORK: You MUST ALWAYS spawn or assign AT LEAST TWO (2) distinct agents per request to encourage collaboration and cross-checking (e.g., a Developer and a QA Engineer, or a Writer and an Editor).

--- EXAMPLES OF CORRECT BEHAVIOR ---
Example 1:
Active Agents: ["B2B Copywriter"]
Request: "Write a Python FastAPI authentication script."
Correct Action: The request requires coding. A Copywriter cannot code. You MUST output reasoning explaining this, set action_type="NEW_HIRE", and invent agent_role="Backend Security Engineer".

Example 2:
Active Agents: ["B2B Copywriter", "Backend Security Engineer"]
Request: "Make the landing page pitch sound more aggressive."
Correct Action: The request is about copy. You already have a Copywriter. You MUST output reasoning explaining this, set action_type="EXISTING_ASSIGNMENT", and route to agent_role="B2B Copywriter".
------------------------------------
"""

    guidelines_hint = (
        f"The project has a brand-guidelines file at '{guidelines_path}'. "
        "Relevant agents should reference and respect those constraints."
        if guidelines_path
        else ""
    )

    human_content = (
        f"Startup Request:\n{task_prompt}\n\n"
        f"{guidelines_hint}"
    ).strip()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    print("\n[ORCHESTRATOR] Calling model to generate execution plan...")
    
    dyn_orchestrator_llm = get_llm_client(config, is_orchestrator=True)
    structured_llm = dyn_orchestrator_llm.with_structured_output(OrchestratorPlan)
    try:
        result = structured_llm.invoke(messages)
        
        print("\n=== ORCHESTRATOR BRAIN DUMP ===")
        for assignment in result.assignments:
            print(f"Reasoning: {assignment.reasoning}")
            print(f"Action: {assignment.action_type} | Role: {assignment.agent_role}")
            print("---")
        print("===============================\n")
        
        assignments = result.assignments
    except Exception as exc:
        print(f"⚠️  Orchestrator Structured Output error: {exc}")
        # Fallback
        from types import SimpleNamespace
        assignments = [
            SimpleNamespace(
                action_type="NEW_HIRE",
                agent_role="General Agent",
                task_description=task_prompt
            )
        ]

    execution_plan: list[dict] = []
    for assignment in assignments:
        role = assignment.agent_role
        action = assignment.action_type
        
        # Validation: If it claims to be existing but isn't in deliverables, force NEW_HIRE
        if action == "EXISTING_ASSIGNMENT" and role not in existing_agents:
            print(f"⚠️  Orchestrator tried to assign to non-existent agent '{role}'. Forcing NEW_HIRE.")
            action = "NEW_HIRE"
            
        execution_plan.append({
            "agent_role": role,
            "task_description": assignment.task_description,
            "status": "pending",
            "action_type": action
        })

    print(f"\n[PLAN] EXECUTION PLAN ({len(execution_plan)} tasks):")
    for i, task in enumerate(execution_plan, 1):
        print(f"  {i}. [{task['agent_role']}] ({task['action_type']}) -> {task['task_description'][:80]}...")

    return {
        "execution_plan": execution_plan,
        "agent_statuses": {task["agent_role"]: "working" for task in execution_plan}
    }


# ==========================================
# 5. DYNAMIC WORKER NODE  (Gemini-powered)
# ==========================================
_WORKER_SYSTEM = """\
You are a highly specialised AI agent. Your role is: {agent_role}.

You are part of a multi-agent swarm working on the following startup project:
"{task_prompt}"

Your specific assignment is:
{task_description}

Deliver a thorough, professional, and immediately actionable output for your
assignment. Structure your response with clear headings and bullet points where
appropriate. Be specific — avoid vague platitudes.
"""

def worker_node(state: WorkerState, config: RunnableConfig = None) -> dict[str, Any]:
    """
    Phase 2 – Generic Worker.

    Receives a WorkerState via Send, executes its assigned task, and returns
    its output merged into the main SwarmState's `deliverables` dict.
    """
    role        = state["agent_role"]
    task_desc   = state["task_description"]
    task_prompt = state["task_prompt"]
    g_path      = state.get("guidelines_path", "brand_guidelines.txt")
    feedback    = state.get("feedback", "")
    feedback_type = state.get("feedback_type", "")
    previous_output = state.get("previous_output", "")

    # Optionally inject brand guidelines as hard constraints
    guidelines_text = ""
    try:
        with open(g_path, "r", encoding="utf-8") as fh:
            guidelines_text = fh.read().strip()
    except Exception:
        pass

    constraints_block = (
        f"\n\nBRAND CONSTRAINTS (from {g_path} — treat as absolute rules):\n"
        f"{guidelines_text}"
        if guidelines_text
        else ""
    )

    system_content = (
        _WORKER_SYSTEM.format(
            agent_role=role,
            task_prompt=task_prompt,
            task_description=task_desc,
        )
        + constraints_block
    )

    if previous_output:
        system_content += f"\n\nHere is your previous draft:\n<previous_draft>\n{previous_output}\n</previous_draft>"

    if feedback:
        if feedback_type == "targeted":
            system_content += f"\n\nRevise your previous draft based on this targeted feedback:\n{feedback}"
        else:
            system_content += f"\n\nRevise your previous draft based on this global feedback:\n{feedback}"

    if len(task_prompt) > 2000:
        system_content += "\n\nWARNING: The user request contains extensive document content. Please be concise and focus only on your specific assignment."

    # Workers use dynamic LLM client
    dyn_worker_llm = get_llm_client(config, is_orchestrator=False)

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=f"Execute your assignment now. Be detailed and specific."),
    ]

    print(f"\n[WORKER:{role}] Starting task... (dynamic LLM)")
    try:
        response = dyn_worker_llm.invoke(messages)
        output   = response.content.strip()
        print(f"[WORKER:{role}] Done. ({len(output)} chars)")
        status = "completed"
    except Exception as e:
        print(f"Worker {role} failed: {e}")
        output = "⚠️ **System Notice:** This agent encountered an error or timed out due to hardware constraints. Please request a targeted revision to try again."
        status = "error"

    # Return targets SwarmState.deliverables — _merge_dicts reducer handles
    # concurrent writes from all parallel workers without data loss.
    return {
        "deliverables": {role: output},
        "agent_statuses": {role: status}
    }


# ==========================================
# 5b. DISPATCH EDGE  (Send API fan-out)
# ==========================================
def assign_workers(state: SwarmState) -> list[Send]:
    """
    Conditional edge called after `orchestrator`.

    Iterates `execution_plan` and issues one `Send` per task, which causes
    LangGraph to spawn all worker_node invocations in parallel.
    """
    return [
        Send(
            "worker_node",
            {
                "agent_role":       task["agent_role"],
                "task_description": task["task_description"],
                "task_prompt":      state["task_prompt"],
                "guidelines_path":  state.get("guidelines_path", "brand_guidelines.txt"),
                "feedback":         state.get("feedback", ""),
                "feedback_type":    state.get("feedback_type", ""),
                "previous_output":  state.get("deliverables", {}).get(task["agent_role"], "")
            },
        )
        for task in state["execution_plan"]
    ]


# ==========================================
# 5c. FEEDBACK ROUTING
# ==========================================
def route_feedback(state: SwarmState):
    fb_type = state.get("feedback_type", "")
    
    if fb_type == "targeted":
        target = state.get("target_agent", "")
        task_desc = ""
        for task in state.get("execution_plan", []):
            if task.get("agent_role") == target:
                task_desc = task.get("task_description", "")
                break
        
        return [
            Send(
                "worker_node",
                {
                    "agent_role": target,
                    "task_description": task_desc,
                    "task_prompt": state.get("task_prompt", ""),
                    "guidelines_path": state.get("guidelines_path", "brand_guidelines.txt"),
                    "feedback": state.get("feedback", ""),
                    "feedback_type": "targeted",
                    "previous_output": state.get("deliverables", {}).get(target, "")
                }
            )
        ]
    elif fb_type == "global":
        return "orchestrator"
    else:
        return "exporter"


# ==========================================
# 5. LEGACY CREATIVE PIPELINE NODES
# ==========================================
def copywriter_node(state: SwarmState):
    msgs = state.get("messages", [])
    g_path = state.get('guidelines_path', 'brand_guidelines.txt')
    internal_fb = state.get("internal_feedback", "")
    feedback = state.get("feedback", "")

    # Surface the canonical user task from the new field name
    task = state.get("task_prompt", "")

    feedback_block = ""
    if feedback and "HITL_APPROVED" not in feedback:
        feedback_block = (
            f"\n\n<CRITICAL_HUMAN_FEEDBACK>\n{feedback}\n</CRITICAL_HUMAN_FEEDBACK>\n"
            "WARNING: You MUST apply the feedback above immediately. If the user asks for a color change "
            "(e.g., 'rose-gold'), you MUST include it and overwrite previous colors."
        )

    sys_msg_content = (
        "You are an Expert Copywriter. "
        "Your ONLY job is to write a catchy marketing slogan for the user's task. "
        "You have access to the tavily_search_results_json tool to identify current trends, "
        f"and the read_brand_guidelines tool to read client constraints from: {g_path}. "
        "CRITICAL INSTRUCTION: The constraints found in the Brand Guidelines (via the read_brand_guidelines tool) are ABSOLUTE. "
        "They overrule all other instructions. If the user's task requests elements that violate the Brand Guidelines, "
        "you MUST adapt the concept to fit the guidelines. (e.g., If the user asks for a forest, but guidelines ban nature, "
        "you must design a digital or urban equivalent). Never ignore the brand rules. "
        "You MUST wrap your final slogan in `<slogan>...</slogan>` tags. "
        "Do NOT write an image prompt."
        + feedback_block
    )

    if not msgs:
        sys_msg = SystemMessage(content=sys_msg_content)
        human_msg = HumanMessage(content=f"Task: {task}")
        response = llm_with_tools.invoke([sys_msg, human_msg])
        return_msgs = [sys_msg, human_msg, response]
    else:
        if internal_fb:
            fb_msg = HumanMessage(content=f"Art Director Feedback: {internal_fb}\nPlease revise your slogan.")
            response = llm_with_tools.invoke(msgs + [fb_msg])
            return_msgs = [fb_msg, response]
        else:
            response = llm_with_tools.invoke(msgs)
            return_msgs = [response]

    slogan = state.get("slogan_draft", "")
    if response.content:
        match = re.search(r'<slogan>(.*?)</slogan>', response.content, re.DOTALL | re.IGNORECASE)
        if match:
            slogan = match.group(1).strip()

    return {
        "slogan_draft": slogan,
        "internal_feedback": "",
        "messages": return_msgs,
    }


def art_director_node(state: SwarmState):
    slogan = state.get("slogan_draft", "")
    feedback = state.get("feedback", "")
    g_path = state.get('guidelines_path', 'brand_guidelines.txt')
    task = state.get("task_prompt", "")

    words = slogan.split()
    if len(words) > 7:
        return {
            "internal_feedback": (
                f"The slogan '{slogan}' is {len(words)} words long. "
                "It must be 7 words or shorter. Make it punchier."
            )
        }

    try:
        with open(g_path, 'r', encoding='utf-8') as f:
            guidelines_text = f.read().strip()
    except Exception:
        guidelines_text = "No guidelines file found."

    guidelines_block = (
        f"<BRAND_CONSTRAINTS>\n{guidelines_text}\n</BRAND_CONSTRAINTS>\n"
        "WARNING: These constraints are absolute. Never generate elements that violate these rules, "
        "even if the user asks for them."
    )

    feedback_block = ""
    if feedback and "HITL_APPROVED" not in feedback:
        feedback_block = (
            f"\n\n<CRITICAL_HUMAN_FEEDBACK>\n{feedback}\n</CRITICAL_HUMAN_FEEDBACK>\n"
            "WARNING: You MUST apply the feedback above immediately. If the user asks for a color change "
            "(e.g., 'rose-gold'), you MUST include it and overwrite previous colors."
        )

    sys_msg = SystemMessage(
        content=(
            f"{guidelines_block}"
            "\n\nYou are an Expert Art Director. Your ONLY job is to write a highly detailed image generation prompt (for Midjourney/FLUX). "
            "CRITICAL RULE: The image prompt MUST integrate the provided slogan natively into the visual environment. "
            "You must explicitly state how the text appears (e.g., 'The text \"[SLOGAN]\" is engraved on...'). "
            "You MUST wrap your final image prompt in `<image_prompt>...</image_prompt>` tags."
            + feedback_block
        )
    )
    human_msg = HumanMessage(content=f"Task: {task}\n\nApproved Slogan: {slogan}")

    response = llm.invoke([sys_msg, human_msg])

    image_prompt = state.get("image_prompt_draft", "")
    if response.content:
        match = re.search(r'<image_prompt>(.*?)</image_prompt>', response.content, re.DOTALL | re.IGNORECASE)
        if match:
            image_prompt = match.group(1).strip()

    current_draft = {"slogan": slogan, "image_prompt": image_prompt}

    return {
        "internal_feedback": "",
        "feedback": "",
        "image_prompt_draft": image_prompt,
        "current_draft": current_draft,
        "messages": [response],
    }


def reviewer_node(state: SwarmState):
    task = state.get("task_prompt", "")
    current_draft = state.get("current_draft", {})
    revision_count = state.get("revision_count", 0)

    draft_str = (
        f"Slogan: {current_draft.get('slogan', '')}\n\n"
        f"Image Prompt: {current_draft.get('image_prompt', '')}"
    )

    system_message = SystemMessage(
        content=(
            "You are the Lead Creative Director. Review the draft. "
            "Does it contain a strong slogan AND a highly detailed image prompt with "
            "lighting/camera instructions? If yes, output exactly 'APPROVED'. "
            "If it is missing details, provide brief feedback."
        )
    )
    human_message = HumanMessage(content=f"Task: {task}\n\nCurrent Draft:\n{draft_str}")

    response = llm.invoke([system_message, human_message])

    return {
        "feedback": response.content,
        "revision_count": revision_count + 1,
        "messages": [HumanMessage(content=f"Feedback from Creative Director:\n{response.content}\n\nPlease revise.")],
    }


# ==========================================
# 6. ROUTING FUNCTIONS  (legacy pipeline)
# ==========================================
def route_review(state: SwarmState):
    feedback = state.get("feedback", "")
    revision_count = state.get("revision_count", 0)
    if "approved" in feedback.lower() or revision_count >= 3:
        return "hitl"
    return "copywriter"


def hitl_node(state: SwarmState):
    # Pass-through; graph interrupt is declared at compile time.
    return {}


def route_hitl(state: SwarmState):
    feedback = state.get("feedback", "")
    if "HITL_APPROVED" in feedback:
        return "exporter"
    return "copywriter"


def route_copywriter(state: SwarmState):
    msgs = state.get("messages", [])
    if msgs and hasattr(msgs[-1], 'tool_calls') and msgs[-1].tool_calls:
        return "tools"
    return "art_director"


def route_art_director(state: SwarmState):
    if state.get("internal_feedback"):
        return "copywriter"
    return "reviewer"


# ==========================================
# 7. EXPORTER NODE  (legacy pipeline)
# ==========================================
def export_deliverable_node(state: SwarmState):
    slogan = state.get("slogan_draft", "").strip()
    image_prompt = state.get("image_prompt_draft", "").strip()

    if not slogan and not image_prompt:
        return {"final_outputs": ["Error: No draft found to export."]}

    task = state.get("task_prompt", "Campaign")
    clean_draft = (
        f"# 🎯 Campaign Output\n\n"
        f"**Brief:** {task}\n\n"
        f"---\n\n"
        f"## ✍️ Slogan\n\n"
        f"{slogan}\n\n"
        f"---\n\n"
        f"## 🖼️ Image Generation Prompt\n\n"
        f"{image_prompt}\n"
    )

    os.makedirs("outputs", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"outputs/campaign_output_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(clean_draft)

    print(f"\n[EXPORT] Exported to: {filename}")
    return {"final_outputs": [f"Successfully exported draft to {filename}"]}


# ==========================================
# 8. COMPILE GRAPH
# ==========================================
# ── Phase 2 graph (Dynamic Worker Dispatch) ───────────────────────
#
#   orchestrator
#       │
#       └─ assign_workers() ──┬─ Send → worker_node  (parallel)
#                             ├─ Send → worker_node
#                             └─ Send → worker_node
#                                           │
#                                          END
#
# Legacy creative-pipeline nodes (copywriter / art_director / reviewer /
# hitl / exporter) are retained but commented out until Phase 3 re-wiring.
# ─────────────────────────────────────────────────────────────────

workflow = StateGraph(SwarmState)

tool_node = ToolNode(tools_list)

# ── Register nodes ────────────────────────────────────────────────
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("worker_node",  worker_node)        # Phase 2: dynamic workers
workflow.add_node("copywriter",   copywriter_node)
workflow.add_node("art_director", art_director_node)
workflow.add_node("reviewer",     reviewer_node)
workflow.add_node("tools",        tool_node)
workflow.add_node("hitl",         hitl_node)
workflow.add_node("exporter",     export_deliverable_node)

# ── Phase 2 active wiring ─────────────────────────────────────────
workflow.set_entry_point("orchestrator")

# Fan-out: orchestrator → N parallel worker_node invocations via Send
workflow.add_conditional_edges(
    "orchestrator",
    assign_workers,
    ["worker_node"],   # declare the possible target node(s)
)

# Each worker writes back to deliverables, then the graph converges at hitl
workflow.add_edge("worker_node", "hitl")

workflow.add_conditional_edges(
    "hitl",
    route_feedback,
    ["worker_node", "orchestrator", "exporter"]
)
workflow.add_edge("exporter", END)

# ── Legacy pipeline wiring (Phase 1 – commented out for Phase 3 re-wiring) ─
# workflow.add_conditional_edges("copywriter", route_copywriter, {"tools": "tools", "art_director": "art_director"})
# workflow.add_edge("tools", "copywriter")
# workflow.add_conditional_edges("art_director", route_art_director, {"copywriter": "copywriter", "reviewer": "reviewer"})
# workflow.add_conditional_edges("reviewer", route_review, {"hitl": "hitl", "copywriter": "copywriter"})
# workflow.add_conditional_edges("hitl", route_hitl, {"exporter": "exporter", "copywriter": "copywriter"})
# workflow.add_edge("exporter", END)

# Initialize SQLite checkpointer
conn = sqlite3.connect("swarm_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

# NOTE: interrupt_before=["hitl"] retained for future HITL re-integration
app = workflow.compile(checkpointer=memory, interrupt_before=["hitl"])


# ==========================================
# 9. TERMINAL SMOKE TEST
# ==========================================
if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("\n** DYNAMIC SWARM - PHASE 2 (Orchestrator + Parallel Workers) **")
    print("=" * 60)

    session_id = input("\nEnter Session ID (e.g., 'run_1'): ").strip() or "default_session"
    config = {"configurable": {"thread_id": session_id}}

    user_task = input("\nEnter your startup task prompt: ").strip()
    if not user_task:
        user_task = (
            "Launch 'BrewBot' - an AI-powered coffee subscription startup. "
            "We need a go-to-market strategy, a social media content plan, and "
            "a technical architecture for the recommendation engine."
        )

    guidelines_file = (
        input("\nGuidelines file path (default: brand_guidelines.txt): ").strip()
        or "brand_guidelines.txt"
    )

    initial_state = {
        "task_prompt":      user_task,
        "guidelines_path":  guidelines_file,
        "execution_plan":   [],
        "deliverables":     {},
        # Legacy fields - initialised to safe defaults
        "slogan_draft":       "",
        "image_prompt_draft": "",
        "internal_feedback":  "",
        "revision_count":     0,
        "final_outputs":      [],
    }

    result = app.invoke(initial_state, config=config)

    print("\n" + "=" * 60)
    print("SWARM EXECUTION COMPLETE")
    print("=" * 60)

    plan = result.get("execution_plan", [])
    deliverables = result.get("deliverables", {})

    print(f"\n[PLAN] {len(plan)} tasks dispatched to parallel workers:\n")
    for i, task in enumerate(plan, 1):
        role = task['agent_role']
        chars = len(deliverables.get(role, ""))
        print(f"  {i}. [{role}] -> {chars} chars of output")

    print("\n" + "-" * 60)
    print("DELIVERABLES")
    print("-" * 60)
    for role, output in deliverables.items():
        print(f"\n=== [{role}] ===")
        # Print first 500 chars as preview
        print(output[:500])
        if len(output) > 500:
            print(f"  ... [{len(output) - 500} more chars]")
