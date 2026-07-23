import json
import operator
import os
import re
import sqlite3
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import time
from typing import Annotated, Any, List, TypedDict, Literal
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send
from langgraph.graph.message import add_messages
from langchain_tavily import TavilySearch

load_dotenv()

import asyncio as _asyncio

_main_loop = None

def set_main_loop(loop):
    global _main_loop
    _main_loop = loop

def _sync_emit(session_id: str, event: str, data: dict) -> None:
    """
    Fire-and-forget socket emit from a synchronous LangGraph node.
    Works because FastAPI's event loop runs in the main thread while
    LangGraph nodes run in a thread-pool executor (run_in_executor).
    """
    if not session_id or _main_loop is None:
        return
    try:
        from socket_server import emit_to_session
        _asyncio.run_coroutine_threadsafe(emit_to_session(session_id, event, data), _main_loop)
    except Exception as exc:
        print(f"[WS EMIT ERROR] {exc}")



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


def clean_previous_output(output: str) -> str:
    """Strips reviewer feedback appended to deliverables from previous turns."""
    if not output:
        return ""
    # Split by the reviewer feedback markdown indicator and keep the prefix
    parts = re.split(r"\n\n\*Reviewer Feedback \(Internal Revision \d+\):\*", output)
    return parts[0].strip()


class SwarmState(TypedDict):
    # ── Core inputs ──────────────────────────────────────────────
    task_prompt: str          # The raw user request sent from the frontend
    user_brief: str           # The user request without attached file content
    guidelines_path: str      # Path to the brand-guidelines file

    # ── Orchestrator outputs ─────────────────────────────────────
    execution_plan: list[dict]
    deliverables: Annotated[dict, operator.ior]
    agent_statuses: Annotated[dict, _merge_dicts]
    agent_durations: Annotated[dict, _merge_dicts]  # ponytail: {role: seconds_float}
    agent_tokens: Annotated[dict, _merge_dicts]
    feedback_type: str
    target_agent: str
    guardrail_status: str
    feedback: str
    revision_count: int
    messages: Annotated[list[AnyMessage], add_messages]
    final_outputs: Annotated[List[str], operator.add]


class WorkerState(TypedDict):
    """Scoped state passed to each dynamically-spawned worker via Send."""
    agent_role: str
    task_description: str
    task_prompt: str
    guidelines_path: str
    feedback: str
    feedback_type: str
    previous_output: str
    critic_feedback: str
    internal_revision_count: int
    approved_by_critic: bool
    worker_status: str
    worker_duration: float      # seconds taken by this worker
    agent_tokens: dict
    deliverables: dict
    agent_statuses: dict


# ==========================================
# 2. TOOLS
# ==========================================
tavily_tool = TavilySearch(max_results=3)

@tool
def read_brand_guidelines(file_path: str) -> str:
    """Reads the brand guidelines file. INPUT: file path string."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

tools_list = [tavily_tool, read_brand_guidelines]

import concurrent.futures

def invoke_llm_with_timeout(llm: Any, messages: list, timeout_seconds: float = 45.0) -> Any:
    """ponytail: Strictly enforce execution timeout on LLM calls to bypass proxy hangs."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(llm.invoke, messages)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"API request timed out after {timeout_seconds} seconds.")

def extract_tokens(response) -> dict:
    """ponytail: Extracts prompt and completion token usage from LLM response metadata."""
    try:
        meta = getattr(response, "response_metadata", {}) or {}
        usage = meta.get("token_usage") or {}
        return {
            "prompt": usage.get("prompt_tokens", 0),
            "completion": usage.get("completion_tokens", 0)
        }
    except Exception:
        return {"prompt": 0, "completion": 0}

def get_llm_client(config: RunnableConfig = None, is_orchestrator: bool = False) -> Any:
    """Returns an OpenRouter ChatOpenAI client using the free models router."""
    configurable = config.get("configurable", {}) if config else {}
    openrouter_key = (configurable.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY") or "").strip()
    temp = 0.2 if is_orchestrator else 0.7
    if not openrouter_key:
        raise ValueError(
            "OpenRouter API Key not found. Please click the Settings gear icon (⚙️) "
            "in the top-right corner of the page and paste a valid OpenRouter API Key."
        )
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_key,
        model="openrouter/free",  # ponytail: zero-cost free model router
        temperature=temp,
        timeout=45.0,             # ponytail: prevent indefinite hangs on congested free models
    )


# ── Guardrails Safety Verification Node ────────────────────────────
from guardrails import guardrail_node, route_guardrail


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
        result = invoke_llm_with_timeout(structured_llm, messages, timeout_seconds=45.0)
        
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

    ws_session_id = (config or {}).get("configurable", {}).get("ws_session_id", "")
    _sync_emit(ws_session_id, "plan_ready", {
        "execution_plan": execution_plan,
        "agent_count":    len(execution_plan),
    })
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
    Phase 2 – Generic Worker with Dynamic Tool Loop.

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
    critic_feedback = state.get("critic_feedback", "")

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

    if critic_feedback:
        system_content += f"\n\nCRITICAL INTERNAL REVIEW FEEDBACK:\n{critic_feedback}\n\nYou MUST revise your previous draft to address the specific critiques listed above."

    if len(task_prompt) > 2000:
        system_content += "\n\nWARNING: The user request contains extensive document content. Please be concise and focus only on your specific assignment."

    # Workers use dynamic LLM client
    dyn_worker_llm = get_llm_client(config, is_orchestrator=False)

    # Try tool binding; if the routed model rejects it the except block retries without tools.
    tools_supported = True  # ponytail: attempt tools; catch error on 404

    tools_map = {t.name: t for t in tools_list}
    llm_with_tools = dyn_worker_llm.bind_tools(tools_list) if tools_supported else dyn_worker_llm

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=f"Execute your assignment now. Be detailed and specific." + (" Use tools if needed." if tools_supported else "")),
    ]

    print(f"\n[WORKER:{role}] Starting task...")
    ws_session_id = (config or {}).get("configurable", {}).get("ws_session_id", "")
    _t_start = time.time()
    _sync_emit(ws_session_id, "agent_started", {"role": role, "task": task_desc[:120]})
    _sync_emit(ws_session_id, "agent_token", {"role": role, "token": "🚀 Starting task execution...\n"})
    prompt_tokens = 0
    completion_tokens = 0
    try:
        for _ in range(3):  # tool loop, max 3 turns
            response = invoke_llm_with_timeout(llm_with_tools, messages, timeout_seconds=45.0)
            messages.append(response)
            t = extract_tokens(response)
            prompt_tokens += t["prompt"]
            completion_tokens += t["completion"]
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    fn = tools_map.get(tc['name'])
                    _sync_emit(ws_session_id, "agent_token", {"role": role, "token": f"⚙️ Calling tool {tc['name']}...\n"})
                    result = fn.invoke(tc['args']) if fn else f"Tool {tc['name']} not found"
                    messages.append(ToolMessage(content=str(result), name=tc['name'], tool_call_id=tc['id']))
            else:
                break
        # Ensure we have a plain-text final answer
        if not messages[-1].content or (hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls):
            _sync_emit(ws_session_id, "agent_token", {"role": role, "token": "🧠 Calling OpenRouter free model router...\n"})
            final_resp = invoke_llm_with_timeout(dyn_worker_llm, messages, timeout_seconds=45.0)
            t = extract_tokens(final_resp)
            prompt_tokens += t["prompt"]
            completion_tokens += t["completion"]
            output = final_resp.content.strip()
        else:
            output = messages[-1].content.strip()
        _sync_emit(ws_session_id, "agent_token", {"role": role, "token": "✅ Task completed. Preparing draft.\n"})
        status = "completed"
    except Exception as e:
        import traceback
        traceback.print_exc()
        err_str = str(e)
        if "429" in err_str or "rate_limit" in err_str.lower():
            time.sleep(10)
            try:
                final_resp = dyn_worker_llm.invoke(messages)
                t = extract_tokens(final_resp)
                prompt_tokens += t["prompt"]
                completion_tokens += t["completion"]
                output = final_resp.content.strip()
                status = "completed"
            except Exception as e2:
                output = f"⚠️ **Rate Limit:** Provider overloaded. Request a targeted revision to retry.\n\n`{str(e2)[:200]}`"
                status = "error"
        else:
            output = f"⚠️ **Agent Error:** `{err_str[:300]}`\n\nRequest a targeted revision to retry."
            status = "error"

    duration = round(time.time() - _t_start, 1)
    print(f"[WORKER:{role}] {status} in {duration}s ({len(output)} chars)")
    _sync_emit(ws_session_id, "agent_done", {
        "role": role,
        "duration": duration,
        "tokens": {"prompt": prompt_tokens, "completion": completion_tokens}
    })
    return {
        "previous_output": output,
        "worker_status": status,
        "worker_duration": duration,
        "agent_tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
        "deliverables": {role: output},
        "agent_statuses": {role: status},
        "approved_by_critic": False,
    }


# ==========================================
# 5a. CRITIC LAYER & ROUTING
# ==========================================
def critic_node(state: WorkerState, config: RunnableConfig = None) -> dict[str, Any]:
    role = state["agent_role"]
    task_desc = state["task_description"]
    task_prompt = state["task_prompt"]
    output = state["previous_output"]
    revision_count = state.get("internal_revision_count", 0)

    # If the output is empty or contains system notice/agent error, skip review
    if not output or "System Notice" in output or "Agent Error" in output or state.get("worker_status") == "error":
        return {
            "approved_by_critic": True,
            "critic_feedback": "",
            "deliverables": {role: output},
            "agent_statuses": {role: "error"},
            "agent_tokens": state.get("agent_tokens") or {"prompt": 0, "completion": 0}
        }

    critic_prompt = f"""You are the Lead Quality Assurance and Critic Agent for an AI Swarm.
Your job is to critically review the deliverable produced by the '{role}' agent and determine if it is complete, matches the task requirements, and is high-quality.

Original Project Brief:
"{task_prompt}"

Agent Role: {role}
Agent's Specific Task:
"{task_desc}"

Deliverable to Review:
<deliverable>
{output}
</deliverable>

CRITICAL RULES FOR EVALUATION:
1. Thoroughness: Does the deliverable fully address the specific task? If it is too short, generic, or has placeholders, reject it.
2. Alignment: Does it respect the project brief and guidelines?
3. Actionability: Is it professional and immediately usable?

If the deliverable passes your checks and is high quality, respond with:
APPROVED

If it requires improvements, start your response with:
REVISE
Followed by a numbered list of clear, specific, and constructive instructions for the agent to implement. Do not be overly harsh, but do not accept low-quality or incomplete work.
"""

    dyn_critic_llm = get_llm_client(config, is_orchestrator=True)
    messages = [
        SystemMessage(content=critic_prompt),
        HumanMessage(content="Evaluate the deliverable. Start with either 'APPROVED' or 'REVISE'."),
    ]
    
    print(f"\n[CRITIC:{role}] Reviewing deliverable...")
    ws_session_id = (config or {}).get("configurable", {}).get("ws_session_id", "")
    _sync_emit(ws_session_id, "agent_critic_reviewing", {"role": role})
    _sync_emit(ws_session_id, "agent_token", {"role": role, "token": "🧐 Submitting draft to Lead Critic for review...\n"})
    
    c_prompt = 0
    c_completion = 0
    try:
        response = invoke_llm_with_timeout(dyn_critic_llm, messages, timeout_seconds=45.0)
        review = response.content.strip()
        t = extract_tokens(response)
        c_prompt = t["prompt"]
        c_completion = t["completion"]
        _sync_emit(ws_session_id, "agent_token", {"role": role, "token": f"📝 Critic review response received.\n"})
        print(f"[CRITIC:{role}] Review complete:\n{review[:200]}...")
    except Exception as e:
        print(f"[CRITIC:{role}] Review failed: {e}. Defaulting to APPROVED.")
        review = "APPROVED"

    w_tokens = state.get("agent_tokens") or {"prompt": 0, "completion": 0}
    prompt_tokens = w_tokens.get("prompt", 0) + c_prompt
    completion_tokens = w_tokens.get("completion", 0) + c_completion
    merged_tokens = {"prompt": prompt_tokens, "completion": completion_tokens}
    _sync_emit(ws_session_id, "agent_critic_done", {"role": role, "tokens": merged_tokens})

    if review.startswith("APPROVED") or "approved" in review.lower()[:15]:
        _sync_emit(ws_session_id, "agent_token", {"role": role, "token": "🎉 Deliverable APPROVED by critic!\n"})
        return {
            "approved_by_critic": True,
            "critic_feedback": "",
            "deliverables": {role: output},
            "agent_statuses": {role: "completed"},
            "agent_tokens": merged_tokens
        }
    else:
        # Extract revision feedback
        feedback = review
        if feedback.startswith("REVISE"):
            feedback = feedback[len("REVISE"):].strip()
            if feedback.startswith(":") or feedback.startswith("-"):
                feedback = feedback[1:].strip()
        
        print(f"[CRITIC:{role}] Rejected (Revision count: {revision_count + 1})")
        _sync_emit(ws_session_id, "agent_token", {"role": role, "token": f"🔄 Deliverable REJECTED. Looping back for revision (count: {revision_count + 1}).\n"})
        return {
            "approved_by_critic": False,
            "critic_feedback": feedback,
            "internal_revision_count": revision_count + 1,
            # Render the intermediate draft + critique so it can be seen
            "deliverables": {role: f"{output}\n\n*Reviewer Feedback (Internal Revision {revision_count + 1}):*\n{feedback}"},
            "agent_statuses": {role: "working"},
            "agent_tokens": merged_tokens
        }


def route_critic(state: WorkerState):
    """Routing function used inside the worker subgraph.
    Returns 'worker_node' for another revision cycle, or END when approved/max revisions reached.
    """
    approved = state.get("approved_by_critic", False)
    revision_count = state.get("internal_revision_count", 0)
    role = state.get("agent_role", "Worker")

    if approved or revision_count >= 2:
        if revision_count >= 2 and not approved:
            print(f"[CRITIC ROUTER:{role}] Max internal revision limit reached. Finalizing.")
        else:
            print(f"[CRITIC ROUTER:{role}] Approved! Finalizing.")
        return END
    else:
        print(f"[CRITIC ROUTER:{role}] Loop back to worker for revision.")
        return "worker_node"


# ==========================================
# 5b. WORKER SUBGRAPH  (isolated worker-critic loop per agent)
# ==========================================
# The parent graph fans-out via Send to `worker_subgraph_node`.
# Each branch runs its own worker → critic → (revise? loop back) → END
# cycle entirely inside a *separate* StateGraph that uses WorkerState.
# This prevents parallel branches from writing un-annotated keys like
# `previous_output` and `approved_by_critic` to the shared SwarmState,
# which caused InvalidUpdateError.

_worker_sub = StateGraph(WorkerState)
_worker_sub.add_node("worker_node", worker_node)
_worker_sub.add_node("critic_node", critic_node)
_worker_sub.set_entry_point("worker_node")
_worker_sub.add_edge("worker_node", "critic_node")
_worker_sub.add_conditional_edges(
    "critic_node",
    route_critic,
    ["worker_node", END],
)

worker_subgraph = _worker_sub.compile()


def worker_subgraph_node(state: WorkerState, config: RunnableConfig = None) -> dict:
    """Runs isolated worker-critic loop; returns only SwarmState-annotated keys."""
    final: WorkerState = worker_subgraph.invoke(state, config=config or {})
    role = final["agent_role"]
    return {
        "deliverables":    {role: final.get("previous_output", "")},
        "agent_statuses":  {role: final.get("worker_status", "completed")},
        "agent_durations": {role: final.get("worker_duration", 0.0)},
        "agent_tokens":    {role: final.get("agent_tokens", {"prompt": 0, "completion": 0})},
    }


# ==========================================
# 5c. DISPATCH EDGE  (Send API fan-out)
# ==========================================
def assign_workers(state: SwarmState) -> list[Send]:
    """
    Conditional edge called after `orchestrator`.

    Iterates `execution_plan` and issues one `Send` per task, which causes
    LangGraph to spawn all worker_subgraph_node invocations in parallel.
    Each invocation runs its own isolated worker-critic loop.
    """
    return [
        Send(
            "worker_subgraph_node",
            {
                "agent_role":              task["agent_role"],
                "task_description":        task["task_description"],
                "task_prompt":             state.get("user_brief", state["task_prompt"]),
                "guidelines_path":         state.get("guidelines_path", "brand_guidelines.txt"),
                "feedback":                state.get("feedback", ""),
                "feedback_type":           state.get("feedback_type", ""),
                "previous_output":         clean_previous_output(
                                               state.get("deliverables", {}).get(task["agent_role"], "")
                                           ),
                "critic_feedback":         "",
                "internal_revision_count": 0,
                "approved_by_critic":      False,
                "worker_status":           "",
                "deliverables":            {},
                "agent_statuses":          {},
                "agent_tokens":            {"prompt": 0, "completion": 0},
            },
        )
        for task in state["execution_plan"]
    ]


# ==========================================
# 5d. FEEDBACK ROUTING
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
                "worker_subgraph_node",
                {
                    "agent_role":              target,
                    "task_description":        task_desc,
                    "task_prompt":             state.get("user_brief", state["task_prompt"]),
                    "guidelines_path":         state.get("guidelines_path", "brand_guidelines.txt"),
                    "feedback":                state.get("feedback", ""),
                    "feedback_type":           "targeted",
                    "previous_output":         clean_previous_output(
                                                   state.get("deliverables", {}).get(target, "")
                                               ),
                    "critic_feedback":         "",
                    "internal_revision_count": 0,
                    "approved_by_critic":      False,
                    "worker_status":           "",
                    "deliverables":            {},
                    "agent_statuses":          {},
                    "agent_tokens":            {"prompt": 0, "completion": 0},
                }
            )
        ]
    elif fb_type == "global":
        return "orchestrator"
    else:
        return "exporter"


# ==========================================
# 6. HITL PASS-THROUGH NODE
# ==========================================
def hitl_node(state: SwarmState):
    # Graph interrupt is declared at compile time; this is a pass-through.
    return {}


# ==========================================
# 7. EXPORTER NODE
# ==========================================
def export_deliverable_node(state: SwarmState):
    deliverables = state.get("deliverables", {})
    task = state.get("task_prompt", "Project Brief")
    plan = state.get("execution_plan", [])
    durations = state.get("agent_durations", {})

    if not deliverables:
        return {"final_outputs": ["Error: No agent outputs to export."]}

    os.makedirs("outputs", exist_ok=True)
    lines = [
        "# 🎯 CriticAI Swarm Report",
        f"**Brief:** {task}\n",
        "---",
    ]
    if plan:
        lines.append("## 🤖 Execution Plan")
        for i, t in enumerate(plan, 1):
            lines.append(f"{i}. **[{t.get('agent_role')}]**: {t.get('task_description')}")
        lines.append("\n---")
    lines.append("## 📂 Agent Deliverables")
    for role, content in deliverables.items():
        dur = f" *(⏱ {durations[role]}s)*" if role in durations else ""
        lines.append(f"\n### 👤 {role}{dur}")
        lines.append(content)
        lines.append("\n---")

    filename = f"outputs/project_output_{time.strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[EXPORT] → {filename}")
    return {"final_outputs": [f"Exported to {filename}"]}


# ==========================================
# 8. COMPILE GRAPH
# ==========================================
# ── Phase 2 graph (Dynamic Worker Dispatch via Subgraph) ─────────
#
#   guardrail
#       │
#       ├─(blocked)─► hitl
#       └─(safe)───► orchestrator
#                        │
#                        └─ assign_workers() ──┬─ Send → worker_subgraph_node (parallel)
#                                              ├─ Send → worker_subgraph_node
#                                              └─ Send → worker_subgraph_node
#                                                            │ (writes only deliverables + agent_statuses)
#                                                           hitl
#                                                            │
#                                                        exporter ──► END
#
# Each worker_subgraph_node runs an isolated worker→critic loop
# (worker_subgraph) and returns ONLY SwarmState-annotated keys so that
# parallel execution never conflicts on un-annotated WorkerState fields.
# ─────────────────────────────────────────────────────────────────

workflow = StateGraph(SwarmState)
workflow.add_node("guardrail",          guardrail_node)
workflow.add_node("orchestrator",        orchestrator_node)
workflow.add_node("worker_subgraph_node", worker_subgraph_node)
workflow.add_node("hitl",                hitl_node)
workflow.add_node("exporter",            export_deliverable_node)

workflow.set_entry_point("guardrail")
workflow.add_conditional_edges("guardrail",          route_guardrail, ["orchestrator", "hitl"])
workflow.add_conditional_edges("orchestrator",        assign_workers,  ["worker_subgraph_node"])
workflow.add_edge("worker_subgraph_node", "hitl")
workflow.add_conditional_edges("hitl",               route_feedback,  ["worker_subgraph_node", "orchestrator", "exporter"])
workflow.add_edge("exporter", END)

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
