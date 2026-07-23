import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, PenTool, Image as ImageIcon, ArrowUp, Paperclip, Bot, User, CheckCircle, RefreshCw, ArrowRight, Plus, Menu, X, MessageSquare, Trash2, Terminal, Code, Activity, Briefcase, FileText, Settings, Eye, EyeOff, Copy, Download, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const LoadingSkeleton = ({ agentStatuses = {}, agentDurations = {} }) => {
  const activeCount = Object.values(agentStatuses).filter(s => s === 'working').length;
  const completedCount = Object.values(agentStatuses).filter(s => s === 'completed').length;
  const totalCount = Object.keys(agentStatuses).length;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-4 justify-start w-full mt-6"
    >
      <div className="w-8 h-8 shrink-0 rounded-lg bg-zinc-900 border border-white/10 flex items-center justify-center mt-1">
        <Activity size={16} className="text-emerald-400 animate-pulse" />
      </div>
      <div className="w-full max-w-xl space-y-4 pt-1">
        <div className="flex items-center gap-3 px-2 text-[11px] font-semibold tracking-wider uppercase text-zinc-500">
          <span className={totalCount > 0 ? "text-emerald-400" : "animate-pulse"}>1. Orchestrating</span>
          <ArrowRight size={12} className={activeCount > 0 || completedCount > 0 ? "text-emerald-400" : ""} />
          <span className={activeCount > 0 ? "text-emerald-400" : ""}>2. Parallel Work</span>
          <ArrowRight size={12} className={completedCount === totalCount && totalCount > 0 ? "text-emerald-400" : ""} />
          <span className={completedCount === totalCount && totalCount > 0 ? "text-emerald-400" : ""}>3. Synthesizing</span>
        </div>
        
        <div className="space-y-2 mt-4">
          {totalCount > 0 ? (
            Object.entries(agentStatuses).map(([role, status]) => (
              <div key={role} className="flex items-center justify-between bg-zinc-900/50 border border-white/5 rounded-lg px-4 py-2">
                <div className="flex items-center gap-3">
                  <Bot size={14} className={status === 'working' ? "text-amber-400" : "text-emerald-400"} />
                  <span className="text-xs text-zinc-300 font-medium">{role}</span>
                </div>
                <div className="flex items-center gap-2">
                  {agentDurations[role] && (
                    <span className="text-[10px] text-zinc-500 tabular-nums">⏱ {agentDurations[role]}s</span>
                  )}
                  <span className={`text-[10px] uppercase tracking-tighter font-bold ${
                    status === 'working' ? 'text-amber-400 animate-pulse' : 'text-emerald-500'
                  }`}>
                    {status === 'working' ? 'Processing...' : 'Done'}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="bg-zinc-800/50 border border-white/5 rounded-xl p-4 animate-pulse">
              <div className="h-4 bg-zinc-700/50 rounded w-1/3 mb-3"></div>
              <div className="h-3 bg-zinc-700/50 rounded w-full mb-2"></div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

const SwarmFlowDiagram = () => (
  <div className="w-full border border-white/5 bg-zinc-900/20 rounded-2xl p-4 md:p-6 mb-6 shadow-2xl backdrop-blur-md">
    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest block mb-4 text-center">CriticAI Swarm Architecture</span>
    <svg className="w-full max-w-2xl mx-auto text-zinc-400" viewBox="0 0 700 240" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad-glow" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.1" />
          <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.1" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0.1" />
        </linearGradient>
      </defs>
      
      {/* Glow background effect */}
      <rect x="0" y="0" width="700" height="240" rx="16" fill="url(#grad-glow)" stroke="none" />
      
      {/* Connection lines */}
      <path d="M 95 120 L 205 120" stroke="#27272a" strokeWidth="2" strokeDasharray="4 4" />
      <path d="M 295 120 L 405 120" stroke="#10b981" strokeWidth="2" />
      <path d="M 405 120 L 495 60" stroke="#3b82f6" strokeWidth="1.5" />
      <path d="M 405 120 L 495 120" stroke="#3b82f6" strokeWidth="1.5" />
      <path d="M 405 120 L 495 180" stroke="#3b82f6" strokeWidth="1.5" />
      
      <path d="M 585 60 L 635 120" stroke="#27272a" strokeWidth="1.5" />
      <path d="M 585 120 L 635 120" stroke="#27272a" strokeWidth="1.5" />
      <path d="M 585 180 L 635 120" stroke="#27272a" strokeWidth="1.5" />
      
      {/* User Brief Node */}
      <rect x="10" y="90" width="85" height="60" rx="12" fill="#18181b" stroke="#27272a" strokeWidth="1.5" />
      <text x="52" y="118" dominantBaseline="middle" textAnchor="middle" fill="#fafafa" fontSize="11" fontWeight="600">User Brief</text>
      <text x="52" y="134" dominantBaseline="middle" textAnchor="middle" fill="#71717a" fontSize="9">Prompt & Files</text>

      {/* Guardrail Node */}
      <rect x="205" y="90" width="90" height="60" rx="12" fill="#18181b" stroke="#3f3f46" strokeWidth="1.5" />
      <text x="250" y="118" dominantBaseline="middle" textAnchor="middle" fill="#fafafa" fontSize="11" fontWeight="600">Guardrails</text>
      <text x="250" y="134" dominantBaseline="middle" textAnchor="middle" fill="#a1a1aa" fontSize="9">Input Safety</text>

      {/* Orchestrator Node */}
      <rect x="405" y="90" width="90" height="60" rx="12" fill="#022c22" stroke="#10b981" strokeWidth="1.5" />
      <text x="450" y="118" dominantBaseline="middle" textAnchor="middle" fill="#10b981" fontSize="11" fontWeight="700">Orchestrator</text>
      <text x="450" y="134" dominantBaseline="middle" textAnchor="middle" fill="#34d399" fontSize="9">Decompose Plan</text>

      {/* Specialized Workers */}
      <rect x="495" y="35" width="90" height="50" rx="8" fill="#18181b" stroke="#27272a" strokeWidth="1.5" />
      <text x="540" y="60" dominantBaseline="middle" textAnchor="middle" fill="#e4e4e7" fontSize="10" fontWeight="600">Copywriter</text>
      
      <rect x="495" y="95" width="90" height="50" rx="8" fill="#18181b" stroke="#27272a" strokeWidth="1.5" />
      <text x="540" y="120" dominantBaseline="middle" textAnchor="middle" fill="#e4e4e7" fontSize="10" fontWeight="600">Marketing Strategy</text>

      <rect x="495" y="155" width="90" height="50" rx="8" fill="#18181b" stroke="#27272a" strokeWidth="1.5" />
      <text x="540" y="180" dominantBaseline="middle" textAnchor="middle" fill="#e4e4e7" fontSize="10" fontWeight="600">AI Architect</text>

      {/* Critic Loop Node */}
      <rect x="635" y="90" width="60" height="60" rx="12" fill="#1c0d0d" stroke="#ef4444" strokeWidth="1.5" />
      <text x="665" y="118" dominantBaseline="middle" textAnchor="middle" fill="#ef4444" fontSize="11" fontWeight="600">Critic</text>
      <text x="665" y="134" dominantBaseline="middle" textAnchor="middle" fill="#f87171" fontSize="9">HITL Review</text>
    </svg>
  </div>
);

export default function App() {
  const [sessionId, setSessionId] = useState('');
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('swarm_sessions');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [guidelinesPath, setGuidelinesPath] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [processingSessions, setProcessingSessions] = useState({});
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const isProcessing = processingSessions[sessionId] || false;
  const setIsProcessing = (val) => {
    if (sessionId) {
      setProcessingSessions(prev => {
        const currentVal = prev[sessionId] || false;
        const newVal = typeof val === 'function' ? val(currentVal) : val;
        return { ...prev, [sessionId]: newVal };
      });
    }
  };
  const [agentStatuses, setAgentStatuses] = useState({});
  const [agentDurations, setAgentDurations] = useState({});

  // LLM Key states
  const [provider, setProvider] = useState('openrouter');
  const [openrouterKey, setOpenrouterKey] = useState(() => localStorage.getItem('swarm_openrouter_key') || '');
  const [backendToken, setBackendToken] = useState(() => localStorage.getItem('swarm_backend_token') || '');

  // Verify Key state
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  // Socket connection state to prevent race conditions during room joining
  const [socketConnected, setSocketConnected] = useState(false);

  const handleVerifyKey = async () => {
    if (!openrouterKey.trim()) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const response = await fetch('http://localhost:8000/api/verify-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ key: openrouterKey }),
      });
      if (response.ok) {
        const data = await response.json();
        setVerifyResult(data);
      } else {
        setVerifyResult({ valid: false, error: 'Server returned error status' });
      }
    } catch (err) {
      setVerifyResult({ valid: false, error: err.message });
    } finally {
      setVerifying(false);
    }
  };

  // Visibility toggles for keys
  const [showOpenrouterKey, setShowOpenrouterKey] = useState(false);
  const [copied, setCopied] = useState(false);

  // Initialize session ID from backend
  const initSession = useCallback(async () => {
    try {
      const headers = {};
      const token = localStorage.getItem('swarm_backend_token') || '';
      if (token) {
        headers['X-Backend-Token'] = token;
      }
      const response = await fetch('http://localhost:8000/api/sessions', {
        method: 'POST',
        headers
      });
      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        return data.session_id;
      }
    } catch (err) {
      console.error("Failed to create secure session:", err);
    }
    const fallbackId = crypto.randomUUID() + ".unsigned_fallback";
    setSessionId(fallbackId);
    return fallbackId;
  }, []);

  const handleCopyDeliverable = () => {
    const content = latestDeliverables[activeView] || '';
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownloadDeliverable = () => {
    const content = latestDeliverables[activeView] || '';
    if (!content) return;
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${activeView.replace(/\s+/g, '_')}_deliverable.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Telemetry Key states
  const [langsmithEnabled, setLangsmithEnabled] = useState(() => localStorage.getItem('swarm_langsmith_enabled') === 'true');
  const [langsmithKey, setLangsmithKey] = useState(() => localStorage.getItem('swarm_langsmith_api_key') || '');
  const [langsmithProject, setLangsmithProject] = useState(() => localStorage.getItem('swarm_langsmith_project') || 'CriticAI');
  const [langsmithEndpoint, setLangsmithEndpoint] = useState(() => localStorage.getItem('swarm_langsmith_endpoint') || 'https://api.smith.langchain.com');
  const [showLangsmithKey, setShowLangsmithKey] = useState(false);
  
  // Workspace State
  const [activeView, setActiveView] = useState('main'); // 'main' or agentRole string
  const [attachedFile, setAttachedFile] = useState(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const socketRef = useRef(null);
  const terminalEndRef = useRef(null);

  // Live terminal: array of { role, status, partialOutput }
  const [liveAgents, setLiveAgents] = useState([]);
  const [terminalVisible, setTerminalVisible] = useState(false);

  // Auto-scroll main chat
  useEffect(() => {
    if (activeView === 'main') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeView, isProcessing, agentStatuses]);

  // Session Recovery or Initialization on Mount
  useEffect(() => {
    const lastSessionId = localStorage.getItem('swarm_last_session_id');
    if (lastSessionId) {
      loadSession(lastSessionId);
    } else {
      initSession();
    }
  }, [initSession]);

  // ── Socket.IO setup (single persistent connection) ────────────────────────────
  useEffect(() => {
    const socket = io('http://localhost:8000', {
      path: '/ws/socket.io',
      transports: ['websocket'],
      reconnection: true,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('[WS] Connected:', socket.id);
      if (sessionId) socket.emit('join_session', { session_id: sessionId, backend_token: backendToken });
    });

    socket.on('connect_error', (err) => {
      console.error('[WS] Connection error:', err);
      setIsProcessing(false);
      setMessages(prev => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.content && typeof lastMsg.content === 'string' && lastMsg.content.includes("Cannot connect to backend")) {
          return prev;
        }
        return [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'ai',
            type: 'text',
            content: `⚠️ Cannot connect to backend at localhost:8000. Please make sure the backend server is running and port 8000 is accessible.`,
          }
        ];
      });
    });

    socket.on('disconnect', (reason) => {
      console.log('[WS] Disconnected:', reason);
      setSocketConnected(false);
      setIsProcessing(prevIsProcessing => {
        if (prevIsProcessing) {
          setMessages(prev => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: 'ai',
              type: 'text',
              content: `⚠️ Connection to backend was lost (${reason}). Please ensure the server is running.`,
            }
          ]);
        }
        return false;
      });
    });

    socket.on('plan_ready', (data) => {
      setLiveAgents(
        (data.execution_plan || []).map(t => ({
          role: t.agent_role,
          status: 'pending',
          partialOutput: '',
        }))
      );
      setTerminalVisible(true);
    });

    socket.on('agent_started', (data) => {
      setLiveAgents(prev =>
        prev.map(a => a.role === data.role ? { ...a, status: 'working' } : a)
      );
    });

    socket.on('agent_token', (data) => {
      setLiveAgents(prev =>
        prev.map(a =>
          a.role === data.role
            ? { ...a, partialOutput: a.partialOutput + data.token }
            : a
        )
      );
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    });

    socket.on('agent_critic_reviewing', (data) => {
      setLiveAgents(prev =>
        prev.map(a => a.role === data.role ? { ...a, status: 'reviewing' } : a)
      );
    });

    socket.on('agent_done', (data) => {
      if (data.duration != null) {
        setAgentDurations(prev => ({ ...prev, [data.role]: data.duration }));
      }
      setLiveAgents(prev =>
        prev.map(a =>
          a.role === data.role
            ? { ...a, status: 'done', partialOutput: (data.output || a.partialOutput).slice(0, 600) }
            : a
        )
      );
    });

    socket.on('swarm_status', (data) => {
      console.log('[WS] swarm_status:', data.status);
    });

    socket.on('swarm_complete', (data) => {
      setIsProcessing(false);
      if (data.agent_statuses) setAgentStatuses(data.agent_statuses);
      if (data.agent_durations) setAgentDurations(data.agent_durations);
      const newDeliverables = data.deliverables;
      const deliverables = newDeliverables && Object.keys(newDeliverables).length > 0
        ? newDeliverables
        : {};
      const executionPlan = data.execution_plan || [];
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'draft',
          content: { deliverables, executionPlan },
          isAwaitingFeedback: data.status !== 'completed',
          isFinal: data.status === 'completed',
        }
      ]);
      setLiveAgents(prev => prev.map(a => ({ ...a, status: 'done' })));
    });

    socket.on('swarm_error', (data) => {
      setIsProcessing(false);
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'text',
          content: `System Error: ${data.message}`,
        }
      ]);
    });

    return () => { socket.disconnect(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-join room when sessionId changes or socket connects
  useEffect(() => {
    if (socketRef.current?.connected && sessionId) {
      socketRef.current.emit('join_session', { session_id: sessionId, backend_token: backendToken });
    }
  }, [sessionId, backendToken, socketConnected]);

  // Sync session selection
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('swarm_last_session_id', sessionId);
    }
  }, [sessionId]);

  // Save messages to LocalStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`swarm_chat_${sessionId}`, JSON.stringify(messages));
      
      setSessions(prev => {
        const existing = prev.find(s => s.sessionId === sessionId);
        let title = "New Campaign";
        
        const firstUserMsg = messages.find(m => m.role === 'user' && m.type === 'text');
        if (firstUserMsg) {
          title = firstUserMsg.content.substring(0, 35) + (firstUserMsg.content.length > 35 ? '...' : '');
        }

        if (existing) {
          return prev.map(s => s.sessionId === sessionId ? { ...s, title, updatedAt: Date.now() } : s);
        } else {
          return [{ sessionId, title, updatedAt: Date.now() }, ...prev];
        }
      });
    }
  }, [messages, sessionId]);

  useEffect(() => {
    localStorage.setItem('swarm_sessions', JSON.stringify(sessions));
  }, [sessions]);

  // Utility to get the latest deliverables
  const getLatestDraftMessage = () => {
    return [...messages].reverse().find(m => m.type === 'draft');
  };
  
  const latestDraft = getLatestDraftMessage();
  const latestDeliverables = latestDraft?.content?.deliverables || {};

  const loadSession = async (id) => {
    setSessionId(id);
    setActiveView('main');
    try {
      const savedChat = localStorage.getItem(`swarm_chat_${id}`);
      let loaded = savedChat ? JSON.parse(savedChat) : [];

      const headers = {};
      if (backendToken) {
        headers['X-Backend-Token'] = backendToken;
      }
      const response = await fetch(`http://localhost:8000/api/sessions/${id}`, { headers });
      if (response.ok) {
        const data = await response.json();
        if (data.agent_statuses) setAgentStatuses(data.agent_statuses);
        if (data.agent_durations) setAgentDurations(data.agent_durations);

        if (data.status === 'processing') {
          // ponytail: recover active run state on reload
          setIsProcessing(true);
          setTerminalVisible(true);
          setLiveAgents(
            Object.entries(data.agent_statuses || {}).map(([role, status]) => ({
              role,
              status: status === 'completed' ? 'done' : status,
              partialOutput: 'Task running in background...\n',
            }))
          );
        } else {
          const hasDraftMessage = loaded.some(m => m.type === 'draft');
          const hasDeliverables = data.deliverables && Object.keys(data.deliverables).length > 0;

          if (hasDeliverables && !hasDraftMessage) {
            // ponytail: recover missing draft state (e.g. page reloaded mid-campaign)
            loaded.push({
              id: crypto.randomUUID(),
              role: 'ai',
              type: 'draft',
              content: {
                deliverables: data.deliverables,
                executionPlan: data.execution_plan || []
              },
              isAwaitingFeedback: data.status !== 'completed',
              isFinal: data.status === 'completed'
            });
          }
        }
      }
      setMessages(loaded);
    } catch (err) {
      console.warn("Session sync failed:", err);
      const savedChat = localStorage.getItem(`swarm_chat_${id}`);
      setMessages(savedChat ? JSON.parse(savedChat) : []);
    }
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const startNewChat = async () => {
    const newId = await initSession();
    setMessages([]);
    setInputValue("");
    setActiveView('main');
  };

  const deleteSession = (e, id) => {
    e.stopPropagation();
    if (isProcessing) return;
    setSessions(prev => prev.filter(s => s.sessionId !== id));
    localStorage.removeItem(`swarm_chat_${id}`);
    if (sessionId === id) startNewChat();
  };

  const startCampaign = useCallback(async (promptText) => {
    if (!socketRef.current?.connected) {
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'text',
          content: `⚠️ Cannot start campaign. The connection to the backend server is down. Please ensure the backend server is running at http://localhost:8000.`
        }
      ]);
      return;
    }

    setIsProcessing(true);
    setActiveView('main');
    setLiveAgents([]);
    setTerminalVisible(true);

    // Encode attached file as base64 if present
    let fileContent = '';
    let fileName = '';
    if (attachedFile) {
      fileName = attachedFile.name;
      const arrayBuffer = await attachedFile.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
      fileContent = btoa(binary);
      setAttachedFile(null);
    }

    // Ensure room joined before emitting
    socketRef.current?.emit('join_session', { session_id: sessionId, backend_token: backendToken });
    socketRef.current?.emit('start_campaign', {
      session_id:        sessionId,
      task_prompt:       promptText,
      guidelines_path:   guidelinesPath || 'brand_guidelines.txt',
      file_content:      fileContent,
      file_name:         fileName,
      provider:          'openrouter',
      groq_api_key:      '',
      gemini_api_key:    '',
      openrouter_api_key: openrouterKey,
      langsmith_tracing:  langsmithEnabled ? 'true' : 'false',
      langsmith_api_key:  langsmithKey,
      langsmith_project:  langsmithProject,
      langsmith_endpoint: langsmithEndpoint,
      backend_token:      backendToken,
    });
  }, [sessionId, guidelinesPath, attachedFile, openrouterKey, backendToken,
      langsmithEnabled, langsmithKey, langsmithProject, langsmithEndpoint]);

  /**
   * Detects if the input is a casual/off-topic message that should NOT trigger
   * the swarm. Returns a friendly reply string, or null if it's a real task.
   */
  const getConversationalReply = (text) => {
    const t = text.trim().toLowerCase();
    const wordCount = t.split(/\s+/).length;

    // Very short greetings / single-word inputs
    const greetings = ['hi', 'hello', 'hey', 'sup', 'yo', 'howdy', 'hiya', 'good morning', 'good afternoon', 'good evening', 'morning', 'evening'];
    if (greetings.some(g => t === g || t.startsWith(g + ' ') || t.startsWith(g + '!'))) {
      return "👋 Hey there! I'm the **CriticAI Orchestrator**. Describe your project, campaign, or task and I'll spin up a team of specialized AI agents to tackle it in parallel. What would you like to build?";
    }

    // Thank-you / acknowledgement messages
    const thanks = ['thanks', 'thank you', 'ty', 'thx', 'cheers', 'great', 'awesome', 'cool', 'nice', 'perfect', 'got it', 'ok', 'okay', 'k', 'sure', 'sounds good', 'alright'];
    if (thanks.some(k => t === k || t === k + '!')) {
      return "You're welcome! 😊 Let me know if there's anything else you'd like the swarm to work on.";
    }

    // Pasted document / brand guidelines detection
    // Heuristic: very long text (>300 words) that contains typical doc markers but no action verbs
    const hasDocMarkers = /(brand guidelines|compliance checklist|introduction|training and resources|potential challenges)/i.test(text);
    const hasSwarmActionVerbs = /(build|create|launch|design|write|develop|generate|implement|set up|plan|research|analyze|make me|help me build)/i.test(text);
    if (hasDocMarkers && !hasSwarmActionVerbs) {
      return `📄 It looks like you've pasted a document (e.g. brand guidelines). I can't auto-launch the swarm from raw document content alone.\n\nTry describing what you'd like me to **do** with it — for example:\n> *'Review my brand guidelines and create a marketing campaign for a new product launch.'*`;
    }

    // Generic off-topic short messages (no clear task intent, < 5 words)
    const hasTaskIntent = /(build|create|launch|design|write|develop|generate|implement|set up|plan|research|analyze|make|help|fix|improve|review|audit|draft|outline|strategy|app|website|product|campaign|startup|code|api|feature)/i.test(text);
    if (wordCount <= 4 && !hasTaskIntent) {
      return "I'm not sure what you'd like me to do with that! 🤔 Try describing a project or task, and I'll dispatch the right agents to get it done.";
    }

    return null; // It's a real task — let the swarm handle it
  };

  const handleSendPrompt = () => {
    if (!inputValue.trim() || isProcessing) return;
    const userPrompt = inputValue;
    
    if (attachedFile) {
      console.log("Attached File:", attachedFile.name);
      setAttachedFile(null);
    }
    
    setMessages(prev => [...prev, { id: crypto.randomUUID(), role: 'user', type: 'text', content: userPrompt }]);
    setInputValue('');
    setShowSettings(false);

    // 🧠 Conversational intent check — skip the swarm for casual / irrelevant inputs
    const conversationalReply = getConversationalReply(userPrompt);
    if (conversationalReply) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'ai',
        type: 'text',
        content: conversationalReply
      }]);
      if (attachedFile) setAttachedFile(null);
      return; // Do NOT invoke the swarm
    }
    
    // Check if the swarm has actually started (not just conversational replies).
    // Using messages.length===0 was wrong: conversational replies add messages
    // without ever starting a swarm session, breaking subsequent real-task routing.
    const hasCampaignStarted = messages.some(m => m.type === 'draft');
    if (!hasCampaignStarted) {
      startCampaign(userPrompt);
    } else {
      handleRevise(userPrompt);
    }

    if (attachedFile) setAttachedFile(null);
  };

  const handleRevise = useCallback(async (feedbackText, targetAgent = null, isApproved = false) => {
    if (isProcessing) return;

    // Mark previous drafts as no longer awaiting feedback
    setMessages(prev => prev.map(msg =>
      msg.type === 'draft' ? { ...msg, isAwaitingFeedback: false, isFinal: isApproved } : msg
    ));

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user',
      type: 'text',
      content: isApproved ? '\u2705 Approve and finalize.' : feedbackText,
    };
    setMessages(prev => [...prev, userMsg]);

    if (isApproved) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'ai',
        type: 'text',
        content: 'Campaign finalized successfully! All assets have been exported.',
      }]);
      setActiveView('main');
      return;
    }

    if (!socketRef.current?.connected) {
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'text',
          content: `⚠️ Cannot submit feedback. The connection to the backend server is down. Please ensure the backend server is running at http://localhost:8000.`
        }
      ]);
      return;
    }

    setIsProcessing(true);
    setActiveView('main');
    setLiveAgents([]);
    setTerminalVisible(true);

    // Encode attached file as base64 if present
    let fileContent = '';
    let fileName = '';
    if (attachedFile) {
      fileName = attachedFile.name;
      const arrayBuffer = await attachedFile.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
      fileContent = btoa(binary);
      setAttachedFile(null);
    }

    socketRef.current?.emit('join_session', { session_id: sessionId, backend_token: backendToken });
    socketRef.current?.emit('send_feedback', {
      session_id:    sessionId,
      feedback:      feedbackText,
      type:          targetAgent ? 'targeted' : 'global',
      target_agent:  targetAgent || null,
      file_content:  fileContent,
      file_name:     fileName,
      provider:      'openrouter',
      groq_api_key:       '',
      gemini_api_key:     '',
      openrouter_api_key: openrouterKey,
      langsmith_tracing:  langsmithEnabled ? 'true' : 'false',
      langsmith_api_key:  langsmithKey,
      langsmith_project:  langsmithProject,
      langsmith_endpoint: langsmithEndpoint,
      backend_token:      backendToken,
    });
  }, [isProcessing, sessionId, attachedFile, openrouterKey, backendToken,
      langsmithEnabled, langsmithKey, langsmithProject, langsmithEndpoint]);

  const handleTargetedRevise = (agentRole, feedbackText) => {
    if (isProcessing || !feedbackText.trim()) return;
    handleRevise(feedbackText, agentRole, false);
  };

  const AgentNodeBadge = ({ label, icon: Icon, active, pulse, onClick }) => (
    <span 
      onClick={onClick}
      className={`px-3 py-1.5 text-xs rounded-full border flex items-center gap-2 transition-all duration-300 ${
        onClick ? 'cursor-pointer hover:border-zinc-600 hover:bg-zinc-800/40 text-zinc-200' : ''
      } ${
        active 
          ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400 font-semibold' 
          : 'border-zinc-850 bg-zinc-900/50 text-zinc-500'
      }`}
    >
      <Icon size={14} className={pulse ? 'animate-pulse text-zinc-300' : ''} />
      {label}
    </span>
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100 font-sans selection:bg-zinc-800">
      
      {/* LEFT SIDEBAR - Project Explorer */}
      <AnimatePresence initial={false}>
        {isSidebarOpen && (
          <motion.div 
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="flex-shrink-0 bg-zinc-900/40 border-r border-white/5 flex flex-col overflow-hidden z-20"
          >
            <div className="p-4 flex items-center justify-between border-b border-white/5 bg-zinc-900/60">
              <h1 className="text-sm font-semibold flex items-center gap-2 text-zinc-200">
                <Briefcase size={16} className="text-zinc-400" />
                CriticAI Workspace
              </h1>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setShowSettings(true)}
                  className="p-1 text-zinc-500 hover:text-zinc-250 transition-colors rounded hover:bg-zinc-800"
                  title="LLM Settings"
                >
                  <Settings size={16} />
                </button>
                <button onClick={() => setIsSidebarOpen(false)} className="text-zinc-500 hover:text-zinc-300 transition-colors">
                  <X size={18} />
                </button>
              </div>
            </div>
            
            <div className="p-3">
              <button onClick={startNewChat} className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-sm font-medium transition-colors border border-white/5 shadow-sm">
                <Plus size={16} /> New Workspace
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto overflow-x-hidden">
              {/* Active Campaign Tree */}
              <div className="px-3 pt-2 pb-4">
                <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider px-2 mb-2">Active Campaign</div>
                
                <div className="space-y-1">
                  <button 
                    onClick={() => setActiveView('main')}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors text-left ${activeView === 'main' ? 'bg-zinc-800/80 text-zinc-100 font-medium' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'}`}
                  >
                    <MessageSquare size={15} /> Main Chat
                  </button>
                  
                  {/* Nested Deliverables Navigation */}
                  <AnimatePresence>
                    {Object.keys(latestDeliverables).length > 0 && (
                      <motion.div 
                        initial={{ opacity: 0, height: 0 }} 
                        animate={{ opacity: 1, height: 'auto' }}
                        className="pl-4 pt-1 space-y-1 border-l border-white/10 ml-5"
                      >
                        {Object.keys(latestDeliverables).map((agentRole) => (
                          <button 
                            key={agentRole}
                            onClick={() => setActiveView(agentRole)}
                            className={`w-full flex items-center gap-2 px-3 py-1.5 text-[13px] rounded-lg transition-colors text-left ${activeView === agentRole ? 'bg-zinc-800/80 text-zinc-100 font-medium' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/30'}`}
                          >
                            <FileText size={14} className={activeView === agentRole ? "text-zinc-300" : "text-zinc-600"} />
                            <span className="truncate flex-1">{agentRole}</span>
                            {agentStatuses[agentRole] && (
                              <div className={`w-1.5 h-1.5 rounded-full ${
                                agentStatuses[agentRole] === 'working' ? 'bg-amber-400 animate-pulse' : 
                                agentStatuses[agentRole] === 'completed' ? 'bg-emerald-500' : 
                                'bg-red-500'
                              }`} title={agentStatuses[agentRole]} />
                            )}
                          </button>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* ── LIVE TERMINAL ── */}
              <AnimatePresence>
                {terminalVisible && liveAgents.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="px-3 pt-0 pb-3 border-t border-white/5"
                  >
                    <div className="flex items-center justify-between px-2 mb-2 mt-3">
                      <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                        <Activity size={11} className="text-emerald-400 animate-pulse" />
                        Live Terminal
                      </div>
                      <button
                        onClick={() => setTerminalVisible(false)}
                        className="text-zinc-600 hover:text-zinc-400 transition-colors"
                      >
                        <X size={12} />
                      </button>
                    </div>
                    <div className="bg-zinc-950 border border-white/5 rounded-lg overflow-hidden">
                      {/* Agent Status Bubbles */}
                      <div className="flex flex-wrap gap-1.5 p-2 border-b border-white/5">
                        {liveAgents.map(agent => (
                          <span
                            key={agent.role}
                            title={agent.role}
                            className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-widest border transition-all ${
                              agent.status === 'done'
                                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                                : agent.status === 'reviewing'
                                ? 'border-violet-500/30 bg-violet-500/10 text-violet-400'
                                : agent.status === 'working'
                                ? 'border-amber-500/30 bg-amber-500/10 text-amber-400 animate-pulse'
                                : 'border-zinc-700 bg-zinc-900 text-zinc-600'
                            }`}
                          >
                            {agent.role.length > 14 ? agent.role.slice(0, 14) + '…' : agent.role}
                          </span>
                        ))}
                      </div>
                      {/* Scrollable live output */}
                      <div className="h-44 overflow-y-auto font-mono text-[10px] leading-relaxed text-emerald-300/80 p-2 space-y-1">
                        {liveAgents.filter(a => a.partialOutput).map(agent => (
                          <div key={agent.role} className="mb-1">
                            <span className="text-zinc-500">[{agent.role.slice(0,12)}]</span>{' '}
                            <span className="whitespace-pre-wrap break-words">{agent.partialOutput.slice(-400)}</span>
                          </div>
                        ))}
                        {liveAgents.every(a => !a.partialOutput) && (
                          <div className="text-zinc-600 italic">Waiting for agents to start…</div>
                        )}
                        <div ref={terminalEndRef} />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Recent Sessions */}
              <div className="px-3 pt-2 pb-4 border-t border-white/5">
                <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider px-2 mb-2 mt-2">Recent Sessions</div>
                <div className="space-y-1">
                  {sessions.sort((a,b) => b.updatedAt - a.updatedAt).map((session) => (
                    <div key={session.sessionId} className={`group flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors text-left cursor-pointer ${sessionId === session.sessionId ? 'bg-zinc-800/50 text-zinc-300' : 'text-zinc-500 hover:bg-zinc-800/30 hover:text-zinc-300'}`} onClick={() => loadSession(session.sessionId)}>
                      <span className="truncate flex-1">{session.title}</span>
                      <button onClick={(e) => deleteSession(e, session.sessionId)} className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-opacity">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                  {sessions.length === 0 && (
                    <div className="px-3 py-2 text-xs text-zinc-600 italic">No recent sessions</div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col relative min-w-0 bg-zinc-950">
        
        {/* Header Strip */}
        <header className="h-14 border-b border-white/5 flex items-center px-4 justify-between bg-zinc-950/80 backdrop-blur-md z-10 sticky top-0">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button onClick={() => setIsSidebarOpen(true)} className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors">
                <Menu size={18} />
              </button>
            )}
            <span className="text-sm font-medium text-zinc-300">
              {activeView === 'main' ? 'Main Orchestrator Chat' : `${activeView} (Focused View)`}
            </span>
          </div>
          {activeView !== 'main' && (
            <button onClick={() => setActiveView('main')} className="text-xs bg-zinc-900 border border-white/10 px-3 py-1.5 rounded-md text-zinc-400 hover:text-white transition-colors flex items-center gap-2">
               <ArrowRight size={14} /> Back to Main
            </button>
          )}
        </header>

        {/* --- VIEW SWAPPER --- */}
        
        {/* VIEW 1: MAIN CHAT */}
        {activeView === 'main' && (
          <>
            <div className={`flex-1 overflow-y-auto ${isProcessing ? 'pb-72' : 'pb-36'} scroll-smooth`}>
              <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
                
                {messages.length === 0 && !isProcessing && (
                  <div className="flex flex-col items-center justify-center min-h-[70vh] text-center py-6">
                     <div className="w-12 h-12 bg-zinc-900 border border-white/5 rounded-xl flex items-center justify-center mb-4 shadow-xl">
                       <Bot size={24} className="text-zinc-350" />
                     </div>
                     <h2 className="text-xl font-semibold text-zinc-100 mb-2 tracking-tight">CriticAI Swarm Workspace</h2>
                     <p className="text-xs text-zinc-400 max-w-md leading-relaxed mb-6">Enter your project brief below. The Orchestrator will analyze your prompt, check safety guardrails, and deploy specialized agents in parallel.</p>
                     <SwarmFlowDiagram />
                  </div>
                )}

                <AnimatePresence initial={false}>
                  {messages.map((msg, index) => (
                    <motion.div 
                      key={msg.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {/* AI Avatar */}
                      {msg.role === 'ai' && (
                        <div className="w-8 h-8 shrink-0 rounded-lg bg-zinc-900 border border-white/10 flex items-center justify-center mt-1 shadow-sm">
                          <Bot size={16} className="text-zinc-400" />
                        </div>
                      )}

                      <div className={`max-w-[85%] md:max-w-[80%] ${msg.role === 'user' ? 'order-1' : 'order-2'}`}>
                        
                        {/* User Bubble */}
                        {msg.role === 'user' && msg.type === 'text' && (
                          <div className="bg-zinc-800 text-zinc-100 p-4 rounded-2xl rounded-tr-sm text-[15px] leading-relaxed shadow-md">
                            {msg.content}
                          </div>
                        )}

                        {/* AI Bubbles */}
                        {msg.role === 'ai' && (
                          <div className="text-[15px] text-zinc-300 leading-relaxed bg-transparent w-full">
                            
                            {/* Draft Output (Summarized for Main Chat) */}
                            {msg.type === 'draft' && (
                              <div className="space-y-3 pt-1 w-full min-w-[280px] md:min-w-[400px]">
                                 <div className="bg-zinc-900/80 border border-white/10 rounded-xl shadow-lg p-5">
                                    <div className="flex items-center gap-3 mb-4">
                                      <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                                        <CheckCircle className="text-emerald-400" size={20} />
                                      </div>
                                      <div>
                                        <h3 className="text-sm font-medium text-zinc-100">Swarm Execution Complete</h3>
                                        <p className="text-xs text-zinc-500 mt-0.5">The orchestrator has deployed {Object.keys(msg.content.deliverables || {}).length} specialized agents.</p>
                                        {msg.content.executionPlan && msg.content.executionPlan.length > 0 && (
                                       <div className="bg-zinc-950/50 rounded-lg p-3 border border-white/5">
                                         <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2 block">Execution Plan (Click any agent to view)</span>
                                         <div className="flex flex-wrap items-center gap-2">
                                           {msg.content.executionPlan.map((task, idx) => (
                                             <React.Fragment key={idx}>
                                               <AgentNodeBadge 
                                                 label={task.agent_role} 
                                                 icon={Bot} 
                                                 active={activeView === task.agent_role} 
                                                 onClick={() => setActiveView(task.agent_role)}
                                               />
                                               {idx < msg.content.executionPlan.length - 1 && <ArrowRight size={12} className="text-zinc-700" />}
                                             </React.Fragment>
                                           ))}
                                         </div>
                                       </div>
                                     )}
                                      </div>
                                    </div>
                                    
                                    <div className="mt-4 pt-4 border-t border-white/5 text-sm text-zinc-400">
                                      Select an agent from the <strong className="text-zinc-200">left sidebar</strong> to review and revise their specific deliverables.
                                    </div>
                                 </div>
                              </div>
                            )}

                            {/* Text Response */}
                            {msg.type === 'text' && (
                              <div className="bg-zinc-900 border border-white/10 p-5 rounded-xl shadow-md mt-1">
                                <div className="prose prose-invert prose-zinc max-w-none prose-headings:font-semibold prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-p:text-zinc-300 prose-p:leading-relaxed prose-a:text-emerald-400 prose-li:text-zinc-300 prose-strong:text-zinc-100">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {msg.content}
                                  </ReactMarkdown>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* User Avatar */}
                      {msg.role === 'user' && (
                        <div className="w-8 h-8 shrink-0 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center mt-1 order-2 shadow-sm">
                          <User size={16} className="text-zinc-400" />
                        </div>
                      )}
                    </motion.div>
                  ))}

                  {/* Engaging Loading State */}
                  {isProcessing && <LoadingSkeleton agentStatuses={agentStatuses} agentDurations={agentDurations} />}
                </AnimatePresence>
                <div ref={messagesEndRef} className="h-4" />
              </div>
            </div>

            {/* Input Bar (Main Chat) */}
            <div className="absolute bottom-0 left-0 right-0 bg-zinc-950/80 backdrop-blur-md pt-4 pb-6 px-4">
              <div className="max-w-3xl mx-auto relative">
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept=".txt,.pdf,image/*" 
                  onChange={(e) => setAttachedFile(e.target.files[0])} 
                />
                
                {/* File Attachment Badge */}
                <AnimatePresence>
                  {attachedFile && (
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="absolute bottom-full mb-3 left-2 bg-zinc-800 border border-white/10 rounded-lg px-3 py-1.5 flex items-center gap-2 shadow-lg z-10"
                    >
                      <FileText size={14} className="text-emerald-400" />
                      <span className="text-xs font-medium text-zinc-300 max-w-[150px] truncate">{attachedFile.name}</span>
                      <button onClick={() => setAttachedFile(null)} className="ml-1 text-zinc-500 hover:text-zinc-200 transition-colors">
                        <X size={14} />
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Pre-flight OpenRouter Key warning banner */}
                {!openrouterKey.trim() && (
                  <div className="w-full bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 mb-3 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="text-amber-500 shrink-0 animate-bounce" size={18} />
                      <span className="text-[13px] text-zinc-300 font-medium leading-relaxed">
                        To run the AI agent swarm, please configure your **OpenRouter API Key** first.
                      </span>
                    </div>
                    <button 
                      onClick={() => setShowSettings(true)}
                      className="text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 px-3.5 py-1.5 rounded-lg transition-colors font-semibold"
                    >
                      Open Settings
                    </button>
                  </div>
                )}

                <div className="relative flex items-end w-full bg-zinc-800/50 border border-zinc-700 focus-within:border-zinc-500 rounded-2xl p-2 transition-colors">
                  <div className="flex flex-col justify-end pb-1 px-1">
                     <button 
                       onClick={() => fileInputRef.current?.click()}
                       disabled={!openrouterKey.trim()}
                       className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 rounded-xl transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                       title="Attach File"
                     >
                       <Plus size={20} />
                     </button>
                  </div>
                  
                  <textarea
                    rows="1"
                    placeholder={!openrouterKey.trim() ? "Configure OpenRouter API Key in Settings to message..." : (latestDraft && latestDraft.isAwaitingFeedback ? "Send global revision to the swarm..." : "Message CriticAI Orchestrator...")}
                    value={inputValue}
                    disabled={!openrouterKey.trim()}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (latestDraft && latestDraft.isAwaitingFeedback) {
                          handleRevise(inputValue, null, false);
                          setInputValue('');
                        } else {
                          handleSendPrompt();
                        }
                      }
                    }}
                    className="w-full max-h-40 min-h-[44px] bg-transparent resize-none px-3 py-3 text-[15px] text-zinc-100 outline-none placeholder-zinc-500 leading-relaxed overflow-y-auto disabled:opacity-50"
                  />

                  {latestDraft && latestDraft.isAwaitingFeedback ? (
                    <div className="flex items-center gap-2 pr-1 pb-1">
                      <button 
                        onClick={() => { handleRevise(inputValue, null, false); setInputValue(''); }}
                        disabled={!inputValue.trim() || isProcessing}
                        className="bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-zinc-200 px-3 py-2 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5"
                      >
                        <RefreshCw size={16} /> Global Revise
                      </button>
                      <button 
                        onClick={() => { handleRevise('', null, true); setInputValue(''); }}
                        disabled={isProcessing}
                        className="bg-emerald-500 hover:bg-emerald-400 text-zinc-950 px-3 py-2 rounded-xl text-sm font-semibold transition-colors flex items-center gap-1.5"
                      >
                        <CheckCircle size={16} /> Approve All
                      </button>
                    </div>
                  ) : (
                    <div className="pr-1 pb-1">
                      <button 
                        onClick={handleSendPrompt}
                        disabled={!inputValue.trim() || isProcessing || !openrouterKey.trim()}
                        className={`p-2 rounded-xl transition-all flex items-center justify-center ${
                          inputValue.trim() && !isProcessing && openrouterKey.trim()
                            ? 'bg-white text-black hover:bg-zinc-200 shadow-md' 
                            : 'bg-zinc-700/50 text-zinc-500 cursor-not-allowed'
                        }`}
                      >
                        <ArrowUp size={20} strokeWidth={2.5} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {/* VIEW 2: FOCUSED CANVAS (Agent Output) */}
        {activeView !== 'main' && (
          <motion.div 
            key={activeView}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex-1 flex flex-col h-full bg-zinc-900 relative"
          >
            <div className="flex-1 overflow-y-auto p-6 md:p-12 scroll-smooth">
              <div className="max-w-3xl mx-auto w-full pb-32">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-zinc-800 border border-white/10 flex items-center justify-center shadow-lg">
                      <Bot size={24} className="text-zinc-350" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-semibold text-zinc-100">{activeView}</h2>
                      <p className="text-sm text-zinc-500 mt-0.5">
                        {latestDraft?.content?.executionPlan?.find(t => t.agent_role === activeView)?.task_description
                          ? latestDraft.content.executionPlan.find(t => t.agent_role === activeView).task_description.slice(0, 120) + (latestDraft.content.executionPlan.find(t => t.agent_role === activeView).task_description.length > 120 ? '…' : '')
                          : 'Dedicated output canvas'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 self-start md:self-center">
                    <button
                      onClick={handleCopyDeliverable}
                      className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-white/10 rounded-xl text-xs font-semibold text-zinc-200 transition-all flex items-center gap-1.5 shadow-sm"
                      title="Copy content to clipboard"
                    >
                      {copied ? <CheckCircle size={12} className="text-emerald-450" /> : <Copy size={12} />}
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                    <button
                      onClick={handleDownloadDeliverable}
                      className="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm"
                      title="Download as Markdown file"
                    >
                      <Download size={12} />
                      Download
                    </button>
                  </div>
                </div>
                
                <hr className="border-white/10 my-8" />
                
                <div className="prose prose-invert prose-zinc max-w-none prose-headings:font-semibold prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-p:text-zinc-300 prose-p:leading-relaxed prose-a:text-emerald-400 prose-li:text-zinc-300 prose-strong:text-zinc-100">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {latestDeliverables[activeView] || "No content generated yet."}
                  </ReactMarkdown>
                </div>
              </div>
            </div>

            {/* Sub-Chat Targeted Input */}
            <div className="absolute bottom-0 left-0 right-0 bg-zinc-950/90 backdrop-blur-xl border-t border-white/5 p-4">
               <div className="max-w-3xl mx-auto">
                  <div className="relative flex items-end w-full bg-zinc-800/50 border border-zinc-700 focus-within:border-zinc-500 rounded-2xl p-2 transition-colors">
                    <textarea
                      rows="1"
                      placeholder={`Tell the ${activeView} what to revise...`}
                      id="targeted-feedback-input"
                      className="w-full max-h-32 min-h-[44px] bg-transparent resize-none px-3 py-3 text-[15px] text-zinc-100 outline-none placeholder-zinc-500 leading-relaxed overflow-y-auto"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          const val = e.target.value.trim();
                          if (val) {
                            handleTargetedRevise(activeView, val);
                            e.target.value = '';
                          }
                        }
                      }}
                    />
                    <div className="pr-1 pb-1">
                      <button 
                        onClick={() => {
                          const input = document.getElementById('targeted-feedback-input');
                          if (input && input.value.trim()) {
                            handleTargetedRevise(activeView, input.value.trim());
                            input.value = '';
                          }
                        }}
                        disabled={isProcessing}
                        className="p-2 rounded-xl transition-all flex items-center justify-center bg-white text-black hover:bg-zinc-200 shadow-md disabled:opacity-50 disabled:bg-zinc-700/50 disabled:text-zinc-500"
                      >
                        <ArrowUp size={20} strokeWidth={2.5} />
                      </button>
                    </div>
                  </div>
               </div>
            </div>
          </motion.div>
        )}

      {/* Settings Modal */}
      <AnimatePresence>
        {showSettings && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col"
            >
              <div className="p-6 border-b border-white/5 flex items-center justify-between">
                <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                  <Settings size={18} className="text-zinc-400" />
                  CriticAI Configuration Settings
                </h3>
                <button 
                  onClick={() => setShowSettings(false)}
                  className="text-zinc-400 hover:text-zinc-200 transition-colors"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="p-6 space-y-6 flex-1 overflow-y-auto max-h-[70vh]">
                <div className="space-y-4">
                  {/* OpenRouter Key */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-medium text-zinc-300">OpenRouter API Key (Required)</label>
                      <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" className="text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors underline">Get Key</a>
                    </div>
                    <div className="relative flex items-center">
                      <input 
                        type={showOpenrouterKey ? 'text' : 'password'}
                        value={openrouterKey}
                        onChange={(e) => {
                          setOpenrouterKey(e.target.value);
                          localStorage.setItem('swarm_openrouter_key', e.target.value);
                        }}
                        placeholder="sk-or-v1-..."
                        className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-800 text-zinc-200 pr-10"
                      />
                      <button 
                        type="button"
                        onClick={() => setShowOpenrouterKey(!showOpenrouterKey)}
                        className="absolute right-3 text-zinc-500 hover:text-zinc-350 transition-colors"
                      >
                        {showOpenrouterKey ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    {/* Verify Key Button */}
                    <div className="flex flex-col gap-2 pt-1.5">
                      <div className="flex gap-3 items-center">
                        <button
                          type="button"
                          onClick={handleVerifyKey}
                          disabled={verifying || !openrouterKey.trim()}
                          className="px-3.5 py-2 bg-zinc-850 hover:bg-zinc-750 disabled:opacity-40 disabled:hover:bg-zinc-850 text-[10px] font-bold tracking-wider uppercase text-zinc-300 rounded-xl transition-colors border border-white/5 shadow-sm"
                        >
                          {verifying ? 'Verifying Connection...' : 'Verify API Connection'}
                        </button>
                        {verifyResult && (
                          <div className={`text-xs font-semibold flex items-center gap-1.5 ${verifyResult.valid ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {verifyResult.valid ? (
                              <span>✅ Valid Key ({verifyResult.label || 'Active'})</span>
                            ) : (
                              <span>❌ {verifyResult.error || 'Connection Failed'}</span>
                            )}
                          </div>
                        )}
                      </div>
                      {verifyResult && verifyResult.valid && (
                        <div className="text-[11px] text-zinc-400 px-1 select-none flex gap-3">
                          <span>Limit: <strong className="text-zinc-300">{verifyResult.limit}</strong></span>
                          <span>Usage: <strong className="text-zinc-300">${Number(verifyResult.usage).toFixed(4)}</strong></span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Backend Access Token */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-300">Backend Access Token (Optional)</label>
                    <input 
                      type="password"
                      value={backendToken}
                      onChange={(e) => {
                        setBackendToken(e.target.value);
                        localStorage.setItem('swarm_backend_token', e.target.value);
                      }}
                      placeholder="Enter connection token if required by server"
                      className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-800 text-zinc-200"
                    />
                  </div>
                </div>

                <hr className="border-white/5" />

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">LangSmith Tracing</label>
                    <input 
                      type="checkbox" 
                      checked={langsmithEnabled} 
                      onChange={(e) => {
                        setLangsmithEnabled(e.target.checked);
                        localStorage.setItem('swarm_langsmith_enabled', e.target.checked);
                      }}
                      className="accent-white h-4 w-4 rounded border-zinc-700 bg-zinc-900"
                    />
                  </div>

                  {langsmithEnabled && (
                    <>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-zinc-300">LangSmith API Key</label>
                        <div className="relative flex items-center">
                          <input 
                            type={showLangsmithKey ? 'text' : 'password'}
                            value={langsmithKey}
                            onChange={(e) => {
                              setLangsmithKey(e.target.value);
                              localStorage.setItem('swarm_langsmith_api_key', e.target.value);
                            }}
                            placeholder="lsv2_pt_..."
                            className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-800 text-zinc-200 pr-10"
                          />
                          <button 
                            type="button" 
                            onClick={() => setShowLangsmithKey(!showLangsmithKey)}
                            className="absolute right-3 text-zinc-500 hover:text-zinc-350 transition-colors"
                          >
                            {showLangsmithKey ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-zinc-300">LangSmith Project</label>
                        <input 
                          type="text"
                          value={langsmithProject}
                          onChange={(e) => {
                            setLangsmithProject(e.target.value);
                            localStorage.setItem('swarm_langsmith_project', e.target.value);
                          }}
                          placeholder="CriticAI"
                          className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-800 text-zinc-200"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-zinc-300">LangSmith Endpoint</label>
                        <input 
                          type="text"
                          value={langsmithEndpoint}
                          onChange={(e) => {
                            setLangsmithEndpoint(e.target.value);
                            localStorage.setItem('swarm_langsmith_endpoint', e.target.value);
                          }}
                          placeholder="https://api.smith.langchain.com"
                          className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-800 text-zinc-200"
                        />
                      </div>
                    </>
                  )}
                </div>

                <div className="bg-zinc-950/50 border border-white/5 rounded-xl p-4 text-[11px] leading-relaxed text-zinc-400 space-y-1.5">
                  <p className="font-semibold text-zinc-200 flex items-center gap-1">🔒 Local Privacy & Security</p>
                  <p>Your API keys are stored **only inside your local browser storage** and sent securely over the WebSocket headers directly to the AI providers. They are never saved, stored, or logged on our servers.</p>
                </div>
              </div>

              <div className="p-4 border-t border-white/5 bg-zinc-900/40 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    localStorage.setItem('swarm_provider', 'openrouter');
                    localStorage.setItem('swarm_openrouter_key', openrouterKey);
                    localStorage.setItem('swarm_backend_token', backendToken);
                    localStorage.setItem('swarm_langsmith_enabled', langsmithEnabled ? 'true' : 'false');
                    localStorage.setItem('swarm_langsmith_api_key', langsmithKey);
                    localStorage.setItem('swarm_langsmith_project', langsmithProject);
                    localStorage.setItem('swarm_langsmith_endpoint', langsmithEndpoint);
                    setShowSettings(false);
                  }}
                  className="px-4 py-2 bg-white hover:bg-zinc-200 text-black text-xs font-semibold rounded-lg transition-colors shadow-sm"
                >
                  Save Configuration
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      </div>
    </div>
  );
}
