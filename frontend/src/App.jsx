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

const StatBox = ({ title, value, type = '', tooltip = '' }) => (
  <div className={`stat-box ${type}`} title={tooltip}>
    <h3>{title}</h3>
    <p>{value}</p>
    {tooltip && <span style={{ display: 'block', fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.25rem' }}>{tooltip}</span>}
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

const TIER1_LANGUAGES = [
  { name: "Python", key: "python" },
  { name: "TypeScript", key: "typescript" },
  { name: "JavaScript", key: "javascript" }
];

const EXPERIMENTAL_LANGUAGES = [
  { name: "Java", key: "java" },
  { name: "C++", key: "cpp" },
  { name: "C", key: "c" },
  { name: "Go", key: "go" },
  { name: "Rust", key: "rust" },
  { name: "Ruby", key: "ruby" },
  { name: "Kotlin", key: "kotlin" },
  { name: "Swift", key: "swift" },
  { name: "C#", key: "csharp" },
  { name: "PHP", key: "php" },
  { name: "HTML", key: "html" },
  { name: "CSS", key: "css" },
  { name: "SQL", key: "sql" },
  { name: "Bash", key: "bash" }
];

const LANG_KEYS = {
  "Auto (Detect)": "auto",
  "Python": "python", "Python (Supported)": "python",
  "TypeScript": "typescript", "TypeScript (Supported)": "typescript",
  "JavaScript": "javascript", "JavaScript (Supported)": "javascript",
  "Java": "java", "Java (Experimental)": "java",
  "C++": "cpp", "C++ (Experimental)": "cpp",
  "C": "c", "C (Experimental)": "c",
  "Go": "go", "Go (Experimental)": "go",
  "Rust": "rust", "Rust (Experimental)": "rust",
  "Ruby": "ruby", "Ruby (Experimental)": "ruby",
  "Kotlin": "kotlin", "Kotlin (Experimental)": "kotlin",
  "Swift": "swift", "Swift (Experimental)": "swift",
  "C#": "csharp", "C# (Experimental)": "csharp",
  "PHP": "php", "PHP (Experimental)": "php",
  "HTML": "html", "HTML (Experimental)": "html",
  "CSS": "css", "CSS (Experimental)": "css",
  "SQL": "sql", "SQL (Experimental)": "sql",
  "Bash": "bash", "Bash (Experimental)": "bash"
};

const API_BASE = import.meta.env.VITE_API_URL || '';

function App() {
  const [activeTab, setActiveTab] = useState('optimizer');
  const [taskType, setTaskType] = useState('efficiency-boost');
  const [selectedLanguage, setSelectedLanguage] = useState('Auto (Detect)');
  const [inputCode, setInputCode] = useState('def process_data(data):\n    import sys\n    results = []\n    for item in data:\n        for other_item in data:\n            if item == other_item:\n                results.append(item)\n    return results');
  const [outputCode, setOutputCode] = useState('');
  const [insight, setInsight] = useState('');
  
  const [initialScore, setInitialScore] = useState('-');
  const [optimizedScore, setOptimizedScore] = useState('-');
  const [astNodeDelta, setAstNodeDelta] = useState('-');
  const [structuralComplexity, setStructuralComplexity] = useState('-');
  
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
      const response = await fetch(`${API_BASE}/run_benchmark`, {
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
      const response = await fetch(`${API_BASE}${endpoint}`, {
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
        setAstNodeDelta(data.perf_gain || '+0 nodes');
        setStructuralComplexity(data.mem_reduction || '-0.0');
        
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
                  <option value="Auto (Detect)">Auto (Detect)</option>
                  <optgroup label="Supported (Tier-1)">
                    {TIER1_LANGUAGES.map((lang) => (
                      <option key={lang.name} value={lang.name}>
                        {lang.name} (Supported)
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Experimental">
                    {EXPERIMENTAL_LANGUAGES.map((lang) => (
                      <option key={lang.name} value={lang.name}>
                        {lang.name} (Experimental)
                      </option>
                    ))}
                  </optgroup>
                </select>
                {EXPERIMENTAL_LANGUAGES.some(l => l.name === selectedLanguage) && (
                  <div style={{
                    marginTop: '0.75rem',
                    padding: '0.75rem 1rem',
                    background: 'rgba(245, 158, 11, 0.1)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: '8px',
                    color: '#fbbf24',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}>
                    <span>⚠️</span>
                    <span>Language is in experimental static preview mode. Full AST grading active for Python &amp; TypeScript.</span>
                  </div>
                )}
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span className="control-label" style={{ margin: 0 }}>📊 Performance Metrics</span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>
                    Static AST Structural Metric — Real execution benchmarks available via Aion-Bench
                  </span>
                </div>
                <div className="stat-grid">
                  <StatBox title="Initial Score" value={initialScore} />
                  <StatBox title="Optimized Score" value={optimizedScore} type="success" />
                  <StatBox 
                    title="AST Node Delta" 
                    value={astNodeDelta} 
                    type="highlight" 
                    tooltip="Exact change in total AST nodes"
                  />
                  <StatBox 
                    title="Structural Complexity Score" 
                    value={structuralComplexity} 
                    type="highlight" 
                    tooltip="AST nesting & branch reduction"
                  />
                </div>
                <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#64748b', fontStyle: 'italic', textAlign: 'center' }}>
                  Static AST Structural Metric — Real execution benchmarks available via Aion-Bench
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
