import React, { useState, useEffect } from "react";

export default function LeaderboardView() {
  const [entries, setEntries] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  useEffect(() => {
    fetchLeaderboard();
  }, [filter]);

  const fetchLeaderboard = async () => {
    setLoading(true);
    try {
      const url = filter === "all" ? "/api/leaderboard" : `/api/leaderboard?model_type=${filter}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEntries(data.entries || []);
        setSummary(data.summary || null);
      }
    } catch (err) {
      console.error("Failed to fetch leaderboard:", err);
    } finally {
      setLoading(false);
    }
  };

  const getTypeBadgeClass = (type) => {
    switch (type) {
      case "open-weights":
        return "bg-emerald-900/60 text-emerald-300 border-emerald-500/40";
      case "commercial-api":
        return "bg-purple-900/60 text-purple-300 border-purple-500/40";
      case "static-tool":
        return "bg-blue-900/60 text-blue-300 border-blue-500/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto p-6 space-y-8 font-sans">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-500/30 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
        <div className="relative z-10 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              GROWTH-02 Benchmark Hub
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              🔒 Locked Private Test Split
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
              🛡️ Clean-Diff FPR Evaluated
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Aion-Bench Public Leaderboard
          </h1>
          <p className="text-slate-300 text-base max-w-3xl leading-relaxed">
            The objective, reproducible benchmark for AI-native code reviewers. Evaluated across real bug injections, mined maintainer PR corrections, and clean diff negative controls to penalize subjective nitpicking and hallucinations.
          </p>

          <div className="pt-2 flex flex-wrap gap-4">
            <button
              onClick={() => setShowSubmitModal(true)}
              className="px-5 py-2.5 rounded-xl font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all text-sm flex items-center gap-2"
            >
              <span>🚀 Submit Evaluation</span>
            </button>
            <a
              href="/docs"
              className="px-5 py-2.5 rounded-xl font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all text-sm flex items-center gap-2"
            >
              <span>📖 Methodology & Schema</span>
            </a>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Total Evaluated</div>
            <div className="text-2xl font-bold text-white mt-1">{summary.total_models} models</div>
            <div className="text-xs text-slate-500 mt-1">{summary.open_weights_count} open-weights</div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Top Ranked Model</div>
            <div className="text-base font-bold text-emerald-400 mt-1 truncate">{summary.top_model}</div>
            <div className="text-xs text-slate-500 mt-1">Precision: {summary.top_precision}</div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Benchmark Mean Precision</div>
            <div className="text-2xl font-bold text-indigo-400 mt-1">{summary.average_precision}</div>
            <div className="text-xs text-slate-500 mt-1">Held-out split</div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Evaluation Gate</div>
            <div className="text-sm font-semibold text-cyan-400 mt-1">Clean-Diff FPR &lt; 10%</div>
            <div className="text-xs text-slate-500 mt-1">Anti-hallucination barrier</div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          {["all", "open-weights", "commercial-api", "static-tool"].map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === t
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              {t === "all" ? "All Models" : t.replace("-", " ").toUpperCase()}
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-400">Ranked by Precision (desc) & Clean-Diff FPR (asc)</span>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950/80 text-slate-400 uppercase text-xs tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-4 px-4 text-center">Rank</th>
                <th className="py-4 px-6">Model & Provider</th>
                <th className="py-4 px-4">Type</th>
                <th className="py-4 px-4 text-right">Precision</th>
                <th className="py-4 px-4 text-right">Recall</th>
                <th className="py-4 px-4 text-right">Clean FPR</th>
                <th className="py-4 px-4 text-right">Nitpicks</th>
                <th className="py-4 px-4 text-right">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan="8" className="text-center py-12 text-slate-500">
                    Loading benchmark submissions...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-12 text-slate-500">
                    No models matching filter criteria.
                  </td>
                </tr>
              ) : (
                entries.map((item, idx) => {
                  const isTop = idx === 0;
                  return (
                    <tr
                      key={item.model_id}
                      className={`hover:bg-slate-800/40 transition-colors ${
                        isTop ? "bg-indigo-950/20 font-semibold" : ""
                      }`}
                    >
                      <td className="py-4 px-4 text-center">
                        {isTop ? (
                          <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold">
                            🏆 1
                          </span>
                        ) : (
                          <span className="text-slate-400 font-mono text-sm">#{idx + 1}</span>
                        )}
                      </td>
                      <td className="py-4 px-6">
                        <div className="text-white font-medium flex items-center gap-2">
                          {item.display_name}
                          {item.verified && (
                            <span className="text-cyan-400 text-xs" title="Verified by Aion maintainers">
                              ✓
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400">
                          {item.organization} • <span className="font-mono">{item.license}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span
                          className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${getTypeBadgeClass(
                            item.model_type
                          )}`}
                        >
                          {item.model_type}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-right font-mono text-emerald-400 font-bold">
                        {(item.precision * 100).toFixed(1)}%
                      </td>
                      <td className="py-4 px-4 text-right font-mono text-slate-300">
                        {(item.recall * 100).toFixed(1)}%
                      </td>
                      <td className="py-4 px-4 text-right font-mono text-cyan-400">
                        {(item.false_positive_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-4 px-4 text-right font-mono text-amber-400">
                        {(item.nitpick_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-4 px-4 text-right font-mono text-slate-400 text-xs">
                        {Math.round(item.avg_latency_ms)}ms
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Submission Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-xl font-bold text-white">Submit to Aion-Bench Leaderboard</h3>
            <p className="text-slate-300 text-sm">
              We welcome community model submissions. Evaluations must run against the official held-out test split using the Aion-Bench runner:
            </p>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-indigo-300 overflow-x-auto">
              aion bench evaluate --model &lt;model-name&gt; --split test --output results.json
            </div>
            <p className="text-slate-400 text-xs">
              Submissions can be submitted programmatically via <code className="text-indigo-300">POST /api/leaderboard/submit</code> or by opening a PR modifying <code className="text-indigo-300">data/leaderboard.json</code> with replication instructions.
            </p>
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowSubmitModal(false)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

