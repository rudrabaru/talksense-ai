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

const MetricsPanel = memo(({ metrics, sessionStatus, lastSyncAt, mode }) => {
  const [secondsAgo, setSecondsAgo] = React.useState(null);

  React.useEffect(() => {
    if (!lastSyncAt) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
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

  const hasValidMetrics = !!(
    metrics &&
    (
      metrics.speakerAttributionStatus !== undefined ||
      (metrics.health_score != null && !isNaN(Number(metrics.health_score))) ||
      (metrics.duration_seconds != null && !isNaN(Number(metrics.duration_seconds))) ||
      (metrics.participation != null &&
        typeof metrics.participation === "object" &&
        Object.keys(metrics.participation).length > 0)
    )
  );

  if (!hasValidMetrics) {
    return (
      <div
        className="metrics-panel-placeholder flex flex-col w-full"
        role="region"
        aria-label="Session metrics"
      >
        <h3 
          className="font-semibold text-slate-800 text-lg m-0"
          style={{ position: "sticky", top: 0, background: "white", zIndex: 10, paddingBottom: "8px", paddingTop: "8px" }}
        >
          Session Metrics
        </h3>
        <p className="text-sm text-slate-500 italic m-0">No metrics available.</p>
      </div>
    );
  }



  const {
    health_score,
    speaking_ratio,
    filler_count,
    duration_seconds,
    interruptions,
    speaker_switches,
    action_items,
    decisions,
    objection_timeline,
    buying_signal_timeline,
    filler_penalty,
    pause_penalty,
    sentiment,
    talkTimeline,
    analyticsHealth,
    postSessionAi,
  } = metrics;



  const parsedDuration = duration_seconds != null ? Number(duration_seconds) : NaN;
  const durationText = !isNaN(parsedDuration) ? `${parsedDuration.toFixed(1)}s` : "N/A";

  const renderSpeakingRatio = () => {
    if (!speaking_ratio || typeof speaking_ratio !== "object") return <div style={{ color: "#64748b", fontSize: "0.85em", fontStyle: "italic" }}>N/A</div>;
    const speakerColors = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b"];
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {Object.entries(speaking_ratio).map(([speaker, ratio], idx) => {
          const color = speakerColors[idx % speakerColors.length];
          return (
            <div key={speaker}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85em", marginBottom: "4px" }}>
                <span style={{ fontWeight: 600, color: "#1e293b" }}>{speaker}</span>
                <span style={{ color: "#64748b", fontWeight: 500 }}>{ratio}%</span>
              </div>
              <div 
                aria-label={`${speaker} speaking ratio: ${ratio}%`}
                style={{ height: "6px", backgroundColor: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}
              >
                <div style={{ height: "100%", width: `${ratio}%`, backgroundColor: color, borderRadius: "3px", transition: "width 0.3s ease" }} />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div
      className="metrics-panel-placeholder flex flex-col w-full"
      role="region"
      aria-label="Session metrics"
      style={{ wordBreak: "break-word" }}
    >
      <h3 
        className="font-semibold text-slate-800 text-lg m-0"
        style={{ position: "sticky", top: 0, background: "white", zIndex: 10, paddingBottom: "12px", paddingTop: "8px" }}
      >
        Session Metrics
      </h3>
      <div className="metrics-content flex flex-col gap-6">
      
        {/* ── 1. Session Health ── */}
        <div style={{ padding: "12px", backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h4 style={{ margin: 0, fontWeight: "700", color: "#1e293b", fontSize: "0.9em", textTransform: "uppercase", letterSpacing: "0.5px" }}>Session Health</h4>
            <div style={{ 
              backgroundColor: health_score >= 70 ? "#d1fae5" : health_score >= 40 ? "#fef3c7" : "#fee2e2", 
              color: health_score >= 70 ? "#059669" : health_score >= 40 ? "#d97706" : "#dc2626", 
              padding: "2px 8px", borderRadius: "12px", fontWeight: "bold", fontSize: "0.85em" 
            }}>
              {health_score != null ? `${health_score}%` : "N/A"}
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "0.85em", color: "#475569" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Sentiment:</span>
              <strong style={{ color: "#1e293b", textTransform: "capitalize" }}>
                {sentiment != null ? (typeof sentiment === 'number' ? `${sentiment.toFixed(0)}%` : sentiment) : "N/A"}
              </strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Filler Penalty:</span>
              <strong style={{ color: filler_penalty == null ? "#1e293b" : filler_penalty > 15 ? "#ef4444" : filler_penalty > 5 ? "#f59e0b" : "#10b981" }}>
                {filler_penalty != null ? `${filler_penalty.toFixed(0)}` : "N/A"}
              </strong>
            </div>
            {pause_penalty != null && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Pause Penalty:</span>
                <strong style={{ color: pause_penalty > 15 ? "#ef4444" : pause_penalty > 5 ? "#f59e0b" : "#10b981" }}>{pause_penalty.toFixed(0)}</strong>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Action Items:</span>
              <strong style={{ color: "#1e293b" }}>{action_items ? action_items.length : 0}</strong>
            </div>
          </div>
        </div>

        {/* ── 2. Speaking Ratio ── */}
        <div>
          <strong style={{ display: "block", marginBottom: "12px", color: "#1e293b", fontSize: "0.95em" }}>Speaking Ratio</strong>
          {renderSpeakingRatio()}
        </div>

        {/* ── 3. Conversation Flow ── */}
        <div>
          <strong style={{ display: "block", marginBottom: "12px", color: "#1e293b", fontSize: "0.95em" }}>Conversation Flow (Live)</strong>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.85em" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #f1f5f9" }} aria-label={`Speaker Switches: ${speaker_switches ?? 0}`}>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569" }}><span aria-hidden="true" title="Speaker Switches">🔄</span> Switches</span>
              <strong style={{ color: "#1e293b" }}>{speaker_switches ?? 0}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #f1f5f9" }} aria-label={`Interruptions: ${interruptions ?? 0}`}>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569" }}><span aria-hidden="true" title="Interruptions">✋</span> Interruptions</span>
              <strong style={{ color: "#1e293b" }}>{interruptions ?? 0}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #f1f5f9" }} aria-label={`Fillers: ${filler_count ?? 0}`}>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569" }}><span aria-hidden="true" title="Fillers">💬</span> Fillers</span>
              <strong style={{ color: "#1e293b" }}>{filler_count ?? 0}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #f1f5f9" }} aria-label={`Duration: ${durationText}`}>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569" }}><span aria-hidden="true" title="Duration">⏱</span> Duration</span>
              <strong style={{ color: "#1e293b" }}>{durationText}</strong>
            </div>
          </div>
        </div>

        {/* ── 4. Meeting/Sales specific metrics ── */}
        <div style={{ borderTop: "1px solid #eee", paddingTop: "20px", display: "flex", flexDirection: "column", gap: "20px" }}>
          
          {/* Meeting Intelligence */}
          <div>
            <strong style={{ display: "block", marginBottom: "12px", color: "#1e293b", fontSize: "0.95em" }}>Meeting Intelligence</strong>
            
            <div style={{ marginBottom: "12px" }}>
              <span style={{ fontSize: "0.85em", fontWeight: "bold", color: "#475569", textTransform: "uppercase" }}>Decisions ({decisions ? decisions.length : 0})</span>
              {decisions && decisions.length > 0 ? (
                <ul style={{ paddingLeft: "20px", margin: "8px 0 0 0", fontSize: "0.85em" }}>
                  {decisions.map((dec, idx) => (
                    <li key={idx} style={{ margin: "4px 0", color: "#1e293b" }}>{dec}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "0.85em", fontStyle: "italic" }}>No decisions captured yet.</p>
              )}
            </div>
            
            <div>
              <span style={{ fontSize: "0.85em", fontWeight: "bold", color: "#475569", textTransform: "uppercase" }}>Action Items ({action_items ? action_items.length : 0})</span>
              {action_items && action_items.length > 0 ? (
                <ul style={{ paddingLeft: "20px", margin: "8px 0 0 0", fontSize: "0.85em" }}>
                  {action_items.map((item, idx) => {
                    const text = typeof item === 'object' ? item.text : item;
                    const owner = typeof item === 'object' && item.owner ? item.owner : null;
                    return (
                      <li key={idx} style={{ margin: "4px 0", color: "#1e293b" }}>
                        {text}
                        {owner && <span style={{ marginLeft: "8px", backgroundColor: "#e0e7ff", color: "#4338ca", padding: "2px 6px", borderRadius: "4px", fontSize: "0.8em", fontWeight: "bold" }}>@{owner}</span>}
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "0.85em", fontStyle: "italic" }}>No action items captured yet.</p>
              )}
            </div>
          </div>

          {/* Role Classification */}
          <div>
            <strong style={{ display: "block", marginBottom: "8px", color: "#1e293b", fontSize: "0.95em" }}>Role Classification</strong>
            <div style={{ fontSize: "0.85em", color: "#475569" }}>
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

          {/* Sales specific metrics */}
          {mode === "sales" && (
            <>
              {/* Objection Timeline */}
              <div>
                <strong style={{ display: "inline-flex", alignItems: "center", color: "#1e293b", fontSize: "0.95em" }}>
                  ⚠ Objection Timeline
                  <span style={{ backgroundColor: objection_timeline && objection_timeline.length > 0 ? "#ef4444" : "#e2e8f0", color: objection_timeline && objection_timeline.length > 0 ? "white" : "#475569", borderRadius: "10px", padding: "2px 8px", fontSize: "0.8em", fontWeight: "bold", marginLeft: "8px" }}>
                    {objection_timeline ? objection_timeline.length : 0}
                  </span>
                </strong>
                {objection_timeline && objection_timeline.length > 0 ? (
                  <div style={{ marginTop: "12px", borderLeft: "2px solid #e2e8f0", paddingLeft: "12px" }}>
                    {objection_timeline.map((obj, idx) => {
                      const text = typeof obj === "string" ? obj : (obj?.text || "");
                      const cat = typeof obj === "object" && obj?.category ? `[${obj.category}] ` : "";
                      const ts = typeof obj === "object" && obj?.timestamp != null ? new Date(obj.timestamp * 1000).toISOString().substr(14, 5) : "--:--";
                      return (
                        <div key={idx} style={{ margin: "10px 0", position: "relative" }}>
                          <div style={{ position: "absolute", left: "-17px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#ef4444" }} />
                          <div style={{ fontSize: "0.75em", color: "#64748b", fontWeight: "bold", marginBottom: "2px" }}>{ts}</div>
                          <div style={{ color: "#b91c1c", fontSize: "0.85em" }}>
                            <span style={{ fontWeight: "600" }}>{cat}</span>
                            <span style={{ fontStyle: "italic" }}>"{text}"</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p style={{ margin: "6px 0 0 0", color: "#64748b", fontSize: "0.85em", fontStyle: "italic" }}>No objections detected</p>
                )}
              </div>

              {/* Objection Handling Quality */}
              <div>
                <strong style={{ display: "block", marginBottom: "8px", color: "#1e293b", fontSize: "0.95em" }}>Objection Handling Quality</strong>
                {metrics.objectionHandling && metrics.objectionHandling.length > 0 ? (
                  <div style={{ fontSize: "0.85em" }}>
                    <div style={{ display: "flex", gap: "10px", marginBottom: "10px", flexWrap: "wrap", fontWeight: "600", color: "#475569" }}>
                      <span>Total: {metrics.objectionHandling.length}</span>
                      <span style={{ color: "#10b981" }}>Resolved: {metrics.objectionHandling.filter(o => o.status === "resolved").length}</span>
                      <span style={{ color: "#ef4444" }}>Ignored: {metrics.objectionHandling.filter(o => o.status === "ignored").length}</span>
                      <span>Score: {(metrics.objectionHandling.reduce((acc, o) => acc + o.score, 0) / metrics.objectionHandling.length * 100).toFixed(0)}%</span>
                    </div>
                    <ul style={{ paddingLeft: "0", margin: "0", listStyle: "none" }}>
                      {metrics.objectionHandling.map((obj, idx) => (
                        <li key={idx} style={{ margin: "10px 0", padding: "8px", border: "1px solid #e2e8f0", borderRadius: "6px", backgroundColor: "#f8fafc" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                            <span style={{ fontWeight: "bold", color: "#b91c1c" }}>[{obj.category}] Objection</span>
                            <span style={{ fontWeight: "bold", color: obj.status === "resolved" ? "#10b981" : obj.status === "addressed" ? "#3b82f6" : obj.status === "acknowledged" ? "#f59e0b" : "#ef4444" }}>
                              {obj.status.toUpperCase()} ({obj.score})
                            </span>
                          </div>
                          <div style={{ marginBottom: "4px" }}>
                            <span style={{ fontWeight: "bold" }}>{obj.customer_speaker} (Customer):</span> <span style={{ fontStyle: "italic" }}>"{obj.objection_text}"</span>
                          </div>
                          {obj.response_text ? (
                            <div>
                              <span style={{ fontWeight: "bold" }}>{obj.sales_rep} (Sales Rep):</span> <span style={{ fontStyle: "italic" }}>"{obj.response_text}"</span>
                              <div style={{ fontSize: "0.9em", color: "#64748b", marginTop: "2px" }}>Delay: {obj.response_delay_seconds}s</div>
                            </div>
                          ) : (
                            <div style={{ fontStyle: "italic", color: "#64748b" }}>No sales response recorded.</div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p style={{ margin: "6px 0 0 0", color: "#64748b", fontSize: "0.85em", fontStyle: "italic" }}>{sessionStatus === "completed" ? "No objections handled." : "Handling quality will be calculated post-session."}</p>
                )}
              </div>

              {/* Buying Signals Timeline */}
              <div>
                <strong style={{ display: "inline-flex", alignItems: "center", color: "#1e293b", fontSize: "0.95em" }}>
                  🚀 Buying Signals Timeline
                  <span style={{ backgroundColor: buying_signal_timeline && buying_signal_timeline.length > 0 ? "#10b981" : "#e2e8f0", color: buying_signal_timeline && buying_signal_timeline.length > 0 ? "white" : "#475569", borderRadius: "10px", padding: "2px 8px", fontSize: "0.8em", fontWeight: "bold", marginLeft: "8px" }}>
                    {buying_signal_timeline ? buying_signal_timeline.length : 0}
                  </span>
                </strong>
                {buying_signal_timeline && buying_signal_timeline.length > 0 ? (
                  <div style={{ marginTop: "12px", borderLeft: "2px solid #e2e8f0", paddingLeft: "12px" }}>
                    {buying_signal_timeline.map((sig, idx) => {
                      const text = typeof sig === "string" ? sig : (sig?.text || String(sig));
                      const ts = typeof sig === "object" && sig?.timestamp != null ? new Date(sig.timestamp * 1000).toISOString().substr(14, 5) : "--:--";
                      return (
                        <div key={idx} style={{ margin: "10px 0", position: "relative" }}>
                          <div style={{ position: "absolute", left: "-17px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#10b981" }} />
                          <div style={{ fontSize: "0.75em", color: "#64748b", fontWeight: "bold", marginBottom: "2px" }}>{ts}</div>
                          <div style={{ color: "#065f46", fontSize: "0.85em", fontStyle: "italic" }}>"{text}"</div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p style={{ margin: "6px 0 0 0", color: "#64748b", fontSize: "0.85em", fontStyle: "italic" }}>Awaiting buying signals</p>
                )}
              </div>
            </>
          )}
        </div>

        {/* ── 5. Benchmark / Diagnostic metrics ── */}
        <div style={{ borderTop: "1px solid #eee", paddingTop: "20px", display: "flex", flexDirection: "column", gap: "20px", opacity: 0.85 }}>
          
          {/* Analytics Health Benchmark Status */}
          {analyticsHealth && (
            <div style={{ padding: "10px", backgroundColor: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "8px" }}>
              <strong style={{ display: "block", marginBottom: "8px", fontSize: "0.9em", color: "#475569" }}>Diagnostic: Analytics Health</strong>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", fontSize: "0.8em" }}>
                {Object.entries(analyticsHealth).map(([key, status]) => (
                  <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ color: "#64748b" }}>{key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}:</span>
                    <span style={{ fontWeight: "bold", color: status === "PASS" ? "#10b981" : "#ef4444", fontSize: "0.9em" }}>{status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Speaker Attribution Quality Card */}
          <div style={{ transform: "scale(0.95)", transformOrigin: "left top", width: "105%" }}>
            <SpeakerAttributionCard attribution={metrics.speakerAttribution} attributionStatus={metrics.speakerAttributionStatus} sessionStatus={sessionStatus} secondsAgo={secondsAgo} />
          </div>

          {/* Post-Session Conversation Flow Analytics */}
          <div>
            <strong style={{ display: "block", marginBottom: "6px", color: "#475569", fontSize: "0.9em" }}>Post-Session Flow Analytics</strong>
            {postSessionAi ? (
              <div style={{ fontSize: "0.8em", color: "#64748b" }}>
                <div style={{ marginBottom: "8px" }}>
                  <strong>Summary:</strong> {postSessionAi.summary || postSessionAi.executive_summary || "No summary available."}
                </div>
                {postSessionAi.decisions && postSessionAi.decisions.length > 0 && (
                  <div style={{ marginBottom: "8px" }}>
                    <strong>Decisions:</strong>
                    <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                      {postSessionAi.decisions.map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                  </div>
                )}
                {postSessionAi.action_items && postSessionAi.action_items.length > 0 && (
                  <div style={{ marginBottom: "8px" }}>
                    <strong>Action Items:</strong>
                    <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                      {postSessionAi.action_items.map((a, i) => <li key={i}>{a.description} (Assignee: {a.assignee})</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p style={{ margin: "2px 0 0 0", color: "#94a3b8", fontSize: "0.8em", fontStyle: "italic" }}>{sessionStatus === "completed" ? "Generating AI summary..." : "Available post-session"}</p>
            )}
          </div>

          {/* Talk Ratio Timeline */}
          {talkTimeline && talkTimeline.timeline && talkTimeline.timeline.length > 0 && (
            <div>
              <strong style={{ display: "block", marginBottom: "6px", color: "#475569", fontSize: "0.9em" }}>Talk Ratio Timeline</strong>
              <div style={{ fontSize: "0.75em", overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", color: "#64748b" }}>
                  <thead>
                    <tr style={{ backgroundColor: "#f1f5f9", borderBottom: "1px solid #e2e8f0" }}>
                      <th style={{ padding: "4px" }}>Window</th>
                      {Array.from(new Set(talkTimeline.timeline.flatMap(b => Object.keys(b.speakers)))).sort().map(spk => (
                        <th key={spk} style={{ padding: "4px" }}>{spk} %</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {talkTimeline.timeline.map((bucket, idx) => {
                      const allSpeakers = Array.from(new Set(talkTimeline.timeline.flatMap(b => Object.keys(b.speakers)))).sort();
                      return (
                        <tr key={idx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <td style={{ padding: "4px" }}>{bucket.window_start}s-{bucket.window_end}s</td>
                          {allSpeakers.map(spk => {
                            const pct = bucket.speakers[spk]?.participation || 0;
                            return <td key={spk} style={{ padding: "4px", fontWeight: pct > 50 ? "bold" : "normal" }}>{pct}%</td>;
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
});

MetricsPanel.displayName = "MetricsPanel";

export default MetricsPanel;
