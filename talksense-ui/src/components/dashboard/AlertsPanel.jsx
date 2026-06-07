import React, { memo, useMemo } from "react";

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
          visibleAlerts.map((alert) => (
            <div 
              key={`${alert.level || "info"}-${alert._parsedTimestamp}-${alert.message || ""}-${alert._originalIndex}`} 
              role="alert"
              aria-live="polite"
              className={`alert-item alert-${alert.level || "info"}`} 
              style={{ margin: "8px 0", padding: "8px", borderLeft: "4px solid #ccc" }}
            >
              <strong style={{ textTransform: "capitalize" }}>[{alert.level || "info"}]</strong>
              <p style={{ margin: "4px 0" }}>{alert.message || "Unknown alert message"}</p>
              <small style={{ color: "#666" }}>
                {alert._parsedTimestamp > 0
                  ? new Date(alert._parsedTimestamp).toLocaleTimeString()
                  : "Unknown time"}
              </small>
            </div>
          ))
        ) : (
          <p>No active alerts.</p>
        )}
      </div>
    </div>
  );
});

AlertsPanel.displayName = "AlertsPanel";

export default AlertsPanel;



