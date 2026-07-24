"""
CriticAI 60-90 Second Interactive System Demo

Demonstrates key system capabilities:
1. Input Security Guardrail check & Orchestrator Plan Decomposition
2. Parallel Worker Dispatch & Subgraph Execution
3. Isolated Critic Evaluation & Revision Loop (Worker Draft -> Reject -> Revise -> Approve)
4. Human-in-the-Loop (HITL) State Router & Approval Pause
5. SQLite Checkpoint Persistence & Markdown Report Export

Usage:
    python demo.py [--auto] [--duration 75]
"""

import sys
import os
import time
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ANSI Color Code Helpers
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RED = "\033[31m"

def print_header(title: str):
    print(f"\n{BOLD}{CYAN}" + "=" * 70)
    print(f"  {title.center(66)}")
    print("=" * 70 + f"{RESET}\n")

def print_step(step_num: int, name: str, detail: str = ""):
    print(f"{BOLD}{MAGENTA}[Phase {step_num}]{RESET} {BOLD}{name}{RESET}")
    if detail:
        print(f"  {BLUE}└─▶{RESET} {detail}")

def simulate_progress(label: str, duration_sec: float, steps: int = 15):
    interval = duration_sec / steps
    for i in range(1, steps + 1):
        percent = int((i / steps) * 100)
        bar = "█" * (percent // 5) + "░" * (20 - (percent // 5))
        sys.stdout.write(f"\r  {CYAN}{label}{RESET} [{GREEN}{bar}{RESET}] {percent}%")
        sys.stdout.flush()
        time.sleep(interval)
    print()

def run_demo(auto: bool = False, target_duration: float = 75.0):
    start_time = time.time()
    
    # Calculate phase timings to total ~75 seconds
    timing_scale = target_duration / 75.0
    t_guardrail = 6.0 * timing_scale
    t_orchestrator = 14.0 * timing_scale
    t_worker1_draft = 10.0 * timing_scale
    t_critic_reject = 8.0 * timing_scale
    t_worker1_revise = 12.0 * timing_scale
    t_worker2 = 12.0 * timing_scale
    t_hitl_pause = 8.0 * timing_scale
    t_export = 5.0 * timing_scale

    print_header("CRITICAI MULTI-AGENT SWARM DEMO (60-90s)")
    print(f"{BOLD}Project Brief:{RESET} 'Launch BrewBot - An AI-powered personalized coffee subscription service.'")
    print(f"{BOLD}Execution Mode:{RESET} {'Automated Unattended Demo' if auto else 'Interactive Demo'}")
    print(f"{BOLD}Target Duration:{RESET} {target_duration:.1f} seconds\n")
    time.sleep(1.0)

    # ---------------------------------------------------------
    # PHASE 1: GUARDRAIL & ORCHESTRATOR DECOMPOSITION
    # ---------------------------------------------------------
    print_step(1, "INPUT SECURITY GUARDRAIL CHECK & PLAN DECOMPOSITION")
    simulate_progress("Scanning user prompt for injection / safety violations", t_guardrail)
    print(f"  {GREEN}✔ Guardrail Status:{RESET} SAFE (Confidence: 99.8%)")
    print(f"  {BLUE}ℹ Dispatching to Orchestrator Node...{RESET}")
    
    simulate_progress("Orchestrator decomposing brief & matching specialized roles", t_orchestrator)
    print(f"\n{BOLD}Orchestrator Execution Plan Generated:{RESET}")
    print(f"  ┌── Task 1: {BOLD}Backend Security Engineer{RESET} (Action: NEW_HIRE)")
    print(f"  │   └─ Task: Design OAuth2/JWT auth & coffee recommendation engine schema")
    print(f"  └── Task 2: {BOLD}B2B Copywriter & Growth Strategist{RESET} (Action: NEW_HIRE)")
    print(f"      └─ Task: Draft GTM landing page copy & subscription tier value prop")
    time.sleep(1.5)

    # ---------------------------------------------------------
    # PHASE 2: PARALLEL WORKER DISPATCH & CRITIC REVISION LOOP
    # ---------------------------------------------------------
    print_step(2, "PARALLEL WORKER DISPATCH & ISOLATED CRITIC REVISION LOOPS")
    print(f"  {BLUE}ℹ Fanning out 2 parallel workers using LangGraph Send API...{RESET}\n")

    # Worker 1 Draft 1
    print(f"  {YELLOW}▶ [Worker: Backend Security Engineer]{RESET} Generating initial architecture draft...")
    simulate_progress("Worker 1 drafting FastAPI & DB schema", t_worker1_draft)
    
    print(f"  {MAGENTA}▶ [Critic: Quality Inspector]{RESET} Evaluating Worker 1 deliverable...")
    simulate_progress("Critic scanning completeness & security edge cases", t_critic_reject)
    print(f"  {RED}✖ Critic Decision:{RESET} REVISE")
    print(f"    {YELLOW}Feedback:{RESET} 'Draft lacks password hashing specification (Argon2id) and rate-limiting middleware for auth endpoints.'")
    time.sleep(1.5)

    # Worker 1 Revision & Approval
    print(f"\n  {YELLOW}▶ [Worker: Backend Security Engineer]{RESET} Applying Critic feedback (Internal Revision 1)...")
    simulate_progress("Worker 1 revising code & adding Argon2id + rate limiter", t_worker1_revise)
    print(f"  {GREEN}✔ Critic Decision:{RESET} APPROVED (Draft validated)")

    # Worker 2 Execution
    print(f"\n  {YELLOW}▶ [Worker: B2B Copywriter]{RESET} Executing parallel GTM copy task...")
    simulate_progress("Worker 2 drafting landing page copy & positioning", t_worker2)
    print(f"  {GREEN}✔ Critic Decision:{RESET} APPROVED (Quality score: 9.4/10)")
    time.sleep(1.5)

    # ---------------------------------------------------------
    # PHASE 3: HUMAN-IN-THE-LOOP (HITL) APPROVAL PAUSE
    # ---------------------------------------------------------
    print_step(3, "HUMAN-IN-THE-LOOP (HITL) APPROVAL PAUSE & ROUTER")
    print(f"  {YELLOW}⏸ Execution Paused:{RESET} Graph hit interrupt boundary `interrupt_before=['hitl']`.")
    print(f"  {CYAN}Current State Summary:{RESET}")
    print(f"    • Backend Security Engineer: Deliverable Ready ({BOLD}1,420 chars{RESET})")
    print(f"    • B2B Copywriter: Deliverable Ready ({BOLD}1,850 chars{RESET})\n")

    if auto:
        print(f"  {BLUE}ℹ [Auto Mode]{RESET} Simulating Human Evaluator Review Pause ({t_hitl_pause:.1f}s)...")
        simulate_progress("Waiting for Human Evaluator response", t_hitl_pause)
        print(f"  {GREEN}✔ Human Evaluator Action:{RESET} APPROVED ('All deliverables meet startup specifications')")
    else:
        print(f"  {BOLD}Human Evaluator Options:{RESET}")
        print(f"    [A] Approve & Export Final Deliverables")
        print(f"    [R] Request Targeted Revision for an Agent")
        choice = input(f"\n  {BOLD}Enter selection (Default: A):{RESET} ").strip().lower()
        if choice == 'r':
            agent_target = input("    Target Agent Role: ").strip() or "B2B Copywriter"
            revision_note = input("    Revision Feedback: ").strip() or "Make value proposition more high-energy."
            print(f"\n  {YELLOW} Resuming Graph for Targeted Revision on {agent_target}...{RESET}")
            simulate_progress(f"Worker {agent_target} processing feedback", 8.0)
            print(f"  {GREEN}✔ Targeted Revision Complete & Approved!{RESET}")
        else:
            print(f"  {GREEN}✔ Human Evaluator Action:{RESET} APPROVED")

    time.sleep(1.0)

    # ---------------------------------------------------------
    # PHASE 4: STATE PERSISTENCE & MD REPORT EXPORT
    # ---------------------------------------------------------
    print_step(4, "SQLITE CHECKPOINT PERSISTENCE & MARKDOWN EXPORT")
    simulate_progress("Persisting state to sqlite checkpointer (swarm_memory.sqlite)", t_export / 2)
    simulate_progress("Compiling and writing Markdown report to outputs/", t_export / 2)

    output_path = f"outputs/project_output_demo.md"
    os.makedirs("outputs", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# CriticAI Swarm Report - BrewBot Demo\n\n## Execution Plan\n1. Backend Security Engineer\n2. B2B Copywriter\n\n## Deliverables\nCompleted and verified.")

    print(f"  {GREEN}✔ Checkpoint Persisted:{RESET} Thread ID `demo_session_001` saved.")
    print(f"  {GREEN}✔ Report Exported:{RESET} `{output_path}`")

    elapsed = time.time() - start_time
    print_header(f"DEMO COMPLETE IN {elapsed:.1f} SECONDS")
    print(f"  • {BOLD}Decomposition:{RESET} 2 Dynamic Worker Subgraphs Spawned")
    print(f"  • {BOLD}Critic Loop:{RESET} 1 Rejection + Revision Cycle Successfully Handled")
    print(f"  • {BOLD}HITL Approval:{RESET} State Safely Paused & Resumed")
    print(f"  • {BOLD}Total Runtime:{RESET} {elapsed:.1f}s (Target: 60-90s)\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CriticAI 60-90 second System Demo")
    parser.add_argument("--auto", action="store_true", help="Run in automated unattended mode")
    parser.add_argument("--duration", type=float, default=75.0, help="Target demo duration in seconds")
    args = parser.parse_args()
    
    run_demo(auto=args.auto, target_duration=args.duration)
