<div style="font-size:14pt; line-height:1.5;">

# CriticAI: A Dynamic Multi-Agent Orchestration System Using LangGraph

## Diploma Project Report

**Department of Computer Engineering**
**Academic Year: 2025–2026**

---

---

# <span style="font-size:18pt;">Abstract</span>

---

<p style="font-size:14pt; line-height:1.5;">
The emergence of Large Language Models (LLMs) as practical reasoning engines has revealed a fundamental limitation in existing AI-powered tooling: single-model, single-prompt systems are inherently constrained by their context window, their inability to execute multiple lines of reasoning concurrently, and their lack of persistent memory between interactions. These constraints make them structurally unsuited to complex, multi-faceted knowledge tasks that require dynamic planning, specialist expertise, and iterative human oversight.
</p>

<p style="font-size:14pt; line-height:1.5;">
This report presents <strong>CriticAI</strong>, a full-stack dynamic multi-agent orchestration platform designed to address these limitations directly. The system is built on the LangGraph framework, which models the entire agentic pipeline as a compiled, stateful directed graph — a <code>StateGraph</code> — wherein all nodes read from and write to a single, shared, typed <code>SwarmState</code> object. This architectural choice provides automatic state persistence, auditable control flow, and native support for parallel branch execution through the <code>Send</code> API.
</p>

<p style="font-size:14pt; line-height:1.5;">
CriticAI's Orchestrator node, powered by the Groq-hosted LLaMA 3.3 70B model, accepts an arbitrary natural language task prompt and dynamically generates a machine-validated execution plan using a Pydantic-enforced <code>OrchestratorPlan</code> schema. A deliberate chain-of-thought mechanism — enforced by requiring the LLM to produce a <code>reasoning</code> field before declaring an <code>action_type</code> — eliminates the common failure mode of incorrect agent reassignment. The plan is then executed by dynamically-spawned specialist Worker agents, dispatched as concurrent parallel graph branches via the <code>assign_workers</code> conditional edge and the LangGraph <code>Send</code> API. All Worker-level LLM inference is routed through a locally-hosted model via LM Studio, achieving zero marginal API cost for the execution tier.
</p>

<p style="font-size:14pt; line-height:1.5;">
A formal Human-in-the-Loop (HITL) mechanism is implemented using LangGraph's <code>interrupt_before</code> compilation parameter and <code>update_state</code> API. After all workers complete, the graph pauses, serializes its full state to a SQLite database via the <code>SqliteSaver</code> checkpointer, and returns the deliverables to the user for review. The user may then approve, apply targeted revisions to a single named agent, or trigger a global re-orchestration — all without restarting the workflow. A React/Vite frontend provides a professional AI Workspace interface, featuring session persistence via <code>localStorage</code>, real-time agent status indicators, and per-agent Focused Canvas views.
</p>

<p style="font-size:14pt; line-height:1.5;">
Empirical benchmarking demonstrated that the parallel <code>Send</code> API dispatch achieves a <strong>2.55× reduction</strong> in total execution time for a three-agent task compared to a sequential baseline, confirming the core architectural claim. All six primary project objectives — dynamic orchestration, parallel execution, stateful persistence, HITL control, full-stack integration, and cost optimization — were verified through a comprehensive suite of unit, integration, and end-to-end tests. The system's key limitations, including context window saturation from large file attachments and the absence of cross-session semantic memory, are analyzed and addressed in a detailed 6-month future development roadmap covering vector database integration, async inference, and cloud deployment.
</p>

<p style="font-size:14pt; line-height:1.5;">
CriticAI demonstrates that a principled, state-machine-driven approach to multi-agent orchestration — combining typed shared state, reducer-safe parallel writes, schema-enforced chain-of-thought planning, and formal HITL checkpointing — yields a system that is simultaneously more capable, more reliable, and more cost-effective than any single-prompt LLM alternative.
</p>

**Keywords:** Multi-Agent Systems, LangGraph, LLM Orchestration, Dynamic Agent Spawning, Parallel Execution, Human-in-the-Loop, Stateful AI, FastAPI, React, SQLite, LLaMA 3.3 70B, Pydantic, Send API.

---

---

# <span style="font-size:18pt;">Table of Contents</span>

---

- **Abstract**
- **Table of Contents**
- **List of Figures**
- **List of Tables**

---

- **Chapter 1: Introduction**
  - 1.1 Background and Motivation
  - 1.2 The Problem Statement
  - 1.3 The CriticAI System: A High-Level Overview
  - 1.4 Key Contributions of This Project
  - 1.5 Report Organization

- **Chapter 2: Literature Review** *(separate document)*

- **Chapter 3: Scope and Objectives**
  - 3.1 Project Scope
  - 3.2 Objectives
  - 3.3 Work Breakdown Structure
  - 3.4 Functional Requirements
  - 3.5 Non-Functional Requirements

- **Chapter 4: Proposed Methodology**
  - 4.1 Methodological Philosophy: State Machines for Agentic AI
  - 4.2 The State Object: The System's Shared Memory
    - 4.2.1 `SwarmState` — The Global Graph State
    - 4.2.2 `WorkerState` — The Scoped Worker State
  - 4.3 The State Transition Diagram
  - 4.4 High-Level System Architecture
  - 4.5 The Orchestrator Node: Dynamic Planning with Chain-of-Thought
    - 4.5.1 Structured Output with Pydantic
    - 4.5.2 The `action_type` Validation Safety Net
    - 4.5.3 Few-Shot Prompting for Skill Differentiation
  - 4.6 The Worker Dispatch Mechanism: The `Send` API Fan-Out
  - 4.7 The Human-in-the-Loop (HITL) Methodology
  - 4.8 The Feedback Routing Logic
  - 4.9 The FastAPI Server: The Integration Layer
  - 4.10 The React Frontend: The AI Workspace
  - 4.11 Technology Justification Summary

- **Chapter 5: Implementation**
  - 5.1 Development Environment & Hardware Specification
  - 5.2 Software & Runtime Environment
  - 5.3 System Module Decomposition
    - 5.3.1 Module 1 — LangGraph Orchestration Engine (`swarm.py`)
    - 5.3.2 Module 2 — FastAPI HTTP Server (`server.py`)
    - 5.3.3 Module 3 — React Frontend SPA (`swarm-ui/src/App.jsx`)
    - 5.3.4 Module 4 — SQLite Persistence Layer (`swarm_memory.sqlite`)
  - 5.4 Request–Response Sequence: Full Data Flow
  - 5.5 Feedback Submission Sequence
  - 5.6 Core Code Analysis: Annotated Implementation Excerpts
    - Code Block 5.1 — State Definition with Custom Reducers
    - Code Block 5.2 — The Orchestrator Node
    - Code Block 5.3 — The `assign_workers` Fan-Out Edge
    - Code Block 5.4 — The `/api/feedback` Endpoint
  - 5.7 Schema & State Class Diagram
  - 5.8 Key Implementation Challenges & Solutions

- **Chapter 6: Results and Findings**
  - 6.1 Testing Methodology
  - 6.2 Unit Test Results
    - TC-U01: Pydantic Schema Enforcement on Orchestrator Output
    - TC-U02: `_merge_dicts` Reducer Correctness Under Simulated Parallel Write
    - TC-U03: `EXISTING_ASSIGNMENT` Validation Safety Net
  - 6.3 Integration Test Results
    - TC-I01: `POST /api/start` — Full Session Initialization and HITL Interrupt
    - TC-I02: `POST /api/feedback` — Targeted Revision Routing
    - TC-I03: `GET /api/sessions/{id}` — State Persistence and Recovery
    - TC-I04: PDF File Attachment Parsing and Context Injection
  - 6.4 Performance Benchmarking: Parallel vs. Sequential Agent Execution
  - 6.5 End-to-End Workflow Validation

- **Chapter 7: Limitations and Future Scope**
  - 7.1 Current System Limitations
    - 7.1.1 Context Window Saturation from Large File Attachments
    - 7.1.2 Local VRAM Constraint and Worker Serialization
    - 7.1.3 Absence of Cross-Session Semantic Memory
    - 7.1.4 No Authentication or Multi-Tenancy
    - 7.1.5 Blocking Synchronous `swarm_app.invoke()` in FastAPI
    - 7.1.6 Frontend State is Not Encrypted in localStorage
  - 7.2 Future Scope and Development Roadmap
    - 7.2.1 Phase 1: Async Infrastructure and Security
    - 7.2.2 Phase 2: Semantic Memory with ChromaDB
    - 7.2.3 Phase 3: Scalable Parallel Inference
    - 7.2.4 Phase 4: Retrieval-Augmented Document Intelligence
    - 7.2.5 Phase 5: Multi-Tenancy and Cloud Deployment

- **Chapter 8: Conclusion**
  - 8.1 Summary of Work
  - 8.2 Achievement of Objectives
  - 8.3 Technical Significance
  - 8.4 Final Remarks

---

---

# <span style="font-size:18pt;">List of Figures</span>

---

| Figure No. | Caption | Chapter |
|---|---|---|
| **Figure 3.1** | Work Breakdown Structure — CriticAI Project (Mermaid `flowchart TD`) | Chapter 3 |
| **Figure 4.1** | SwarmState Lifecycle — LangGraph State Transition Diagram (Mermaid `stateDiagram-v2`) | Chapter 4 |
| **Figure 4.2** | CriticAI System Architecture — Component and Data Flow Diagram (Mermaid `graph LR`) | Chapter 4 |
| **Figure 5.1** | End-to-End Sequence Diagram — Initial Task Submission (Mermaid `sequenceDiagram`) | Chapter 5 |
| **Figure 5.2** | Sequence Diagram — Feedback Submission (Targeted & Global) (Mermaid `sequenceDiagram`) | Chapter 5 |
| **Figure 5.3** | UML Class Diagram — Pydantic Schemas and State Dictionaries (Mermaid `classDiagram`) | Chapter 5 |
| **Figure 7.1** | CriticAI — 6-Month Future Development Roadmap (Mermaid `gantt`) | Chapter 7 |

---

---

# <span style="font-size:18pt;">List of Tables</span>

---

| Table No. | Caption | Chapter |
|---|---|---|
| **Table 3.1** | Functional Requirements Specification | Chapter 3 |
| **Table 3.2** | Non-Functional Requirements Specification | Chapter 3 |
| **Table 4.1** | SwarmState Field Definitions and Reducer Annotations | Chapter 4 |
| **Table 4.3** | Technology Selection Justification | Chapter 4 |
| **Table 5.1** | Development Hardware Specification | Chapter 5 |
| **Table 5.2** | Backend Python Stack — Verified Package Versions | Chapter 5 |
| **Table 5.3** | Frontend JavaScript Stack — Verified Package Versions | Chapter 5 |
| **Table 5.4** | External API Services | Chapter 5 |
| **Table 5.5** | `swarm.py` Internal Module Structure | Chapter 5 |
| **Table 5.6** | `server.py` API Endpoint Specification | Chapter 5 |
| **Table 5.7** | `App.jsx` React State Variables | Chapter 5 |
| **Table 5.8** | Implementation Challenges and Adopted Solutions | Chapter 5 |
| **Table 6.1** | Parallel (`Send` API) vs. Sequential 3-Agent Pipeline — Performance Comparison | Chapter 6 |

---

</div>
