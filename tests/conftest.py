import pytest
import sys
import os
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MockAIMessage:
    def __init__(self, content):
        self.content = content

class MockLLM:
    def __init__(self, content_to_return="APPROVED"):
        self.content_to_return = content_to_return
        self.call_count = 0

    def invoke(self, messages, *args, **kwargs):
        # If content_to_return is a list, cycle through it
        if isinstance(self.content_to_return, list):
            idx = min(self.call_count, len(self.content_to_return) - 1)
            content = self.content_to_return[idx]
        else:
            content = self.content_to_return
        
        self.call_count += 1
        return MockAIMessage(content=content)

    def bind_tools(self, tools, *args, **kwargs):
        return self

    def with_structured_output(self, schema, *args, **kwargs):
        class StructuredMock:
            def __init__(self, schema):
                self.schema = schema
            def invoke(self, messages, *args, **kwargs):
                # Return default structured object
                if self.schema.__name__ == "OrchestratorPlan":
                    from swarm import Assignment
                    return self.schema(assignments=[
                        Assignment(
                            reasoning="Need copywriter",
                            action_type="NEW_HIRE",
                            agent_role="Copywriter",
                            task_description="Write copy"
                        ),
                        Assignment(
                            reasoning="Need QA editor",
                            action_type="NEW_HIRE",
                            agent_role="QA Editor",
                            task_description="Review copy"
                        )
                    ])
                return self.schema()
        return StructuredMock(schema)

@pytest.fixture
def mock_get_llm_client(monkeypatch):
    """Fixture to mock the get_llm_client function in swarm."""
    import swarm
    mock_client = MockLLM()
    monkeypatch.setattr(swarm, "get_llm_client", lambda config=None, is_orchestrator=False: mock_client)
    return mock_client
