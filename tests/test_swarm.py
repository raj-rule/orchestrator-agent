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
    # Loop back to worker since not approved and max revision not reached
    state1 = {
        "approved_by_critic": False,
        "internal_revision_count": 1
    }
    assert route_critic(state1) == "worker_node"
    
    # Approved goes to hitl
    state2 = {
        "approved_by_critic": True,
        "internal_revision_count": 1
    }
    assert route_critic(state2) == "hitl"
    
    # Max count reached goes to hitl
    state3 = {
        "approved_by_critic": False,
        "internal_revision_count": 2
    }
    assert route_critic(state3) == "hitl"

def test_clean_previous_output():
    from swarm import clean_previous_output
    text_with_fb = "Slogan: Brew the future!\n\n*Reviewer Feedback (Internal Revision 1):*\nSlogan must be shorter."
    assert clean_previous_output(text_with_fb) == "Slogan: Brew the future!"
    assert clean_previous_output("Slogan: Brew the future!") == "Slogan: Brew the future!"
    assert clean_previous_output("") == ""

