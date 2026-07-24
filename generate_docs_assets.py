"""
Generates crisp Architecture Diagram and UI Dashboard visual assets for CriticAI documentation.
Outputs SVG images in docs/images/
"""

import os
import sys

def generate_architecture_diagram_svg(output_path: str):
    svg_content = """<svg width="900" height="520" viewBox="0 0 900 520" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .bg { fill: #09090b; }
    .title { font-family: system-ui, -apple-system, sans-serif; font-size: 18px; font-weight: 700; fill: #f4f4f5; letter-spacing: 1px; }
    .subtitle { font-family: system-ui, -apple-system, sans-serif; font-size: 12px; fill: #a1a1aa; }
    .node-title { font-family: system-ui, -apple-system, sans-serif; font-size: 13px; font-weight: 600; fill: #fafafa; }
    .node-desc { font-family: system-ui, -apple-system, sans-serif; font-size: 10px; fill: #a1a1aa; }
    .badge { font-family: system-ui, -apple-system, sans-serif; font-size: 9px; font-weight: 700; fill: #10b981; }
    .arrow { stroke: #3f3f46; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    .arrow-green { stroke: #10b981; stroke-width: 2; stroke-linecap: round; }
    .arrow-red { stroke: #f43f5e; stroke-width: 2; stroke-dasharray: 4 4; }
  </style>

  <!-- Background -->
  <rect width="900" height="520" rx="16" class="bg" stroke="#27272a" stroke-width="2"/>
  
  <!-- Title -->
  <text x="450" y="36" text-anchor="middle" class="title">CRITICAI SYSTEM ARCHITECTURE</text>
  <text x="450" y="56" text-anchor="middle" class="subtitle">Multi-Agent Workflow Orchestration &amp; Isolated Critic Loops</text>

  <!-- Connectors -->
  <path d="M 170 140 L 230 140" class="arrow" />
  <path d="M 370 140 L 430 140" class="arrow-green" />
  <path d="M 300 175 L 300 230" class="arrow-red" />
  
  <!-- Parallel Worker Fan-Out Lines -->
  <path d="M 550 140 L 610 90" class="arrow-green" />
  <path d="M 550 140 L 610 140" class="arrow-green" />
  <path d="M 550 140 L 610 190" class="arrow-green" />
  
  <!-- Worker to HITL Lines -->
  <path d="M 760 90 L 800 140" class="arrow" />
  <path d="M 760 140 L 800 140" class="arrow" />
  <path d="M 760 190 L 800 140" class="arrow" />
  
  <!-- HITL to Exporter Line -->
  <path d="M 830 180 L 830 350 L 490 350" class="arrow-green" />

  <!-- Node 1: User Brief & Document Input -->
  <rect x="30" y="105" width="140" height="70" rx="12" fill="#18181b" stroke="#3f3f46" stroke-width="1.5"/>
  <text x="100" y="135" text-anchor="middle" class="node-title">1. User Brief</text>
  <text x="100" y="153" text-anchor="middle" class="node-desc">Prompt &amp; PDF/TXT Upload</text>

  <!-- Node 2: Input Guardrail Node -->
  <rect x="230" y="105" width="140" height="70" rx="12" fill="#18181b" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="300" y="135" text-anchor="middle" class="node-title">2. Input Guardrail</text>
  <text x="300" y="153" text-anchor="middle" class="node-desc">Prompt Injection Check</text>

  <!-- Flagged HITL Alert Node -->
  <rect x="230" y="230" width="140" height="55" rx="10" fill="#270f12" stroke="#f43f5e" stroke-width="1.5"/>
  <text x="300" y="255" text-anchor="middle" class="node-title" fill="#f43f5e">Security Alert (HITL)</text>
  <text x="300" y="270" text-anchor="middle" class="node-desc">Abort &amp; Flag Request</text>

  <!-- Node 3: Orchestrator Plan Generator -->
  <rect x="430" y="105" width="140" height="70" rx="12" fill="#022c22" stroke="#10b981" stroke-width="2"/>
  <text x="500" y="135" text-anchor="middle" class="node-title" fill="#10b981">3. Orchestrator</text>
  <text x="500" y="153" text-anchor="middle" class="node-desc">Dynamic Worker Fan-Out</text>

  <!-- Subgraph Worker 1: Backend Security Engineer -->
  <rect x="610" y="65" width="150" height="50" rx="8" fill="#18181b" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="685" y="88" text-anchor="middle" class="node-title">Security Engineer</text>
  <text x="685" y="102" text-anchor="middle" class="node-desc">Worker ↔ Critic Loop</text>

  <!-- Subgraph Worker 2: B2B Copywriter -->
  <rect x="610" y="115" width="150" height="50" rx="8" fill="#18181b" stroke="#8b5cf6" stroke-width="1.5"/>
  <text x="685" y="138" text-anchor="middle" class="node-title">B2B Copywriter</text>
  <text x="685" y="152" text-anchor="middle" class="node-desc">Worker ↔ Critic Loop</text>

  <!-- Subgraph Worker 3: QA Engineer -->
  <rect x="610" y="165" width="150" height="50" rx="8" fill="#18181b" stroke="#ec4899" stroke-width="1.5"/>
  <text x="685" y="188" text-anchor="middle" class="node-title">QA &amp; Test Engineer</text>
  <text x="685" y="202" text-anchor="middle" class="node-desc">Worker ↔ Critic Loop</text>

  <!-- Node 4: HITL State Router -->
  <rect x="780" y="105" width="100" height="70" rx="12" fill="#18181b" stroke="#a855f7" stroke-width="1.5"/>
  <text x="830" y="135" text-anchor="middle" class="node-title" fill="#c084fc">4. HITL Router</text>
  <text x="830" y="153" text-anchor="middle" class="node-desc">Approve / Revise</text>

  <!-- Node 5: Exporter Node & Persistence -->
  <rect x="350" y="320" width="280" height="65" rx="12" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5"/>
  <text x="490" y="348" text-anchor="middle" class="node-title" fill="#38bdf8">5. SQLite Persistence &amp; Exporter</text>
  <text x="490" y="366" text-anchor="middle" class="node-desc">SqliteSaver Checkpoint &amp; Markdown Report Generator</text>

  <!-- Key Highlights Panel -->
  <rect x="30" y="410" width="840" height="80" rx="12" fill="#121215" stroke="#27272a" stroke-width="1"/>
  <text x="50" y="435" class="node-title" fill="#10b981">SYSTEM SPECIFICATIONS &amp; ISOLATION GUARANTEES:</text>
  <text x="50" y="455" class="node-desc" fill="#d4d4d8">• LangGraph StateGraph compiled with interrupt_before=['hitl'] for safe Human Approval Pause.</text>
  <text x="50" y="472" class="node-desc" fill="#d4d4d8">• Isolated Worker Subgraphs prevent key collisions on parallel state writes via custom dict reducers.</text>
  <text x="500" y="455" class="node-desc" fill="#d4d4d8">• HMAC-SHA256 session signature verification on all session IDs.</text>
  <text x="500" y="472" class="node-desc" fill="#d4d4d8">• Automatic execution timeouts (45s) &amp; exponential backoff retries.</text>
</svg>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated SVG: {output_path}")

def generate_ui_screenshot_svg(output_path: str):
    svg_content = """<svg width="1000" height="600" viewBox="0 0 1000 600" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .bg { fill: #09090b; }
    .sidebar { fill: #121215; stroke: #27272a; }
    .card { fill: #18181b; stroke: #27272a; stroke-width: 1; }
    .accent-card { fill: #022c22; stroke: #10b981; stroke-width: 1.5; }
    .header-text { font-family: system-ui, -apple-system, sans-serif; font-size: 15px; font-weight: 700; fill: #fafafa; }
    .sub-text { font-family: system-ui, -apple-system, sans-serif; font-size: 11px; fill: #a1a1aa; }
    .code-text { font-family: monospace; font-size: 10px; fill: #34d399; }
    .badge-green { fill: #064e3b; stroke: #10b981; font-family: sans-serif; font-size: 9px; font-weight: 700; }
  </style>

  <!-- App Frame -->
  <rect width="1000" height="600" rx="14" class="bg" stroke="#3f3f46" stroke-width="2"/>
  
  <!-- Top Bar -->
  <rect width="1000" height="42" fill="#121215" stroke="#27272a" stroke-width="1"/>
  <circle cx="20" cy="21" r="5" fill="#f43f5e"/>
  <circle cx="36" cy="21" r="5" fill="#fbbf24"/>
  <circle cx="52" cy="21" r="5" fill="#10b981"/>
  <text x="500" y="26" text-anchor="middle" class="header-text" font-size="13">CriticAI — Multi-Agent Workspace (BrewBot SaaS Campaign)</text>
  <rect x="880" y="10" width="100" height="22" rx="6" fill="#27272a"/>
  <text x="930" y="24" text-anchor="middle" class="sub-text" fill="#d4d4d8">⚙️ Settings</text>

  <!-- Sidebar -->
  <rect y="42" width="220" height="558" class="sidebar"/>
  <text x="20" y="72" class="header-text" font-size="13">Active Sessions</text>

  <!-- Session Items -->
  <rect x="12" y="85" width="196" height="42" rx="8" class="accent-card"/>
  <text x="24" y="105" class="header-text" font-size="11">BrewBot GTM Strategy</text>
  <text x="24" y="118" class="sub-text" font-size="9">2 Agents • Active</text>

  <rect x="12" y="135" width="196" height="42" rx="8" class="card"/>
  <text x="24" y="155" class="header-text" font-size="11">Fintech Auth Engine</text>
  <text x="24" y="168" class="sub-text" font-size="9">3 Agents • Completed</text>

  <!-- Main Canvas Area -->
  <!-- Swarm Live Story Panel -->
  <rect x="240" y="60" width="340" height="420" rx="12" class="card"/>
  <text x="260" y="88" class="header-text">Swarm Activity Story</text>
  <text x="530" y="88" class="sub-text" fill="#10b981">⏱ 22.4s</text>

  <!-- Agent Node 1 -->
  <rect x="255" y="105" width="310" height="65" rx="8" fill="#09090b" stroke="#10b981" stroke-width="1"/>
  <text x="270" y="125" class="header-text" font-size="12">Backend Security Engineer</text>
  <text x="540" y="125" class="code-text">DONE</text>
  <text x="270" y="145" class="sub-text">✓ Added Argon2id password hashing &amp; JWT auth</text>

  <!-- Agent Node 2 -->
  <rect x="255" y="180" width="310" height="65" rx="8" fill="#09090b" stroke="#10b981" stroke-width="1"/>
  <text x="270" y="200" class="header-text" font-size="12">B2B Copywriter</text>
  <text x="540" y="200" class="code-text">DONE</text>
  <text x="270" y="220" class="sub-text">✓ Drafted high-converting SaaS landing page copy</text>

  <!-- Behind the Scenes Accordion -->
  <rect x="255" y="260" width="310" height="200" rx="8" fill="#09090b" stroke="#3f3f46" stroke-width="1"/>
  <text x="270" y="280" class="header-text" font-size="11">Behind the Scenes (Execution Logs)</text>
  <text x="270" y="300" class="code-text">[ORCHESTRATOR] 2 worker subgraphs spawned via Send API</text>
  <text x="270" y="315" class="code-text">[CRITIC:Security] Draft Rejected -> Revision 1</text>
  <text x="270" y="330" class="code-text">[WORKER:Security] Re-executing with Argon2id fix...</text>
  <text x="270" y="345" class="code-text">[CRITIC:Security] Deliverable APPROVED</text>
  <text x="270" y="360" class="code-text">[HITL ROUTER] Graph paused at interrupt_before=['hitl']</text>

  <!-- Right Canvas: Deliverables Preview -->
  <rect x="600" y="60" width="380" height="420" rx="12" class="card"/>
  <text x="620" y="88" class="header-text">Deliverables Canvas</text>
  <rect x="880" y="72" width="80" height="24" rx="6" fill="#10b981"/>
  <text x="920" y="88" text-anchor="middle" class="header-text" font-size="10" fill="#09090b">Export MD</text>

  <rect x="615" y="105" width="350" height="355" rx="8" fill="#09090b" stroke="#27272a" stroke-width="1"/>
  <text x="630" y="130" class="header-text" font-size="13" fill="#38bdf8"># BrewBot GTM &amp; Technical Architecture</text>
  <text x="630" y="155" class="sub-text" fill="#e4e4e7">## 1. Authentication Security Engine</text>
  <text x="630" y="175" class="sub-text" fill="#a1a1aa">• OAuth2 Bearer token authentication with JWT stateless sessions.</text>
  <text x="630" y="195" class="sub-text" fill="#a1a1aa">• Password hashing: Argon2id with 64MB memory cost.</text>
  <text x="630" y="215" class="sub-text" fill="#a1a1aa">• Rate limiting: 100 req/min per IP via Redis token bucket.</text>
  <text x="630" y="250" class="sub-text" fill="#e4e4e7">## 2. GTM Copywriter Positioning</text>
  <text x="630" y="270" class="sub-text" fill="#a1a1aa">"Precision-roasted coffee curated by AI for your palate."</text>

  <!-- Bottom HITL Input Bar -->
  <rect x="240" y="495" width="740" height="85" rx="12" fill="#121215" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="260" y="520" class="header-text" font-size="12" fill="#60a5fa">Human-in-the-Loop Feedback &amp; Revision Router</text>
  <rect x="260" y="530" width="600" height="38" rx="8" fill="#18181b" stroke="#3f3f46" stroke-width="1"/>
  <text x="275" y="553" class="sub-text" fill="#71717a">Type targeted feedback for an agent or click Approve to finalize...</text>
  <rect x="870" y="530" width="95" height="38" rx="8" fill="#10b981"/>
  <text x="917" y="553" text-anchor="middle" class="header-text" font-size="11" fill="#09090b">Approve ✔</text>
</svg>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated SVG: {output_path}")

if __name__ == "__main__":
    out_dir = "docs/images"
    os.makedirs(out_dir, exist_ok=True)
    
    arch_svg = os.path.join(out_dir, "architecture_diagram.svg")
    ui_svg = os.path.join(out_dir, "ui_dashboard_screenshot.svg")
    
    generate_architecture_diagram_svg(arch_svg)
    generate_ui_screenshot_svg(ui_svg)
    print("Documentation visual assets generated successfully.")
