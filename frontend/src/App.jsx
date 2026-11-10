import React, { useState, useEffect } from 'react';
import './AionStyles.css';
import LeaderboardView from './LeaderboardView.jsx';

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

const Toast = ({ message, type, onRemove }) => {
  useEffect(() => {
    const timer = setTimeout(onRemove, 3000);
    return () => clearTimeout(timer);
  }, [onRemove]);

  return (
    <div className="toast">
      <span aria-hidden="true">{type === 'warning' ? '●' : '■'}</span>
      <span>{message}</span>
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
    addToast("Copied to clipboard");
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
      addToast("Benchmark Sequence Finished");
    } catch {
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
        setAstNodeDelta(data.perf_gain || 'Static Verified');
        setStructuralComplexity(data.mem_reduction || 'AST Clean');
        
        addToast("Optimization Successful");
      }
    } catch {
      addToast("Optimization Failed. Is the server running?", "warning");
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div style={{ width: '100%' }}>
      {/* Top Status Bar */}
      <header className="top-bar">
        <div className="top-bar__inner">
          <span>AION // AUTONOMOUS RL REVIEW ENGINE</span>
          <div className="top-bar__status">
            <span className="top-bar__dot" aria-hidden="true"></span>
            <span>MDP ACTIVE / ROOTLESS SANDBOX</span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="grid" style={{ borderTop: 'none', paddingBottom: '2.5rem' }}>
        <div className="main">
          <span className="eyebrow">POWERED BY RL &amp; AST EVALUATION</span>
          <h1>Aion Code Reviewer</h1>
          <p className="lead">
            An intelligent code optimization engine that detects style, efficiency, and security flaws, rewriting them dynamically.
          </p>
        </div>

        <div className="aside">
          <div className="meta-panel">
            <div className="meta-panel__header">SYSTEM SPECIFICATION</div>
            <div className="meta-row">
              <span className="meta-label">ENVIRONMENT</span>
              <span className="meta-value">Gymnasium / OpenEnv</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">COMMENT CEILING</span>
              <span className="meta-value">≤ 5 / PR</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">PRECISION GATE</span>
              <span className="meta-value">Clean FPR &lt; 10%</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">LICENSE</span>
              <span className="meta-value">Apache-2.0</span>
            </div>
          </div>
        </div>
      </section>

      {/* Hairline-Ruled Navigation Bar */}
      <nav className="tabs-nav" aria-label="Main Navigation">
        <button 
          className={`tab-item ${activeTab === 'optimizer' ? 'active' : ''}`}
          onClick={() => setActiveTab('optimizer')}
          aria-pressed={activeTab === 'optimizer'}
        >
          01 / LIVE OPTIMIZER
        </button>
        <button 
          className={`tab-item ${activeTab === 'benchmark' ? 'active' : ''}`}
          onClick={() => setActiveTab('benchmark')}
          aria-pressed={activeTab === 'benchmark'}
        >
          02 / HACKATHON BENCHMARK
        </button>
        <button 
          className={`tab-item ${activeTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('leaderboard')}
          aria-pressed={activeTab === 'leaderboard'}
        >
          03 / AION-BENCH LEADERBOARD
        </button>
      </nav>

      {/* Tab 1: Live Optimizer */}
      {activeTab === 'optimizer' && (
        <section className="grid grid--equal" style={{ borderTop: 'none' }}>
          {/* Left Column: Input Specification */}
          <div className="main">
            <span className="eyebrow">01.1 // INPUT SPECIFICATION</span>
            <h2 style={{ marginTop: '0.25rem', marginBottom: '1.5rem' }}>Source Code &amp; Policy</h2>
            
            <div className="field-group">
              <label className="field-label">Optimization Goal</label>
              <span className="field-hint">Select the type of AI review to perform</span>
              <div className="goal-grid" role="radiogroup" aria-label="Optimization goal">
                {['style-cleanup', 'efficiency-boost', 'security-audit'].map((goal) => {
                  const isActive = taskType === goal;
                  return (
                    <button 
                      key={goal}
                      type="button"
                      role="radio"
                      aria-checked={isActive}
                      className={`goal-btn ${isActive ? 'active' : ''}`}
                      onClick={() => setTaskType(goal)}
                    >
                      {goal}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="language-select">Source Language</label>
              <span className="field-hint">Language of input code (or choose Auto to detect automatically)</span>
              <select 
                id="language-select"
                className="select-box"
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                aria-label="Select source programming language"
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
                <div className="alert-box">
                  <span className="alert-box__badge">NOTE</span>
                  <span>Language is in experimental static preview mode. Full AST grading active for Python &amp; TypeScript.</span>
                </div>
              )}
            </div>

            <div className="code-panel">
              <div className="code-bar">
                <span>Input / Source Buffer</span>
                <span className="meta-label" style={{ fontFamily: 'var(--font-mono)' }}>{selectedLanguage}</span>
              </div>
              <textarea 
                className="code-textarea"
                value={inputCode}
                onChange={(e) => setInputCode(e.target.value)}
                spellCheck="false"
                aria-label="Source code input buffer"
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <button 
                className="button button--outline" 
                onClick={() => handleOptimize(false)}
                disabled={isOptimizing}
                aria-label={`Analyze code with selected goal: ${taskType}`}
              >
                Analyze ({taskType})
              </button>
              <button 
                className="button" 
                onClick={() => handleOptimize(true)}
                disabled={isOptimizing}
                aria-label="Perform full code review across all optimization passes"
              >
                {isOptimizing ? 'Analyzing...' : 'Full Review (All Passes)'}
              </button>
            </div>
          </div>

          {/* Right Column: Output & Telemetry */}
          <div className="aside">
            <span className="eyebrow">01.2 // VERIFIED OUTPUT &amp; TELEMETRY</span>
            <h2 style={{ marginTop: '0.25rem', marginBottom: '1.5rem' }}>Optimized Synthesis</h2>
            
            <div className="code-panel">
              <div className="code-bar">
                <span>Output / Rewritten Buffer</span>
                <button 
                  className="button button--outline button--small" 
                  onClick={handleCopy}
                  aria-label="Copy optimized code to clipboard"
                >
                  Copy
                </button>
              </div>
              <div 
                className="code-view"
                tabIndex={0}
                aria-label="Optimized rewritten code output"
                dangerouslySetInnerHTML={{ __html: highlightPython(outputCode) }}
              />
            </div>

            <div className="callout-box">
              <div className="callout-box__title">RL Policy Recommendation</div>
              <div className="callout-box__body">
                {insight || 'Optimization details and AST analysis will appear here once executed.'}
              </div>
            </div>

            <div className="field-group" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.75rem' }}>
                <span className="field-label" style={{ margin: 0 }}>AST Structural Telemetry</span>
                <span className="caption">Static AST Analysis</span>
              </div>
              <div className="metrics-grid">
                <div className="metric-cell">
                  <div className="metric-label">Initial Score</div>
                  <div className="metric-value">{initialScore}</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-label">Optimized Score</div>
                  <div className="metric-value metric-value--accent">{optimizedScore}</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-label">Static Analysis</div>
                  <div className="metric-value">{astNodeDelta}</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-label">AST Diagnostics</div>
                  <div className="metric-value">{structuralComplexity}</div>
                </div>
              </div>
              <p className="caption" style={{ marginTop: '0.5rem' }}>
                Verified Static Analysis &amp; AST Diagnostics — Real execution benchmarks available via Aion-Bench.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Tab 2: Hackathon Benchmark */}
      {activeTab === 'benchmark' && (
        <section className="grid" style={{ borderTop: 'none' }}>
          <div className="main">
            <span className="eyebrow">02.1 // BENCHMARK EXECUTION</span>
            <h2>Automated Task Evaluation</h2>
            <p className="lead" style={{ fontSize: '1rem', marginBottom: '1.5rem' }}>
              Run a 5-step RL agent sequence to automatically fix a corrupted baseline file.
            </p>

            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap' }}>
              <select 
                className="select-box" 
                style={{ width: 'auto', minWidth: '220px' }}
                value={benchmarkTask}
                onChange={(e) => setBenchmarkTask(e.target.value)}
                disabled={isBenchmarking}
                aria-label="Select benchmark task type"
              >
                <option value="style-cleanup">style-cleanup</option>
                <option value="efficiency-boost">efficiency-boost</option>
                <option value="security-audit">security-audit</option>
              </select>
              <button 
                className="button" 
                onClick={handleRunBenchmark}
                disabled={isBenchmarking}
                aria-label="Execute benchmark sequence"
              >
                {isBenchmarking ? 'Executing Sequence...' : 'Run Benchmark Sequence'}
              </button>
            </div>

            {benchmarkResult && (
              <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingBottom: '0.5rem', borderBottom: '1px solid var(--black)', marginBottom: '1rem' }}>
                  <span className="field-label" style={{ margin: 0 }}>Trajectory Steps</span>
                  <span className="tag-badge" style={{ color: benchmarkResult.model_loaded ? 'var(--black)' : 'var(--red)' }}>
                    {benchmarkResult.model_loaded ? 'DQN RL Model Loaded' : 'Heuristic Fallback'}
                  </span>
                </div>

                <div className="trajectory-list">
                  {benchmarkResult.steps.map((step, idx) => (
                    <div key={idx} className="trajectory-item">
                      <div className="trajectory-item__step">STEP {step.step}</div>
                      <div className="trajectory-item__action">
                        <div>{step.action}</div>
                        {step.linter && step.linter.length > 0 && (
                          <div style={{ color: 'var(--red)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                            Linter: {step.linter.join(', ')}
                          </div>
                        )}
                      </div>
                      <div className={`trajectory-item__reward ${step.reward >= 0.85 ? 'trajectory-item__reward--pass' : 'trajectory-item__reward--fail'}`}>
                        Reward: {step.reward.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="code-panel" style={{ marginTop: '2rem' }}>
              <div className="code-bar">
                <span>Agent Final Fix Buffer</span>
              </div>
              <div 
                className="code-view"
                tabIndex={0}
                aria-label="Agent final fix buffer"
                dangerouslySetInnerHTML={{ __html: highlightPython(benchmarkResult ? benchmarkResult.final_code : '') }}
              />
            </div>
          </div>

          <div className="aside">
            <div className="meta-panel">
              <div className="meta-panel__header">BENCHMARK SPECIFICATION</div>
              <div className="meta-row">
                <span className="meta-label">HORIZON</span>
                <span className="meta-value">5 Steps Max</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">REWARD FUNCTION</span>
                <span className="meta-value">AST Diff + Linter</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">POLICY</span>
                <span className="meta-value">DQN / Epsilon Greedy</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">BASELINE FILE</span>
                <span className="meta-value">Deterministic Seed</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Tab 3: Aion-Bench Leaderboard */}
      {activeTab === 'leaderboard' && (
        <LeaderboardView />
      )}

      {/* Toast Notifications */}
      <div className="toast-container" role="region" aria-live="polite">
        {toasts.map(t => (
          <Toast 
            key={t.id} 
            message={t.message} 
            type={t.type} 
            onRemove={() => setToasts(prev => prev.filter(item => item.id !== t.id))} 
          />
        ))}
      </div>
    </div>
  );
}

export default App;
