import pytest
from swarm import (
    orchestrator_node,
    worker_node,
    critic_node,
    route_critic
)

def test_orchestrator_node(mock_get_llm_client):
    state = {
        "task_prompt": "Build a coffee recommendation engine",
        "guidelines_path": "brand_guidelines.txt",
        "deliverables": {}
    }
    result = orchestrator_node(state)
    assert "execution_plan" in result
    assert len(result["execution_plan"]) > 0
    assert result["execution_plan"][0]["agent_role"] == "Copywriter"
    assert result["agent_statuses"]["Copywriter"] == "working"

def test_worker_node_simple(mock_get_llm_client):
    mock_get_llm_client.content_to_return = "Here is the slogan: Brew the future!"
    state = {
        "agent_role": "Copywriter",
        "task_description": "Write a slogan",
        "task_prompt": "Launch BrewBot",
        "guidelines_path": "brand_guidelines.txt",
        "previous_output": "",
        "critic_feedback": "",
        "internal_revision_count": 0,
        "approved_by_critic": False
    }
    result = worker_node(state)
    assert result["previous_output"] == "Here is the slogan: Brew the future!"
    assert result["deliverables"]["Copywriter"] == "Here is the slogan: Brew the future!"
    assert result["agent_statuses"]["Copywriter"] == "completed"

def test_critic_node_approved(mock_get_llm_client):
    mock_get_llm_client.content_to_return = "APPROVED"
    state = {
        "agent_role": "Copywriter",
        "task_description": "Write a slogan",
        "task_prompt": "Launch BrewBot",
        "guidelines_path": "brand_guidelines.txt",
        "previous_output": "Here is the slogan: Brew the future!",
        "critic_feedback": "",
        "internal_revision_count": 0,
        "approved_by_critic": False
    }
    result = critic_node(state)
    assert result["approved_by_critic"] is True
    assert result["agent_statuses"]["Copywriter"] == "completed"
    assert result["deliverables"]["Copywriter"] == "Here is the slogan: Brew the future!"

def test_critic_node_revision_loop(mock_get_llm_client):
    mock_get_llm_client.content_to_return = "REVISE: Slogan must be shorter and punchier."
    state = {
        "agent_role": "Copywriter",
        "task_description": "Write a slogan",
        "task_prompt": "Launch BrewBot",
        "guidelines_path": "brand_guidelines.txt",
        "previous_output": "Here is the slogan: Brew the future!",
        "critic_feedback": "",
        "internal_revision_count": 0,
        "approved_by_critic": False
    }
    result = critic_node(state)
    assert result["approved_by_critic"] is False
    assert result["critic_feedback"] == "Slogan must be shorter and punchier."
    assert result["internal_revision_count"] == 1
    assert "Reviewer Feedback" in result["deliverables"]["Copywriter"]

def test_route_critic():
    from langgraph.graph import END
    # Loop back to worker since not approved and max revision not reached
    state1 = {
        "approved_by_critic": False,
        "internal_revision_count": 1
    }
    assert route_critic(state1) == "worker_node"
    
    # Approved: subgraph ends (returns to parent graph which routes to hitl)
    state2 = {
        "approved_by_critic": True,
        "internal_revision_count": 1
    }
    assert route_critic(state2) == END
    
    # Max count reached: subgraph also ends
    state3 = {
        "approved_by_critic": False,
        "internal_revision_count": 2
    }
    assert route_critic(state3) == END

def test_clean_previous_output():
    from swarm import clean_previous_output
    text_with_fb = "Slogan: Brew the future!\n\n*Reviewer Feedback (Internal Revision 1):*\nSlogan must be shorter."
    assert clean_previous_output(text_with_fb) == "Slogan: Brew the future!"
    assert clean_previous_output("Slogan: Brew the future!") == "Slogan: Brew the future!"
    assert clean_previous_output("") == ""

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
    assert sends[0].arg["task_prompt"] == "Task brief"

