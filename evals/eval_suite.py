"""
CriticAI Evaluation Suite

Evaluates performance and quality metrics across swarm execution runs:
1. Plan Completeness Score
2. Critic Agreement Rate
3. Retry Rate (Worker revisions & API retries)
4. Node & End-to-End Latency Breakdown
5. Token Usage & USD Cost Per Run
"""

import time
from typing import Dict, List, Any, TypedDict

# Pricing models (USD per 1,000,000 tokens)
MODEL_PRICING = {
    "google/gemini-2.5-flash:free": {"prompt": 0.0, "completion": 0.0},
    "google/gemini-2.5-flash": {"prompt": 0.075, "completion": 0.30},
    "openai/gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "groq/llama-3.3-70b": {"prompt": 0.59, "completion": 0.79},
}

class EvalResult(TypedDict):
    plan_completeness: float
    critic_agreement: float
    retry_rate: float
    latency: Dict[str, float]
    cost_usd: float
    token_usage: Dict[str, int]
    summary: str

def evaluate_plan_completeness(plan: List[Dict[str, Any]], expected_domains: List[str] = None) -> float:
    """
    Evaluates plan completeness [0.0 - 1.0].
    Checks if at least 2 distinct, valid roles with non-empty descriptions were generated.
    """
    if not plan:
        return 0.0
    
    roles = {task.get("agent_role") for task in plan if task.get("agent_role")}
    valid_tasks = [t for t in plan if t.get("task_description") and len(t.get("task_description", "")) >= 10]
    
    # Baseline requirements: >=2 distinct roles and valid task descriptions
    role_score = min(len(roles) / 2.0, 1.0)
    task_score = min(len(valid_tasks) / len(plan), 1.0)
    
    if expected_domains:
        matched = 0
        plan_text = " ".join([f"{t.get('agent_role', '')} {t.get('task_description', '')}" for t in plan]).lower()
        for domain in expected_domains:
            if domain.lower() in plan_text:
                matched += 1
        domain_score = matched / len(expected_domains)
        return round((role_score * 0.4) + (task_score * 0.3) + (domain_score * 0.3), 2)
    
    return round((role_score * 0.5) + (task_score * 0.5), 2)

def evaluate_critic_agreement(critic_reviews: List[Dict[str, Any]]) -> float:
    """
    Calculates ratio of approved reviews to total reviews [0.0 - 1.0].
    """
    if not critic_reviews:
        return 1.0
    approved_count = sum(1 for r in critic_reviews if r.get("approved", False))
    return round(approved_count / len(critic_reviews), 2)

def evaluate_retry_rate(agent_history: List[Dict[str, Any]]) -> float:
    """
    Calculates fraction of worker tasks that required >=1 internal revision or retry [0.0 - 1.0].
    """
    if not agent_history:
        return 0.0
    retried = sum(1 for a in agent_history if a.get("revisions", 0) > 0 or a.get("api_retries", 0) > 0)
    return round(retried / len(agent_history), 2)

def calculate_cost_usd(tokens: Dict[str, int], model_name: str = "google/gemini-2.5-flash") -> float:
    """
    Calculates total USD cost based on prompt and completion token counts.
    """
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["google/gemini-2.5-flash"])
    p_tokens = tokens.get("prompt", 0)
    c_tokens = tokens.get("completion", 0)
    
    cost_p = (p_tokens / 1_000_000) * pricing["prompt"]
    cost_c = (c_tokens / 1_000_000) * pricing["completion"]
    return round(cost_p + cost_c, 6)

def run_eval_suite(run_data: Dict[str, Any], model_name: str = "google/gemini-2.5-flash") -> EvalResult:
    """
    Runs full evaluation benchmark on a completed swarm execution run dictionary.
    """
    plan = run_data.get("execution_plan", [])
    expected_domains = run_data.get("expected_domains")
    critic_reviews = run_data.get("critic_reviews", [])
    agent_history = run_data.get("agent_history", [])
    durations = run_data.get("agent_durations", {})
    tokens = run_data.get("total_tokens", {"prompt": 0, "completion": 0})
    
    comp_score = evaluate_plan_completeness(plan, expected_domains)
    agree_score = evaluate_critic_agreement(critic_reviews)
    retry = evaluate_retry_rate(agent_history)
    cost = calculate_cost_usd(tokens, model_name)
    
    total_dur = sum(durations.values()) if isinstance(durations, dict) else 0.0
    latency_breakdown = {
        "orchestrator_sec": round(durations.get("orchestrator", 2.5), 2),
        "workers_total_sec": round(total_dur, 2),
        "e2e_latency_sec": round(run_data.get("total_duration_sec", total_dur + 3.0), 2)
    }
    
    total_tokens_count = tokens.get("prompt", 0) + tokens.get("completion", 0)
    summary = (
        f"Evaluation Summary ({model_name}):\n"
        f"  • Plan Completeness: {comp_score * 100:.1f}%\n"
        f"  • Critic Agreement Rate: {agree_score * 100:.1f}%\n"
        f"  • Task Retry Rate: {retry * 100:.1f}%\n"
        f"  • End-to-End Latency: {latency_breakdown['e2e_latency_sec']}s\n"
        f"  • Total Tokens: {total_tokens_count} (Cost: ${cost:.6f} USD)"
    )
    
    return {
        "plan_completeness": comp_score,
        "critic_agreement": agree_score,
        "retry_rate": retry,
        "latency": latency_breakdown,
        "cost_usd": cost,
        "token_usage": tokens,
        "summary": summary
    }

if __name__ == "__main__":
    # Example benchmark run
    mock_run = {
        "execution_plan": [
            {"agent_role": "Backend Security Engineer", "task_description": "Design authentication endpoints and password hashing using Argon2id."},
            {"agent_role": "B2B Copywriter", "task_description": "Draft high-converting SaaS landing page headlines and features."}
        ],
        "expected_domains": ["security", "copywriter"],
        "critic_reviews": [
            {"agent_role": "Backend Security Engineer", "approved": False, "revision": 1},
            {"agent_role": "Backend Security Engineer", "approved": True, "revision": 2},
            {"agent_role": "B2B Copywriter", "approved": True, "revision": 1}
        ],
        "agent_history": [
            {"agent_role": "Backend Security Engineer", "revisions": 1, "api_retries": 0},
            {"agent_role": "B2B Copywriter", "revisions": 0, "api_retries": 0}
        ],
        "agent_durations": {"orchestrator": 2.1, "Backend Security Engineer": 11.4, "B2B Copywriter": 8.7},
        "total_tokens": {"prompt": 4850, "completion": 2100},
        "total_duration_sec": 22.2
    }
    
    res = run_eval_suite(mock_run, "google/gemini-2.5-flash")
    print(res["summary"])
