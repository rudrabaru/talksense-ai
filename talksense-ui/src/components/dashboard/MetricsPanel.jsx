import React, { memo } from "react";

// ── SpeakerAttributionCard ────────────────────────────────────────────────────
// Renders speaker attribution status + post-session quality diagnostics.
//
// Props:
//   attribution      {status, speakers_detected, coverage, segments_updated,
//                    total_segments, speaker_turns} | null
//   attributionStatus string | null  — flat lifecycle status string
//   sessionStatus    string | null   — parent session status
//   secondsAgo       number | null   — seconds since last REST sync

const _STATUS_LABELS = {
  pending:    "Queued",
  processing: "Processing speakers...",
  completed:  "Completed ✓",
  failed:     "Failed",
};

const _STATUS_COLORS = {
  pending:    "#f59e0b",
  processing: "#3b82f6",
  completed:  "#10b981",
  failed:     "#ef4444",
};

const SpeakerAttributionCard = ({ attribution, attributionStatus, sessionStatus, secondsAgo }) => {
  const status      = attribution?.status ?? attributionStatus ?? null;
  const statusLabel = _STATUS_LABELS[status] ?? (sessionStatus === "completed" ? "Waiting for processing" : "Not Started");
  const statusColor = _STATUS_COLORS[status] ?? "#94a3b8";

  const speakersDetected = attribution?.speakers_detected ?? null;
  const coverage         = attribution?.coverage ?? null;
  const segmentsUpdated  = attribution?.segments_updated ?? null;
  const totalSegments    = attribution?.total_segments ?? null;
  const speakerTurns     = attribution?.speaker_turns ?? null;

  const showDiagnostics = status === "completed" && coverage != null;
  const showPollingHint = (status === "pending" || status === "processing") && secondsAgo != null;

  const coverageColor = coverage >= 80 ? "#10b981" : coverage >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div>
      {/* Status header row */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
        <strong>Speaker Attribution:</strong>
        <span style={{ color: statusColor, fontWeight: 600, fontSize: "0.92em" }}>
          {statusLabel}
        </span>
        {showPollingHint && (
          <span style={{ fontSize: "0.8em", color: "#94a3b8" }}>
            (updated {secondsAgo}s ago)
          </span>
        )}
      </div>

      {/* Quality diagnostics — only after completed */}
      {showDiagnostics && (
        <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>

          {/* Coverage progress bar */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82em", color: "#475569", marginBottom: "3px" }}>
              <span>Coverage</span>
              <span style={{ fontWeight: 600, color: coverageColor }}>{coverage}%</span>
            </div>
            <div style={{ height: "6px", borderRadius: "3px", background: "#e2e8f0", overflow: "hidden" }}>
              <div style={{
                height: "100%",
                width: `${Math.min(coverage, 100)}%`,
                borderRadius: "3px",
                background: coverageColor,
                transition: "width 0.6s ease",
              }} />
            </div>
          </div>

          {/* Stat pills */}
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "4px" }}>
            {speakersDetected != null && (
              <span style={{ fontSize: "0.82em", color: "#475569" }}>
                🗣 <strong style={{ color: "#1e293b" }}>{speakersDetected}</strong> speakers
              </span>
            )}
            {segmentsUpdated != null && totalSegments != null && (
              <span style={{ fontSize: "0.82em", color: "#475569" }}>
                📝 <strong style={{ color: "#1e293b" }}>{segmentsUpdated}</strong>/{totalSegments} segments
              </span>
            )}
            {speakerTurns != null && (
              <span style={{ fontSize: "0.82em", color: "#475569" }}>
                🔄 <strong style={{ color: "#1e293b" }}>{speakerTurns}</strong> turns
              </span>
            )}
          </div>
        </div>
      )}

      {/* Failed state hint */}
      {status === "failed" && (
        <p style={{ margin: "6px 0 0 0", fontSize: "0.82em", color: "#ef4444", fontStyle: "italic" }}>
          Diagnostics unavailable
        </p>
      )}
    </div>
  );
};

// ── MetricsPanel ──────────────────────────────────────────────────────────────

const MetricsPanel = memo(({ metrics, sessionStatus, lastSyncAt }) => {
  const hasValidMetrics = !!(
    metrics && (
      metrics.health_score != null ||
      metrics.speaking_ratio != null ||
      metrics.filler_count != null ||
      metrics.objections != null ||
      metrics.buying_signals != null ||
      metrics.speakerAttributionStatus !== undefined ||
      (metrics.duration_seconds != null && !isNaN(Number(metrics.duration_seconds))) ||
      (metrics.participation != null &&
        typeof metrics.participation === "object" &&
        Object.keys(metrics.participation).length > 0)
    )
  );

  if (!hasValidMetrics) {
    return (
      <div
        className="metrics-panel-placeholder"
        role="region"
        aria-label="Conversation intelligence metrics"
        style={{ border: "1px solid #ccc", padding: "16px", height: "100%" }}
      >
        <h3>Conversation Intelligence</h3>
        <p>No metrics available.</p>
      </div>
    );
  }

  const [secondsAgo, setSecondsAgo] = React.useState(null);

  React.useEffect(() => {
    if (!lastSyncAt) {
      setSecondsAgo(null);
      return;
    }
    const update = () => {
      const diff = Math.round((Date.now() - new Date(lastSyncAt).getTime()) / 1000);
      setSecondsAgo(diff >= 0 ? diff : 0);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [lastSyncAt]);

  const {
    health_score,
    speaking_ratio,
    participation,
    filler_count,
    duration_seconds,
    objections,
    buying_signals,
    talkRatioSummary,
    talkTimeline,
    analyticsHealth,
  } = metrics;

  const sortedParticipation = participation && typeof participation === "object"
    ? Object.entries(participation).sort(([a], [b]) => a.localeCompare(b))
    : [];

  const parsedDuration = duration_seconds != null ? Number(duration_seconds) : NaN;
  const durationText = !isNaN(parsedDuration) ? `${parsedDuration.toFixed(1)}s` : "N/A";

  const renderSpeakingRatio = () => {
    if (!speaking_ratio) return "N/A";
    if (typeof speaking_ratio === "object") {
      return Object.entries(speaking_ratio)
        .map(([speaker, ratio]) => `${speaker}: ${ratio}%`)
        .join(" / ");
    }
    return String(speaking_ratio);
  };

  return (
    <div
      className="metrics-panel-placeholder"
      role="region"
      aria-label="Conversation intelligence metrics"
      style={{ border: "1px solid #ccc", padding: "16px", height: "100%" }}
    >
      <h3>Conversation Intelligence</h3>
      <div className="metrics-content">
      
        {/* ── Analytics Health Benchmark Status ── */}
        {analyticsHealth && (
          <div style={{ margin: "0 0 16px 0", padding: "12px", backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
            <strong style={{ display: "block", marginBottom: "8px", fontSize: "1.05em", color: "#1e293b" }}>Benchmark Analytics Health</strong>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.9em" }}>
              {Object.entries(analyticsHealth).map(([key, status]) => (
                <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "#475569" }}>{key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}:</span>
                  <span style={{
                    fontWeight: "bold",
                    color: status === "PASS" ? "#10b981" : "#ef4444",
                    backgroundColor: status === "PASS" ? "#d1fae5" : "#fee2e2",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    fontSize: "0.85em"
                  }}>
                    {status}
                  </span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: "8px", fontSize: "0.8em", color: "#64748b", fontStyle: "italic" }}>
              * Static benchmark status, not live predictions.
            </div>
          </div>
        )}

        <div style={{ margin: "12px 0" }}>
          <strong>Health Score:</strong> {health_score != null ? `${health_score}%` : "N/A"}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Speaking Ratio:</strong> {renderSpeakingRatio()}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Participation:</strong>
          {sortedParticipation.length > 0 ? (
            <ul>
              {sortedParticipation.map(([speaker, percent]) => (
                <li key={speaker}>
                  {speaker}: {percent != null ? `${percent} words` : "N/A"}
                </li>
              ))}
            </ul>
          ) : (
            " N/A"
          )}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Filler Words:</strong> {filler_count ?? "N/A"}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Duration:</strong> {durationText}
        </div>

        {/* ── Conversation Flow Analytics ── */}
        <div style={{ margin: "16px 0 12px 0", borderTop: "1px solid #eee", paddingTop: "12px" }}>
          <strong>Conversation Flow Analytics</strong>
          {talkRatioSummary ? (
            <div style={{ marginTop: "8px", fontSize: "0.9em", color: "#475569" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <div><strong>Dominance:</strong> {talkRatioSummary.summary.dominance_percent}%</div>
                <div>
                  <strong>Balance:</strong> <span style={{
                    color: talkRatioSummary.summary.conversation_balance === "POOR" ? "#ef4444" : talkRatioSummary.summary.conversation_balance === "WARNING" ? "#f59e0b" : "#10b981",
                    fontWeight: "bold"
                  }}>{talkRatioSummary.summary.conversation_balance}</span>
                </div>
                <div><strong>Longest Monologue:</strong> {talkRatioSummary.summary.longest_monologue_seconds}s ({talkRatioSummary.summary.longest_monologue_speaker || "None"})</div>
                <div>
                  <strong>Monologue Risk:</strong> <span style={{
                    color: talkRatioSummary.summary.monologue_risk === "HIGH" ? "#ef4444" : talkRatioSummary.summary.monologue_risk === "MEDIUM" ? "#f59e0b" : "#10b981",
                    fontWeight: "bold"
                  }}>{talkRatioSummary.summary.monologue_risk}</span>
                </div>
                <div><strong>Avg Turn Length:</strong> {talkRatioSummary.summary.average_turn_length_seconds}s</div>
                <div><strong>Speaker Switches:</strong> {talkRatioSummary.summary.speaker_switch_count}</div>
                <div><strong>Interruptions:</strong> {talkRatioSummary.summary.interruption_count}</div>
                <div><strong>Silence Time:</strong> {talkRatioSummary.summary.silence_duration_seconds}s</div>
              </div>
              
              {talkRatioSummary.overall_participation && (
                <div style={{ marginTop: "12px" }}>
                  <strong>Participation %:</strong>
                  <ul style={{ margin: "4px 0 0 0", paddingLeft: "20px" }}>
                    {Object.entries(talkRatioSummary.overall_participation).map(([spk, pct]) => (
                      <li key={spk}>{spk}: {pct}%</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div style={{ marginTop: "8px", fontSize: "0.9em", color: "#64748b", fontStyle: "italic" }}>
              {sessionStatus === "completed" ? "Calculating..." : "Available post-session"}
            </div>
          )}
        </div>

        {/* ── Talk Ratio Timeline ── */}
        {talkTimeline && talkTimeline.timeline && talkTimeline.timeline.length > 0 && (
          <div style={{ margin: "16px 0 12px 0", borderTop: "1px solid #eee", paddingTop: "12px" }}>
            <strong>Talk Ratio Timeline</strong>
            <div style={{ marginTop: "12px", fontSize: "0.85em", overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                <thead>
                  <tr style={{ backgroundColor: "#f8fafc", borderBottom: "2px solid #e2e8f0" }}>
                    <th style={{ padding: "6px" }}>Time Window</th>
                    {Array.from(new Set(talkTimeline.timeline.flatMap(b => Object.keys(b.speakers)))).sort().map(spk => (
                      <th key={spk} style={{ padding: "6px" }}>{spk} %</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {talkTimeline.timeline.map((bucket, idx) => {
                    const allSpeakers = Array.from(new Set(talkTimeline.timeline.flatMap(b => Object.keys(b.speakers)))).sort();
                    return (
                      <tr key={idx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "6px", color: "#475569" }}>{bucket.window_start}s - {bucket.window_end}s</td>
                        {allSpeakers.map(spk => {
                          const pct = bucket.speakers[spk]?.participation || 0;
                          return (
                            <td key={spk} style={{ padding: "6px", fontWeight: pct > 50 ? "bold" : "normal" }}>
                              {pct}%
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Speaker Attribution Quality Card ── */}
        <div style={{ margin: "16px 0 12px 0", borderTop: "1px solid #eee", paddingTop: "12px" }}>
          <SpeakerAttributionCard
            attribution={metrics.speakerAttribution}
            attributionStatus={metrics.speakerAttributionStatus}
            sessionStatus={sessionStatus}
            secondsAgo={secondsAgo}
          />
        </div>

        {/* ── Role Classification ── */}
        <div style={{ margin: "16px 0 12px 0", borderTop: "1px solid #eee", paddingTop: "12px" }}>
          <strong>Role Classification</strong>
          <div style={{ marginTop: "8px", fontSize: "0.9em", color: "#475569" }}>
            {metrics.speakerRoles ? (
              <ul style={{ margin: 0, paddingLeft: "20px" }}>
                {Object.entries(metrics.speakerRoles).map(([speaker, role]) => (
                  <li key={speaker}>
                    <strong>{speaker}</strong> → {role === "sales_rep" ? "Sales Rep" : "Customer"}
                  </li>
                ))}
              </ul>
            ) : (
              <span style={{ fontStyle: "italic" }}>Role Classification Pending</span>
            )}
          </div>
        </div>

        {/* ── Objections ── */}
        <div style={{ margin: "16px 0 12px 0", borderTop: "1px solid #eee", paddingTop: "12px" }}>
          <strong>⚠ Detected Objections:</strong>
          <span style={{
            backgroundColor: objections && objections.length > 0 ? "#ef4444" : "#e2e8f0",
            color: objections && objections.length > 0 ? "white" : "#475569",
            borderRadius: "10px",
            padding: "2px 8px",
            fontSize: "0.8em",
            fontWeight: "bold",
            marginLeft: "6px",
          }}>
            {objections ? objections.length : 0}
          </span>
          {objections && objections.length > 0 ? (
            <ul style={{ paddingLeft: "20px", margin: "8px 0 0 0", fontSize: "0.9em" }}>
              {objections.map((obj, idx) => {
                const text = typeof obj === "string" ? obj : (obj?.text || "");
                const cat = typeof obj === "object" && obj?.category ? `[${obj.category}] ` : "";
                return (
                  <li key={idx} style={{ margin: "6px 0", color: "#b91c1c" }}>
                    <span style={{ fontWeight: "600" }}>{cat}</span>
                    <span style={{ fontStyle: "italic" }}>"{text}"</span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p style={{ margin: "8px 0 0 0", color: "#64748b", fontSize: "0.9em", fontStyle: "italic" }}>
              No objections detected
            </p>
          )}
        </div>

        {/* ── Objection Handling Quality ── */}
        <div style={{ margin: "16px 0 12px 0", borderTop: "1px solid #eee", paddingTop: "12px" }}>
          <strong>Objection Handling Quality</strong>
          {metrics.objectionHandling && metrics.objectionHandling.length > 0 ? (
            <div style={{ marginTop: "8px", fontSize: "0.9em" }}>
              <div style={{ display: "flex", gap: "12px", marginBottom: "8px", flexWrap: "wrap", fontWeight: "600" }}>
                <span>Total: {metrics.objectionHandling.length}</span>
                <span>Resolved: {metrics.objectionHandling.filter(o => o.status === "resolved").length}</span>
                <span>Ignored: {metrics.objectionHandling.filter(o => o.status === "ignored").length}</span>
                <span>Avg Delay: {metrics.objectionHandling.filter(o => o.response_delay_seconds !== null).length > 0 ? (metrics.objectionHandling.reduce((acc, o) => acc + (o.response_delay_seconds || 0), 0) / metrics.objectionHandling.filter(o => o.response_delay_seconds !== null).length).toFixed(1) + "s" : "N/A"}</span>
                <span>Score: {(metrics.objectionHandling.reduce((acc, o) => acc + o.score, 0) / metrics.objectionHandling.length * 100).toFixed(0)}%</span>
              </div>
              <ul style={{ paddingLeft: "0", margin: "0", listStyle: "none" }}>
                {metrics.objectionHandling.map((obj, idx) => (
                  <li key={idx} style={{ margin: "12px 0", padding: "8px", border: "1px solid #e2e8f0", borderRadius: "6px", backgroundColor: "#f8fafc" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontWeight: "bold", color: "#b91c1c" }}>[{obj.category}] Objection</span>
                      <span style={{ 
                        fontWeight: "bold",
                        color: obj.status === "resolved" ? "#10b981" : obj.status === "addressed" ? "#3b82f6" : obj.status === "acknowledged" ? "#f59e0b" : "#ef4444" 
                      }}>
                        {obj.status.toUpperCase()} ({obj.score})
                      </span>
                    </div>
                    <div style={{ marginBottom: "4px" }}>
                      <span style={{ fontWeight: "bold", fontSize: "0.85em" }}>{obj.customer_speaker} (Customer):</span> 
                      <span style={{ fontStyle: "italic", marginLeft: "4px" }}>"{obj.objection_text}"</span>
                    </div>
                    {obj.response_text ? (
                      <div>
                        <span style={{ fontWeight: "bold", fontSize: "0.85em" }}>{obj.sales_rep} (Sales Rep):</span>
                        <span style={{ fontStyle: "italic", marginLeft: "4px" }}>"{obj.response_text}"</span>
                        <div style={{ fontSize: "0.8em", color: "#64748b", marginTop: "4px" }}>Delay: {obj.response_delay_seconds}s</div>
                      </div>
                    ) : (
                      <div style={{ fontStyle: "italic", color: "#64748b" }}>No sales response recorded.</div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p style={{ margin: "8px 0 0 0", color: "#64748b", fontSize: "0.9em", fontStyle: "italic" }}>
              {sessionStatus === "completed" ? "No objections handled." : "Handling quality will be calculated post-session."}
            </p>
          )}
        </div>

        {/* ── Buying Signals ── */}
        <div style={{ margin: "16px 0 12px 0", borderTop: "1px solid #eee", paddingTop: "12px" }}>
          <strong>🚀 Buying Signals:</strong>
          <span style={{
            backgroundColor: buying_signals && buying_signals.length > 0 ? "#10b981" : "#e2e8f0",
            color: buying_signals && buying_signals.length > 0 ? "white" : "#475569",
            borderRadius: "10px",
            padding: "2px 8px",
            fontSize: "0.8em",
            fontWeight: "bold",
            marginLeft: "6px",
          }}>
            {buying_signals ? buying_signals.length : 0}
          </span>
          {buying_signals && buying_signals.length > 0 ? (
            <ul style={{ paddingLeft: "20px", margin: "8px 0 0 0", fontSize: "0.9em" }}>
              {buying_signals.map((sig, idx) => {
                const text = typeof sig === "string" ? sig : (sig?.text || String(sig));
                return (
                  <li key={idx} style={{ margin: "6px 0", color: "#065f46" }}>
                    <span style={{ fontStyle: "italic" }}>"{text}"</span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p style={{ margin: "8px 0 0 0", color: "#64748b", fontSize: "0.9em", fontStyle: "italic" }}>
              Awaiting buying signals
            </p>
          )}
        </div>
      </div>
    </div>
  );
});

MetricsPanel.displayName = "MetricsPanel";

export default MetricsPanel;
