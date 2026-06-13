import React, { useState, useEffect, useRef } from 'react';
import './AionStyles.css';

const highlightPython = (code) => {
  if (!code) return "";
  let escaped = code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  
  const regex = /(#.*$)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|\b(def|class|async|await|import|from|if|else|elif|for|while|return|as|in|is|not|with|try|except|finally|raise|lambda|yield|global|nonlocal|pass|break|continue|assert|del)\b|\b(True|False|None|self|super|__name__|__main__|__init__)\b|\b([a-zA-Z_]\w*)(?=\s*\()/gm;
  
  return escaped.replace(regex, (match, comment, string, keyword, constant, func) => {
    if (comment) return `<span class="sh-c">${comment}</span>`;
    if (string) return `<span class="sh-s">${string}</span>`;
    if (keyword) return `<span class="sh-k">${keyword}</span>`;
    if (constant) return `<span class="sh-c">${constant}</span>`;
    if (func) return `<span class="sh-f">${func}</span>`;
    return match;
  });
};

const StatBox = ({ title, value, type = '' }) => (
  <div className={`stat-box ${type}`}>
    <h3>{title}</h3>
    <p>{value}</p>
  </div>
);

const Toast = ({ message, type, onRemove }) => {
  useEffect(() => {
    const timer = setTimeout(onRemove, 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className={`toast ${type}`}>
      <span>{type === 'warning' ? '⚠️' : '✅'}</span>
      {message}
    </div>
  );
};

const SUPPORTED_LANGUAGES = [
  "Auto (Detect)", "Python", "JavaScript", "TypeScript", "Java",
  "C++", "C", "Go", "Rust", "Ruby", "Kotlin", "Swift", "C#",
  "PHP", "HTML", "CSS", "SQL", "Bash"
];

const LANG_KEYS = {
  "Auto (Detect)": "auto", "Python": "python", "JavaScript": "javascript",
  "TypeScript": "typescript", "Java": "java", "C++": "cpp", "C": "c",
  "Go": "go", "Rust": "rust", "Ruby": "ruby", "Kotlin": "kotlin",
  "Swift": "swift", "C#": "csharp", "PHP": "php", "HTML": "html",
  "CSS": "css", "SQL": "sql", "Bash": "bash"
};

function App() {
  const [activeTab, setActiveTab] = useState('optimizer');
  const [taskType, setTaskType] = useState('efficiency-boost');
  const [selectedLanguage, setSelectedLanguage] = useState('Auto (Detect)');
  const [inputCode, setInputCode] = useState('def process_data(data):\n    import sys\n    results = []\n    for item in data:\n        for other_item in data:\n            if item == other_item:\n                results.append(item)\n    return results');
  const [outputCode, setOutputCode] = useState('');
  const [insight, setInsight] = useState('');
  
  const [initialScore, setInitialScore] = useState('-');
  const [optimizedScore, setOptimizedScore] = useState('-');
  const [speedup, setSpeedup] = useState('-');
  const [memorySaved, setMemorySaved] = useState('-');
  
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [toasts, setToasts] = useState([]);
  
  const [benchmarkTask, setBenchmarkTask] = useState('style-cleanup');
  const [benchmarkResult, setBenchmarkResult] = useState(null);
  const [isBenchmarking, setIsBenchmarking] = useState(false);

  const addToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const handleCopy = () => {
    if (!outputCode) return;
    navigator.clipboard.writeText(outputCode);
    addToast("Copied to clipboard!");
  };

  const handleRunBenchmark = async () => {
    setIsBenchmarking(true);
    setBenchmarkResult(null);
    try {
      const response = await fetch('/run_benchmark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: benchmarkTask })
      });
      if (!response.ok) throw new Error('Benchmark API Error');
      const data = await response.json();
      setBenchmarkResult(data);
      addToast("Benchmark Run Successful!");
    } catch (error) {
      addToast("Benchmark Failed. Is the server running?", "warning");
    } finally {
      setIsBenchmarking(false);
    }
  };

  const handleOptimize = async (full = false) => {
    if (!inputCode.trim()) {
      addToast('Please enter some code', 'warning');
      return;
    }
    
    setIsOptimizing(true);
    const endpoint = full ? '/optimize_full' : '/optimize';
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: inputCode, task_type: taskType, language: LANG_KEYS[selectedLanguage] || "auto" })
      });
      
      if (!response.ok) throw new Error('API Error');
      
      const data = await response.json();
      
      if (data.fixed_code) {
        setOutputCode(data.fixed_code);
        setInsight(data.recommendation || (full ? '[Full Pass] Optimization complete.' : `[${taskType}] Optimization complete.`));
        
        setInitialScore((data.initial_score).toFixed(2));
        setOptimizedScore((data.final_score).toFixed(2));
        setSpeedup(data.perf_gain || '+0.0%');
        setMemorySaved(data.mem_reduction || '-0.0MB');
        
        addToast("Optimization Successful");
      }
    } catch (error) {
      addToast("Optimization Failed. Is the server running?", "warning");
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="gradio-container">
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <div className="badge">Powered by RL & AST Evaluation</div>
        <h1>Aion Code Reviewer</h1>
        <p className="subtitle">
          An intelligent code optimization engine that detects style, efficiency, and security flaws, rewriting them dynamically.
        </p>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <div className="tabs-header">
          <button 
            className={`tab-btn ${activeTab === 'optimizer' ? 'active' : ''}`}
            onClick={() => setActiveTab('optimizer')}
          >
            ✨ Live Optimizer
          </button>
          <button 
            className={`tab-btn ${activeTab === 'benchmark' ? 'active' : ''}`}
            onClick={() => setActiveTab('benchmark')}
          >
            🧪 Hackathon Benchmark
          </button>
        </div>

        {activeTab === 'optimizer' && (
          <div className="dashboard-grid">
            
            {/* Left Column: Input */}
            <div className="gr-box">
              <h2 className="column-header">📥 Input Area</h2>
              
              <div className="mb-6">
                <span className="control-label">Optimization Goal</span>
                <span className="control-info">Select the type of AI review to perform</span>
                <div className="radio-group">
                  {['style-cleanup', 'efficiency-boost', 'security-audit'].map((goal) => (
                    <div 
                      key={goal}
                      className={`radio-pill ${taskType === goal ? 'active' : ''}`}
                      onClick={() => setTaskType(goal)}
                    >
                      {goal}
                    </div>
                  ))}
                </div>
              </div>

              <div className="mb-6">
                <span className="control-label">Source Language</span>
                <span className="control-info">Language of input code (or choose Auto to detect automatically)</span>
                <select 
                  className="select-dropdown"
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                >
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>

              <div className="code-wrapper">
                <div className="code-header">
                  <span>Source Code</span>
                </div>
                <textarea 
                  className="code-input"
                  value={inputCode}
                  onChange={(e) => setInputCode(e.target.value)}
                  spellCheck="false"
                />
              </div>

              <div className="button-row">
                <button 
                  className="btn btn-secondary" 
                  onClick={() => handleOptimize(false)}
                  disabled={isOptimizing}
                >
                  🚀 Analyze (Selected Goal)
                </button>
                <button 
                  className="btn btn-primary" 
                  onClick={() => handleOptimize(true)}
                  disabled={isOptimizing}
                >
                  🔥 Full Review (All Passes)
                </button>
              </div>
            </div>

            {/* Right Column: Output */}
            <div className="gr-box">
              <h2 className="column-header">📤 Output Area</h2>
              
              <div className="code-wrapper mb-6">
                <div className="code-header">
                  <span>Optimized Code</span>
                  <button className="btn-small" onClick={handleCopy}>Copy 📋</button>
                </div>
                <div 
                  className="code-output"
                  dangerouslySetInnerHTML={{ __html: highlightPython(outputCode) }}
                />
              </div>

              <div className="mb-6">
                <span className="control-label">AI Insight</span>
                <div className="textbox-container">
                  {insight || 'Optimization details will appear here...'}
                </div>
              </div>

              <div>
                <span className="control-label" style={{marginBottom: '0.75rem'}}>📊 Performance Metrics</span>
                <div className="stat-grid">
                  <StatBox title="Initial Score" value={initialScore} />
                  <StatBox title="Optimized Score" value={optimizedScore} type="success" />
                  <StatBox title="Est. Speedup" value={speedup} type="highlight" />
                  <StatBox title="Memory Saved" value={memorySaved} type="highlight" />
                </div>
              </div>
            </div>

          </div>
        )}

        {activeTab === 'benchmark' && (
          <div className="gr-box">
            <h3>🤖 Automated Task Evaluation</h3>
            <p className="control-info" style={{marginBottom: '1.5rem'}}>Run a 5-step RL agent sequence to automatically fix a corrupted baseline file.</p>
            <div style={{display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '2rem'}}>
               <select 
                 className="select-dropdown" 
                 style={{padding: '0.75rem 2.5rem 0.75rem 1rem', width: 'auto', flex: '0 0 auto', minWidth: '200px'}}
                 value={benchmarkTask}
                 onChange={(e) => setBenchmarkTask(e.target.value)}
                 disabled={isBenchmarking}
               >
                 <option value="style-cleanup">style-cleanup</option>
                 <option value="efficiency-boost">efficiency-boost</option>
                 <option value="security-audit">security-audit</option>
               </select>
               <button 
                 className="btn btn-secondary" 
                 style={{flex: '0 0 auto', whiteSpace: 'nowrap'}}
                 onClick={handleRunBenchmark}
                 disabled={isBenchmarking}
               >
                 {isBenchmarking ? '⌛ Running...' : '▶ Run Benchmark Sequence'}
               </button>
            </div>

            {benchmarkResult && (
              <div style={{marginBottom: '2rem'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem'}}>
                  <span className="control-label" style={{margin: 0}}>📋 Trajectory Steps</span>
                  <span style={{fontSize: '0.8rem', color: benchmarkResult.model_loaded ? '#10b981' : '#f59e0b', fontWeight: 'bold'}}>
                    {benchmarkResult.model_loaded ? '🟢 DQN RL Model Loaded' : '⚠️ Heuristic Fallback'}
                  </span>
                </div>
                <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '2rem'}}>
                  {benchmarkResult.steps.map((step, idx) => (
                    <div key={idx} style={{background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', padding: '1rem'}}>
                      <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
                        <span style={{fontWeight: 'bold', fontSize: '0.9rem', color: '#818cf8'}}>Step {step.step}: {step.action}</span>
                        <span style={{fontWeight: 'bold', color: step.reward >= 0.85 ? '#10b981' : '#ef4444'}}>Reward: {step.reward.toFixed(2)}</span>
                      </div>
                      {step.linter && step.linter.length > 0 && (
                        <div style={{fontSize: '0.8rem', color: '#f87171'}}>
                          <strong>Linter:</strong> {step.linter.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="code-wrapper" style={{marginTop: '2rem'}}>
                <div className="code-header">
                  <span>Agent Final Fix</span>
                </div>
                <div 
                  className="code-output"
                  dangerouslySetInnerHTML={{ __html: highlightPython(benchmarkResult ? benchmarkResult.final_code : '') }}
                />
            </div>
          </div>
        )}
      </div>

      <div className="toast-container">
        {toasts.map(t => (
          <Toast key={t.id} message={t.message} type={t.type} onRemove={() => setToasts(prev => prev.filter(item => item.id !== t.id))} />
        ))}
      </div>
    </div>
  );
}

export default App;
