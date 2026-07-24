"""
Unit and Integration Tests for CriticAI Evaluation Suite
"""

import pytest
from evals.eval_suite import (
    evaluate_plan_completeness,
    evaluate_critic_agreement,
    evaluate_retry_rate,
    calculate_cost_usd,
    run_eval_suite
)

def test_evaluate_plan_completeness_valid():
    plan = [
        {"agent_role": "Backend Security Engineer", "task_description": "Build FastAPI endpoints with OAuth2 JWT auth."},
        {"agent_role": "B2B Copywriter", "task_description": "Write persuasive landing page copy for BrewBot subscription."}
    ]
    score = evaluate_plan_completeness(plan, expected_domains=["security", "copywriter"])
    assert score >= 0.85

def test_evaluate_plan_completeness_incomplete():
    plan = []
    score = evaluate_plan_completeness(plan)
    assert score == 0.0

def test_evaluate_critic_agreement():
    reviews = [
        {"approved": True},
        {"approved": False},
        {"approved": True},
        {"approved": True}
    ]
    score = evaluate_critic_agreement(reviews)
    assert score == 0.75

def test_evaluate_retry_rate():
    history = [
        {"agent_role": "Dev", "revisions": 1, "api_retries": 0},
        {"agent_role": "Writer", "revisions": 0, "api_retries": 0},
        {"agent_role": "QA", "revisions": 0, "api_retries": 1}
    ]
    rate = evaluate_retry_rate(history)
    assert round(rate, 2) == 0.67

def test_calculate_cost_usd():
    tokens = {"prompt": 1_000_000, "completion": 1_000_000}
    cost = calculate_cost_usd(tokens, "google/gemini-2.5-flash")
    assert cost == pytest.approx(0.375, rel=1e-3)

def test_run_eval_suite_full():
    data = {
        "execution_plan": [
            {"agent_role": "Security Lead", "task_description": "Audit authentication endpoints and secret isolation."},
            {"agent_role": "Frontend Dev", "task_description": "Implement React Tailwind dashboard canvas."}
        ],
        "critic_reviews": [{"approved": True}, {"approved": True}],
        "agent_history": [{"revisions": 0}, {"revisions": 0}],
        "agent_durations": {"orchestrator": 1.5, "Security Lead": 4.2, "Frontend Dev": 3.8},
        "total_tokens": {"prompt": 2500, "completion": 1200},
        "total_duration_sec": 9.5
    }
    res = run_eval_suite(data)
    assert res["plan_completeness"] >= 0.8
    assert res["critic_agreement"] == 1.0
    assert res["retry_rate"] == 0.0
    assert res["latency"]["e2e_latency_sec"] == 9.5
    assert "Evaluation Summary" in res["summary"]
