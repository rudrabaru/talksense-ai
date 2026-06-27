import React, { memo, useMemo } from "react";

const ALERT_RECOMMENDATIONS = {
  sentiment_crash: {
    trigger_reason: "Sharp drop in conversation sentiment",
    recommendation: "Acknowledge the shift in tone and ask open-ended clarifying questions."
  },
  speaking_imbalance: {
    trigger_reason: "One person dominating >80% of conversation",
    recommendation: "Pause and ask the other party for their thoughts to rebalance."
  },
  repeated_objections: {
    trigger_reason: "3+ objections detected",
    recommendation: "Stop pitching. Address the underlying concerns directly."
  },
  long_silence: {
    trigger_reason: ">15s silence with low engagement",
    recommendation: "Re-engage by checking in: 'Does that make sense?'"
  },
  excessive_fillers: {
    trigger_reason: "High filler word density",
    recommendation: "Slow down your pace and speak more deliberately."
  },
  low_engagement: {
    trigger_reason: "Health score < 40",
    recommendation: "Shift the topic or ask a highly relevant question to regain attention."
  },
  buying_signal: {
    trigger_reason: "Positive purchasing intent detected",
    recommendation: "Confirm alignment and move towards next steps or closing."
  }
};

const AlertsPanel = memo(({ alerts }) => {
  // Memoize and sort to show latest alerts first, limited to top 3 visible
  const visibleAlerts = useMemo(() => {
    if (!alerts) return [];
    return [...alerts]
      .map((alert, index) => {
        let tsMs = 0;
        const ts = alert.timestamp;
        if (ts !== undefined && ts !== null) {
          if (typeof ts === "number") {
            tsMs = ts < 1e11 ? ts * 1000 : ts;
          } else {
            const parsedNum = Number(ts);
            if (!isNaN(parsedNum)) {
              tsMs = parsedNum < 1e11 ? parsedNum * 1000 : parsedNum;
            } else {
              const parsedDate = Date.parse(ts);
              tsMs = isNaN(parsedDate) ? 0 : parsedDate;
            }
          }
        }
        return {
          ...alert,
          _parsedTimestamp: tsMs,
          _originalIndex: index
        };
      })
      .sort((a, b) => {
        if (b._parsedTimestamp !== a._parsedTimestamp) {
          return b._parsedTimestamp - a._parsedTimestamp;
        }
        return a._originalIndex - b._originalIndex;
      })
      .slice(0, 3);
  }, [alerts]);

  return (
    <div className="alerts-panel-placeholder" style={{ border: "1px solid #ccc", padding: "16px", height: "100%", overflowY: "auto" }}>
      <h3>Real-Time Alerts</h3>
      <div className="alerts-list">
        {visibleAlerts.length > 0 ? (
          visibleAlerts.map((alert) => {
            const rec = ALERT_RECOMMENDATIONS[alert.alert_type] || {};
            const borderColor = alert.level === 'critical' ? '#ef4444' : alert.level === 'warning' ? '#f59e0b' : '#3b82f6';
            const textColor = alert.level === 'critical' ? '#b91c1c' : alert.level === 'warning' ? '#b45309' : '#0369a1';
            
            return (
            <div 
              key={`${alert.level || "info"}-${alert._parsedTimestamp}-${alert.message || ""}-${alert._originalIndex}`} 
              role="alert"
              aria-live="polite"
              className={`alert-item alert-${alert.level || "info"}`} 
              style={{ margin: "8px 0", padding: "12px", borderLeft: `4px solid ${borderColor}`, backgroundColor: "#f8fafc", borderRadius: "0 6px 6px 0" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
                <strong style={{ textTransform: "capitalize", color: textColor }}>
                  [{alert.level || "info"}]
                </strong>
                <small style={{ color: "#64748b" }}>
                  {alert._parsedTimestamp > 0
                    ? new Date(alert._parsedTimestamp).toLocaleTimeString()
                    : "Unknown time"}
                </small>
              </div>
              <p style={{ margin: "4px 0", fontWeight: "500", color: "#1e293b" }}>{alert.message || "Unknown alert message"}</p>
              
              {rec.trigger_reason && (
                <div style={{ marginTop: "8px", fontSize: "0.85em", color: "#475569" }}>
                  <strong>Trigger:</strong> {rec.trigger_reason}
                </div>
              )}
              
              {rec.recommendation && (
                <div style={{ marginTop: "4px", fontSize: "0.85em", color: "#0f766e", backgroundColor: "#f0fdfa", padding: "6px", borderRadius: "4px", border: "1px solid #ccfbf1" }}>
                  <strong>💡 Recommendation:</strong> {rec.recommendation}
                </div>
              )}
            </div>
          )})
        ) : (
          <p>No active alerts.</p>
        )}
      </div>
    </div>
  );
});

AlertsPanel.displayName = "AlertsPanel";

export default AlertsPanel;



