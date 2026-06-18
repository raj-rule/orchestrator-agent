"""
Phase 2 Smoke Test – Orchestrator + Parallel Workers via Send API
Run: .\\venv\\Scripts\\python.exe _test_orchestrator.py
"""
from dotenv import load_dotenv
load_dotenv()

from swarm import app

initial_state = {
    "task_prompt": (
        "Launch 'BrewBot' - an AI-powered coffee subscription startup. "
        "We need a go-to-market strategy, a social media content plan, "
        "and a technical architecture for the recommendation engine."
    ),
    "guidelines_path": "brand_guidelines.txt",
    "execution_plan": [],
    "deliverables": {},
    "slogan_draft": "",
    "image_prompt_draft": "",
    "internal_feedback": "",
    "revision_count": 0,
    "final_outputs": [],
}

config = {"configurable": {"thread_id": "phase2_test_001"}}

print("\n>> Invoking dynamic swarm (Phase 2)...\n")
result = app.invoke(initial_state, config=config)

plan         = result.get("execution_plan", [])
deliverables = result.get("deliverables", {})

print(f"\n{'='*60}")
print(f"SWARM COMPLETE  |  {len(plan)} tasks  |  {len(deliverables)} deliverables")
print(f"{'='*60}")

for i, task in enumerate(plan, 1):
    role  = task.get("agent_role", "?")
    chars = len(deliverables.get(role, ""))
    print(f"  {i}. [{role}] -> {chars} chars")

print(f"\n{'-'*60}")
print("DELIVERABLE PREVIEWS")
print(f"{'-'*60}")
for role, output in deliverables.items():
    preview = output[:400].replace("\n", "\n     ")
    print(f"\n[{role}]\n     {preview}")
    if len(output) > 400:
        print(f"     ... [{len(output) - 400} more chars]")
