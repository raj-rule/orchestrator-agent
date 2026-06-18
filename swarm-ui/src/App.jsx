import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, PenTool, Image as ImageIcon, ArrowUp, Paperclip, Bot, User, CheckCircle, RefreshCw, ArrowRight, Plus, Menu, X, MessageSquare, Trash2, Terminal, Code, Activity, Briefcase, FileText, Settings, Eye, EyeOff } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const LoadingSkeleton = ({ agentStatuses = {} }) => {
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
                <span className={`text-[10px] uppercase tracking-tighter font-bold ${
                  status === 'working' ? 'text-amber-400 animate-pulse' : 'text-emerald-500'
                }`}>
                  {status === 'working' ? 'Processing...' : 'Done'}
                </span>
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

export default function App() {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
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
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [agentStatuses, setAgentStatuses] = useState({});

  // LLM Key states
  const [provider, setProvider] = useState(() => localStorage.getItem('swarm_provider') || 'groq');
  const [groqKey, setGroqKey] = useState(() => localStorage.getItem('swarm_groq_key') || '');
  const [geminiKey, setGeminiKey] = useState(() => localStorage.getItem('swarm_gemini_key') || '');
  const [openrouterKey, setOpenrouterKey] = useState(() => localStorage.getItem('swarm_openrouter_key') || '');

  // Visibility toggles for keys
  const [showGroqKey, setShowGroqKey] = useState(false);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [showOpenrouterKey, setShowOpenrouterKey] = useState(false);
  
  // Workspace State
  const [activeView, setActiveView] = useState('main'); // 'main' or agentRole string
  const [attachedFile, setAttachedFile] = useState(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll main chat
  useEffect(() => {
    if (activeView === 'main') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeView]);

  // Session Recovery on Mount
  useEffect(() => {
    const lastSessionId = localStorage.getItem('swarm_last_session_id');
    if (lastSessionId) {
      loadSession(lastSessionId);
    }
  }, []);

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
    if (isProcessing) return;
    setSessionId(id);
    setActiveView('main');
    try {
      const savedChat = localStorage.getItem(`swarm_chat_${id}`);
      const loaded = savedChat ? JSON.parse(savedChat) : [];
      setMessages(loaded);
      
      // Attempt to sync with backend
      const response = await fetch(`http://localhost:8000/api/sessions/${id}`);
      if (response.ok) {
        const data = await response.json();
        if (data.agent_statuses) setAgentStatuses(data.agent_statuses);
      }
    } catch (err) {
      console.warn("Session sync failed:", err);
    }
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const startNewChat = () => {
    if (isProcessing) return;
    setSessionId(crypto.randomUUID());
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

  const startCampaign = async (promptText) => {
    setIsProcessing(true);
    setActiveView('main');
    
    try {
      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('task_prompt', promptText);
      if (guidelinesPath) formData.append('guidelines_path', guidelinesPath);
      if (attachedFile) formData.append('file', attachedFile);

      const response = await fetch('http://localhost:8000/api/start', {
        method: 'POST',
        body: formData,
        headers: {
          'X-LLM-Provider': provider,
          'X-Groq-API-Key': groqKey,
          'X-Gemini-API-Key': geminiKey,
          'X-OpenRouter-API-Key': openrouterKey,
        }
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();
      const parsedData = typeof data === 'string' ? JSON.parse(data) : data;

      if (parsedData.agent_statuses) setAgentStatuses(parsedData.agent_statuses);

      const newDeliverables = parsedData?.deliverables;
      const deliverables = newDeliverables && Object.keys(newDeliverables).length > 0 ? newDeliverables : (latestDeliverables || {});
      const executionPlan = parsedData?.execution_plan || [];

      setMessages(prev => [
        ...prev, 
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'draft',
          content: { deliverables, executionPlan },
          isAwaitingFeedback: true,
          isFinal: false
        }
      ]);
    } catch (error) {
      setMessages(prev => [
        ...prev, 
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'text',
          content: `System Error: Unable to connect to the Swarm backend. (${error.message})`
        }
      ]);
    } finally {
      setIsProcessing(false);
    }
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
    
    if (messages.length === 0) {
      startCampaign(userPrompt);
    } else {
      handleRevise(userPrompt);
    }
    
    if (attachedFile) setAttachedFile(null);
  };

  const handleRevise = async (feedbackText, targetAgent = null, isApproved = false) => {
    if (isProcessing) return;
    
    // Mark previous drafts as no longer awaiting feedback
    setMessages(prev => prev.map(msg => 
      msg.type === 'draft' ? { ...msg, isAwaitingFeedback: false, isFinal: isApproved } : msg
    ));

    const userMsg = { 
      id: crypto.randomUUID(), 
      role: 'user', 
      type: 'text',
      content: isApproved ? 'Approve and finalize.' : (targetAgent ? `Targeted Revision to ${targetAgent}: ${feedbackText}` : `Global Revision: ${feedbackText}`) 
    };
    setMessages(prev => [...prev, userMsg]);

    if (isApproved) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'ai',
        type: 'text',
        content: "Campaign finalized successfully! All assets have been exported."
      }]);
      setActiveView('main');
      return;
    }

    setIsProcessing(true);
    setActiveView('main');

    try {
      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('feedback', feedbackText);
      formData.append('type', targetAgent ? 'targeted' : 'global');
      if (targetAgent) formData.append('target_agent', targetAgent);
      if (attachedFile) formData.append('file', attachedFile);

      const response = await fetch('http://localhost:8000/api/feedback', {
        method: 'POST',
        body: formData,
        headers: {
          'X-LLM-Provider': provider,
          'X-Groq-API-Key': groqKey,
          'X-Gemini-API-Key': geminiKey,
          'X-OpenRouter-API-Key': openrouterKey,
        }
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();
      const parsedData = typeof data === 'string' ? JSON.parse(data) : data;

      if (parsedData.agent_statuses) setAgentStatuses(parsedData.agent_statuses);

      const newDeliverables = parsedData?.deliverables;
      const deliverables = newDeliverables && Object.keys(newDeliverables).length > 0 ? newDeliverables : (latestDeliverables || {});
      const executionPlan = parsedData?.execution_plan || [];

      setMessages(prev => [
        ...prev, 
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'draft',
          content: { deliverables, executionPlan },
          isAwaitingFeedback: true,
          isFinal: false
        }
      ]);
    } catch (error) {
      setMessages(prev => [
        ...prev, 
        {
          id: crypto.randomUUID(),
          role: 'ai',
          type: 'text',
          content: `System Error: Unable to process revision. (${error.message})`
        }
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTargetedRevise = (agentRole, feedbackText) => {
    if (isProcessing || !feedbackText.trim()) return;
    handleRevise(feedbackText, agentRole, false);
  };

  const AgentNodeBadge = ({ label, icon: Icon, active, pulse }) => (
    <span className={`px-3 py-1.5 text-xs rounded-full border flex items-center gap-2 transition-all duration-300 ${active ? 'border-zinc-600 bg-zinc-800 text-zinc-100' : 'border-zinc-800 bg-zinc-900/50 text-zinc-500'}`}>
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
            <div className="flex-1 overflow-y-auto pb-36 scroll-smooth">
              <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
                
                {messages.length === 0 && !isProcessing && (
                  <div className="flex flex-col items-center justify-center h-[60vh] text-center">
                     <div className="w-16 h-16 bg-zinc-900 border border-white/5 rounded-2xl flex items-center justify-center mb-6 shadow-2xl">
                       <Bot size={32} className="text-zinc-400" />
                     </div>
                     <h2 className="text-2xl font-semibold text-zinc-100 mb-3 tracking-tight">AI Swarm Workspace</h2>
                     <p className="text-sm text-zinc-400 max-w-md leading-relaxed">Enter your project brief below. The Orchestrator will decompose the task and spawn specialized agents to execute it in parallel.</p>
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
                                      </div>
                                    </div>
                                    
                                    {msg.content.executionPlan && msg.content.executionPlan.length > 0 && (
                                      <div className="bg-zinc-950/50 rounded-lg p-3 border border-white/5">
                                        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2 block">Execution Plan</span>
                                        <div className="flex flex-wrap items-center gap-2">
                                          {msg.content.executionPlan.map((task, idx) => (
                                            <React.Fragment key={idx}>
                                              <AgentNodeBadge label={task.agent_role} icon={Bot} active={false} />
                                              {idx < msg.content.executionPlan.length - 1 && <ArrowRight size={12} className="text-zinc-700" />}
                                            </React.Fragment>
                                          ))}
                                        </div>
                                      </div>
                                    )}

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
                  {isProcessing && <LoadingSkeleton agentStatuses={agentStatuses} />}
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

                <div className="relative flex items-end w-full bg-zinc-800/50 border border-zinc-700 focus-within:border-zinc-500 rounded-2xl p-2 transition-colors">
                  <div className="flex flex-col justify-end pb-1 px-1">
                     <button 
                       onClick={() => fileInputRef.current?.click()}
                       className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 rounded-xl transition-all"
                       title="Attach File"
                     >
                       <Plus size={20} />
                     </button>
                  </div>
                  
                  <textarea
                    rows="1"
                    placeholder={latestDraft && latestDraft.isAwaitingFeedback ? "Send global revision to the swarm..." : "Message CriticAI Orchestrator..."}
                    value={inputValue}
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
                    className="w-full max-h-40 min-h-[44px] bg-transparent resize-none px-3 py-3 text-[15px] text-zinc-100 outline-none placeholder-zinc-500 leading-relaxed overflow-y-auto"
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
                        disabled={!inputValue.trim() || isProcessing}
                        className={`p-2 rounded-xl transition-all flex items-center justify-center ${
                          inputValue.trim() && !isProcessing
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
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-zinc-800 border border-white/10 flex items-center justify-center shadow-lg">
                    <Bot size={24} className="text-zinc-300" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-semibold text-zinc-100">{activeView}</h2>
                    <p className="text-sm text-zinc-500 mt-0.5">Dedicated output canvas</p>
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
                  LLM Provider Settings
                </h3>
                <button 
                  onClick={() => setShowSettings(false)}
                  className="text-zinc-400 hover:text-zinc-200 transition-colors"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="p-6 space-y-6 flex-1 overflow-y-auto max-h-[70vh]">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Default LLM Provider</label>
                  <div className="grid grid-cols-3 gap-3">
                    {['groq', 'gemini', 'openrouter'].map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setProvider(p)}
                        className={`px-4 py-3 rounded-xl border text-xs font-medium uppercase tracking-wider transition-all ${
                          provider === p 
                            ? 'bg-white text-black border-white shadow-md' 
                            : 'bg-zinc-950 border-white/5 text-zinc-400 hover:text-zinc-200 hover:border-white/10'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                <hr className="border-white/5" />

                <div className="space-y-4">
                  {/* Groq Key */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-medium text-zinc-300">Groq API Key</label>
                      <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer" className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors underline">Get Key</a>
                    </div>
                    <div className="relative flex items-center">
                      <input 
                        type={showGroqKey ? 'text' : 'password'}
                        value={groqKey}
                        onChange={(e) => {
                          setGroqKey(e.target.value);
                          localStorage.setItem('swarm_groq_key', e.target.value);
                        }}
                        placeholder="gsk_..."
                        className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-700 text-zinc-200 pr-10"
                      />
                      <button 
                        type="button"
                        onClick={() => setShowGroqKey(!showGroqKey)}
                        className="absolute right-3 text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        {showGroqKey ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Gemini Key */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-medium text-zinc-300">Gemini API Key</label>
                      <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors underline">Get Key</a>
                    </div>
                    <div className="relative flex items-center">
                      <input 
                        type={showGeminiKey ? 'text' : 'password'}
                        value={geminiKey}
                        onChange={(e) => {
                          setGeminiKey(e.target.value);
                          localStorage.setItem('swarm_gemini_key', e.target.value);
                        }}
                        placeholder="AIzaSy..."
                        className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-700 text-zinc-200 pr-10"
                      />
                      <button 
                        type="button"
                        onClick={() => setShowGeminiKey(!showGeminiKey)}
                        className="absolute right-3 text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        {showGeminiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* OpenRouter Key */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-medium text-zinc-300">OpenRouter API Key</label>
                      <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors underline">Get Key</a>
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
                        className="w-full bg-zinc-950 border border-white/5 focus:border-zinc-500 rounded-xl px-4 py-2.5 text-sm outline-none placeholder-zinc-700 text-zinc-200 pr-10"
                      />
                      <button 
                        type="button"
                        onClick={() => setShowOpenrouterKey(!showOpenrouterKey)}
                        className="absolute right-3 text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        {showOpenrouterKey ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="bg-zinc-950/50 border border-white/5 rounded-xl p-4 text-[11px] leading-relaxed text-zinc-400 space-y-1">
                  <p className="font-semibold text-zinc-300">🔒 Secure Local Storage</p>
                  <p>Your API keys are stored only in your browser's LocalStorage and are sent to the local server running at `localhost:8000` via headers. They never touch any remote database.</p>
                </div>
              </div>

              <div className="p-4 border-t border-white/5 bg-zinc-900/40 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    localStorage.setItem('swarm_provider', provider);
                    setShowSettings(false);
                  }}
                  className="px-4 py-2 bg-white hover:bg-zinc-200 text-black text-xs font-semibold rounded-lg transition-colors shadow-sm"
                >
                  Save Settings
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
