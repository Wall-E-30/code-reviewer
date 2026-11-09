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

  return (
    <div>
      {/* Header Grid Section */}
      <section className="grid" style={{ borderTop: "none", paddingTop: "1rem" }}>
        <div className="main">
          <span className="eyebrow">GROWTH-02 BENCHMARK HUB // HELD-OUT SPLIT</span>
          <h1>Aion-Bench Public Leaderboard</h1>
          <p className="lead">
            The objective, reproducible benchmark for AI-native code reviewers. Evaluated across real bug injections, mined maintainer PR corrections, and clean diff negative controls to penalize subjective nitpicking and hallucinations.
          </p>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "2rem" }}>
            <button
              onClick={() => setShowSubmitModal(true)}
              className="button"
              aria-label="Open evaluation submission instructions modal"
            >
              Submit Evaluation
            </button>
            <a
              href="/docs"
              className="button button--outline"
              aria-label="Read methodology and schema documentation"
            >
              Methodology &amp; Schema
            </a>
          </div>
        </div>

        <div className="aside">
          <div className="meta-panel">
            <div className="meta-panel__header">BENCHMARK PROTOCOL</div>
            <div className="meta-row">
              <span className="meta-label">SPLIT TYPE</span>
              <span className="meta-value">Locked Private Test</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">NEGATIVE CONTROLS</span>
              <span className="meta-value">Clean-Diff FPR Evaluated</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">PRECISION GATE</span>
              <span className="meta-value">Clean FPR &lt; 10%</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">INTEGRITY</span>
              <span className="meta-value">SHA-256 Manifest</span>
            </div>
          </div>
        </div>
      </section>

      {/* Summary KPI Metrics */}
      {summary && (
        <section style={{ maxWidth: "72rem", margin: "0 auto", padding: "0 2rem 2.5rem 2rem" }}>
          <div className="metrics-grid">
            <div className="metric-cell">
              <div className="metric-label">Total Evaluated</div>
              <div className="metric-value">{summary.total_models} Models</div>
              <div className="caption" style={{ marginTop: "0.25rem" }}>
                {summary.open_weights_count} open-weights architectures
              </div>
            </div>

            <div className="metric-cell">
              <div className="metric-label">Top Ranked Model</div>
              <div className="metric-value metric-value--accent" style={{ fontSize: "1.5rem" }}>
                {summary.top_model}
              </div>
              <div className="caption" style={{ marginTop: "0.25rem" }}>
                Peak Precision: <strong>{summary.top_precision}</strong>
              </div>
            </div>

            <div className="metric-cell">
              <div className="metric-label">Benchmark Mean Precision</div>
              <div className="metric-value">{summary.average_precision}</div>
              <div className="caption" style={{ marginTop: "0.25rem" }}>
                Held-out evaluation split mean
              </div>
            </div>

            <div className="metric-cell">
              <div className="metric-label">Evaluation Gate</div>
              <div className="metric-value" style={{ fontSize: "1.5rem" }}>
                Clean FPR &lt; 10%
              </div>
              <div className="caption" style={{ marginTop: "0.25rem" }}>
                Anti-hallucination barrier
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Table Section */}
      <section style={{ maxWidth: "72rem", margin: "0 auto", padding: "0 2rem 4rem 2rem" }}>
        {/* Filter Controls & Caption */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "1rem",
            paddingBottom: "1.25rem",
            borderBottom: "1px solid var(--black)"
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {["all", "open-weights", "commercial-api", "static-tool"].map((t) => {
              const isActive = filter === t;
              return (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className={`button button--small ${isActive ? "" : "button--outline"}`}
                  aria-pressed={isActive}
                >
                  {t === "all" ? "All Models" : t.replace("-", " ").toUpperCase()}
                </button>
              );
            })}
          </div>

          <span className="caption" style={{ fontWeight: 600 }}>
            Ranked by Precision (desc) &amp; Clean-Diff FPR (asc)
          </span>
        </div>

        {/* Swiss Data Table */}
        <div className="swiss-table-wrap">
          <table className="swiss-table">
            <thead>
              <tr>
                <th style={{ width: "70px", textAlign: "center" }}>Rank</th>
                <th>Model &amp; Organization</th>
                <th>Type</th>
                <th style={{ textAlign: "right" }}>Precision</th>
                <th style={{ textAlign: "right" }}>Recall</th>
                <th style={{ textAlign: "right" }}>Clean FPR</th>
                <th style={{ textAlign: "right" }}>Nitpicks</th>
                <th style={{ textAlign: "right" }}>Latency</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: "center", padding: "3rem 1rem", color: "var(--text-muted)" }}>
                    Loading benchmark submissions...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: "center", padding: "3rem 1rem", color: "var(--text-muted)" }}>
                    No models matching filter criteria.
                  </td>
                </tr>
              ) : (
                entries.map((item, idx) => {
                  const isTop = idx === 0;
                  return (
                    <tr key={item.model_id} className={isTop ? "highlight" : ""}>
                      <td style={{ textAlign: "center" }}>
                        {isTop ? (
                          <span className="tag-badge tag-badge--accent">#1 TOP</span>
                        ) : (
                          <span className="swiss-mono">#{idx + 1}</span>
                        )}
                      </td>
                      <td>
                        <div style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          {item.display_name}
                          {item.verified && (
                            <span
                              style={{ color: "var(--red)", fontSize: "0.75rem", fontWeight: 700 }}
                              title="Verified by Aion maintainers"
                            >
                              [VERIFIED]
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
                          {item.organization} • <span className="swiss-mono">{item.license}</span>
                        </div>
                      </td>
                      <td>
                        <span className="tag-badge">
                          {item.model_type}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }} className="swiss-mono">
                        <strong>{(item.precision * 100).toFixed(1)}%</strong>
                      </td>
                      <td style={{ textAlign: "right" }} className="swiss-mono">
                        {(item.recall * 100).toFixed(1)}%
                      </td>
                      <td
                        style={{
                          textAlign: "right",
                          color: item.false_positive_rate < 0.1 ? "var(--black)" : "var(--red)"
                        }}
                        className="swiss-mono"
                      >
                        {(item.false_positive_rate * 100).toFixed(1)}%
                      </td>
                      <td style={{ textAlign: "right" }} className="swiss-mono">
                        {(item.nitpick_rate * 100).toFixed(1)}%
                      </td>
                      <td style={{ textAlign: "right", color: "var(--text-muted)" }} className="swiss-mono">
                        {Math.round(item.avg_latency_ms)}ms
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Submission Modal Dialog */}
      {showSubmitModal && (
        <div
          className="swiss-modal-backdrop"
          onClick={() => setShowSubmitModal(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="submit-modal-title"
        >
          <div className="swiss-modal" onClick={(e) => e.stopPropagation()}>
            <div className="swiss-modal__header">
              <div>
                <span className="eyebrow">SUBMISSION PROTOCOL</span>
                <h3 id="submit-modal-title" style={{ marginTop: "0.25rem" }}>
                  Submit to Aion-Bench Leaderboard
                </h3>
              </div>
            </div>

            <div className="swiss-modal__body">
              <p style={{ marginBottom: "1rem" }}>
                We welcome community model submissions. Evaluations must run against the official held-out test split using the Aion-Bench runner:
              </p>

              <div
                style={{
                  background: "var(--gray)",
                  border: "1px solid var(--black)",
                  padding: "1rem",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.8125rem",
                  marginBottom: "1rem",
                  overflowX: "auto"
                }}
              >
                aion bench evaluate --model &lt;model-name&gt; --split test --output results.json
              </div>

              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                Submissions can be submitted programmatically via <code style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>POST /api/leaderboard/submit</code> or by opening a PR modifying <code style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>data/leaderboard.json</code> with replication instructions.
              </p>
            </div>

            <div className="swiss-modal__footer">
              <button
                onClick={() => setShowSubmitModal(false)}
                className="button button--outline"
                aria-label="Close modal dialog"
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
