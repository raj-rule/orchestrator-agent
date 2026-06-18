# Design Spec: Optimization, Observability, CI/CD, and API Documentation

This document outlines the architecture, components, and data flow for the requested improvements to the CriticAI repository:
1. **CI/CD Pipeline**: Automated test execution via GitHub Actions.
2. **Observability / Telemetry**: Dynamic LangSmith tracing integration configurable via the frontend dashboard.
3. **API Documentation**: Automated FastAPI OpenAPI schema, response models, and metadata improvements.
4. **Token Optimization**: Minimizing redundant token usage in worker revision loops and attached file propagation.

---

## 1. CI/CD Pipeline

We will configure a GitHub Actions workflow to run the pytest suite on every push and pull request to the `main` branch.

### Component Details
* **File Path**: `.github/workflows/test.yml`
* **Trigger Conditions**:
  ```yaml
  on:
    push:
      branches: [ main ]
    pull_request:
      branches: [ main ]
  ```
* **Job Environment**: `ubuntu-latest`
* **Steps**:
  1. Check out repository.
  2. Set up Python 3.10.
  3. Install dependencies from `requirements.txt`.
  4. Run `pytest` to execute all unit tests.

---

## 2. Observability / Telemetry (LangSmith)

We will enable dynamic, user-configurable LangSmith tracing to monitor agent token usage, response times, and path tracing. Tracing credentials will be entered by the user in the frontend, saved to `localStorage`, and passed securely to the backend via headers.

### Component Details
* **Frontend (`App.jsx`)**:
  * Add a section in the Settings panel: "Telemetry & Tracing (LangSmith)".
  * Fields:
    * `enableTracing`: boolean toggle
    * `apiKey`: password text input (visibility toggleable)
    * `project`: text input (defaults to `CriticAI`)
    * `endpoint`: text input (defaults to `https://api.smith.langchain.com`)
  * Storage: Persisted in browser's `localStorage` (e.g. `swarm_langsmith_enabled`, etc.).
  * Data Flow: Include headers in `fetch` requests inside `startCampaign` and `handleRevise` when tracing is enabled:
    * `X-Langsmith-Tracing: true`
    * `X-Langsmith-API-Key: ...`
    * `X-Langsmith-Project: ...`
    * `X-Langsmith-Endpoint: ...`
* **Backend (`server.py` & `swarm.py`)**:
  * Extract LangSmith headers in the FastAPI endpoints (`/api/start`, `/api/feedback`).
  * Wrap the `swarm_app.invoke` execution block using LangChain's `tracing_v2_enabled` context manager to trace the run dynamically:
    ```python
    from langchain_core.tracers.context import tracing_v2_enabled

    # Inside start_swarm and provide_feedback
    if x_langsmith_tracing == "true" and x_langsmith_api_key:
        with tracing_v2_enabled(
            project_name=x_langsmith_project or "CriticAI",
            api_key=x_langsmith_api_key,
            endpoint=x_langsmith_endpoint or "https://api.smith.langchain.com"
        ):
            swarm_app.invoke(initial_state, config=config)
    else:
        # Fall back to default execution (respecting backend env vars)
        swarm_app.invoke(initial_state, config=config)
    ```

---

## 3. FastAPI API Documentation Improvements

We will enhance the FastAPI OpenAPI/Swagger documentation to provide a premium, readable schema.

### Component Details
* **FastAPI Metadata**:
  * Configure custom `title`, `description`, `version`, and `contact` information in `server.py`.
* **Pydantic Response Models**:
  * Define explicit response schemas (`StartResponse`, `FeedbackResponse`, `SessionResponse`).
  * Model attributes will have descriptive docstrings, type annotations, and `Field` descriptions.
* **Route Organization**:
  * Group endpoints under categories using the `tags` argument:
    * `GET /`: `["General"]`
    * `POST /api/start`: `["Swarm Lifecycle"]`
    * `POST /api/feedback`: `["Swarm Lifecycle"]`
    * `GET /api/sessions/{session_id}`: `["Session Management"]`
  * Add rich descriptions and summaries to all endpoints.
  * Define explicit request body parameters and custom header documentation.

---

## 4. Token Optimization

We will resolve two major token redundancy issues.

### Optimization A: Cleaner Worker Revision Loop (Feedback Isolation)
* **Problem**: Currently, when an internal critic rejects a worker's draft, it appends the reviewer feedback block directly to the worker's `deliverable` output in the state (`f"{output}\n\n*Reviewer Feedback (Internal Revision ...)*\n{feedback}"`). When the worker runs again, this dirty string is read from the state as `previous_output`. As a result, the feedback is sent to the LLM twice (once in the draft, and once as `critic_feedback`).
* **Solution**: Add a cleaning function to strip the appended feedback block before passing it to the worker model:
  ```python
  def clean_previous_output(output: str) -> str:
      if not output:
          return ""
      # Split by feedback markdown pattern and return only the clean draft
      return re.split(r"\n\n\*Reviewer Feedback \(Internal Revision \d+\):\*", output)[0].strip()
  ```
  Apply this function in `assign_workers` and `route_feedback`.

### Optimization B: Attached Document Content Isolation
* **Problem**: If a user attaches a file, the entire text content of the file is appended to `task_prompt` (`User Request: {task_prompt}\n\nAttached Document Content:\n{file_content}`). This `task_prompt` is sent to *every* worker node's system prompt. If a file is 10k tokens, each worker receives 10k tokens of redundant input context.
* **Solution**:
  1. Add `user_brief` to the `SwarmState` schema in `swarm.py`.
  2. Populate `user_brief` with the original `task_prompt` text (without the file content) in `server.py`.
  3. In `assign_workers` and `route_feedback`, pass `user_brief` as the worker's main context (`task_prompt`) instead of the full file-appended `task_prompt`.
  4. The orchestrator continues to receive the full file-appended `task_prompt` so it has full context to generate plans and assignments.

---

## 5. Verification & Testing

* **Unit Tests**: Add tests to `tests/test_swarm.py` and `tests/test_guardrails.py` to:
  1. Verify the `clean_previous_output` utility correctly strips reviewer feedback.
  2. Verify that worker nodes receive the clean `user_brief` instead of the file-appended prompt.
* **Integration Tests**: Verify that running the FastAPI server and loading `/docs` renders the improved Swagger documentation with correct schemas and tags.
